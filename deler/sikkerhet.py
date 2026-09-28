import hashlib
import hmac
import os
import secrets
import sqlite3

import flask
import flask_login

from deler import database

NOKKEL_FIL = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nokkel.bin')
RUNDER = 200000
TOM_SALT = '00' * 16

login_manager = flask_login.LoginManager()
login_manager.login_view = 'logg_inn'
login_manager.login_message = 'Du må logge inn for å gjøre dette.'


class Bruker(flask_login.UserMixin):
    def __init__(self, id, brukernavn):
        self.id = id
        self.brukernavn = brukernavn


def hent_nokkel():
    if not os.path.exists(NOKKEL_FIL):
        with open(NOKKEL_FIL, 'wb') as fil:
            fil.write(os.urandom(32))
    with open(NOKKEL_FIL, 'rb') as fil:
        return fil.read()


def koble_til_app(app):
    app.secret_key = hent_nokkel()
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.jinja_env.globals['csrf_token'] = csrf_token
    app.before_request(sjekk_csrf)
    app.after_request(sett_hoder)
    login_manager.init_app(app)


def sett_hoder(svar):
    svar.headers['X-Content-Type-Options'] = 'nosniff'
    svar.headers['X-Frame-Options'] = 'DENY'
    svar.headers['Referrer-Policy'] = 'same-origin'
    return svar


@login_manager.user_loader
def last_bruker(bruker_id):
    try:
        bruker_id = int(bruker_id)
    except (TypeError, ValueError):
        return None

    kobling = database.koble()
    rad = kobling.execute(
        'SELECT id, brukernavn FROM brukere WHERE id = ?', (bruker_id,)
    ).fetchone()
    kobling.close()
    return Bruker(rad['id'], rad['brukernavn']) if rad else None


def csrf_token():
    if 'csrf' not in flask.session:
        flask.session['csrf'] = secrets.token_urlsafe(32)
    return flask.session['csrf']


def sjekk_csrf():
    if flask.request.method in ('GET', 'HEAD', 'OPTIONS'):
        return None

    lagret = flask.session.get('csrf', '')
    sendt = flask.request.form.get('csrf') or flask.request.headers.get('X-CSRF-Token', '')

    if lagret and sendt and hmac.compare_digest(lagret, sendt):
        return None

    return flask.jsonify({'feil': 'Skjemaet var utgått. Last siden på nytt og prøv igjen.'}), 400


def trygg_neste():
    neste = flask.request.args.get('next', '')

    if neste.startswith('/') and not neste.startswith('//') and neste.isprintable():
        return neste

    return '/'


def hash_passord(passord, salt):
    return hashlib.pbkdf2_hmac('sha256', passord.encode(), bytes.fromhex(salt), RUNDER).hex()


def lag_bruker(brukernavn, passord):
    salt = os.urandom(16).hex()
    kobling = database.koble()

    try:
        markor = kobling.execute(
            'INSERT INTO brukere (brukernavn, salt, passord, laget) VALUES (?, ?, ?, ?)',
            (brukernavn, salt, hash_passord(passord, salt), database.naa()),
        )
        kobling.commit()
        return Bruker(markor.lastrowid, brukernavn)
    except sqlite3.IntegrityError:
        return None
    finally:
        kobling.close()


def sjekk_innlogging(brukernavn, passord):
    kobling = database.koble()
    rad = kobling.execute(
        'SELECT id, brukernavn, salt, passord FROM brukere WHERE brukernavn = ?', (brukernavn,)
    ).fetchone()
    kobling.close()

    if rad is None:
        hash_passord(passord, TOM_SALT)
        return None

    if not hmac.compare_digest(rad['passord'], hash_passord(passord, rad['salt'])):
        return None

    return Bruker(rad['id'], rad['brukernavn'])
