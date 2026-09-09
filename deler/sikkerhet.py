import base64
import hashlib
import hmac
import os
import sqlite3

import flask
from Crypto.Cipher import AES

from deler import database

NOKKEL_FIL = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nokkel.bin')
RUNDER = 200000
KAKE = 'innlogging'
KAKE_DAGER = 7


def hent_nokkel():
    if not os.path.exists(NOKKEL_FIL):
        with open(NOKKEL_FIL, 'wb') as fil:
            fil.write(os.urandom(32))
    with open(NOKKEL_FIL, 'rb') as fil:
        return fil.read()


NOKKEL = hent_nokkel()


def krypter(tekst):
    nonce = os.urandom(12)
    chiffer = AES.new(NOKKEL, AES.MODE_GCM, nonce=nonce)
    innhold, merke = chiffer.encrypt_and_digest(tekst.encode())
    return base64.urlsafe_b64encode(nonce + merke + innhold).decode()


def dekrypter(kake):
    try:
        raa = base64.urlsafe_b64decode(kake)
        chiffer = AES.new(NOKKEL, AES.MODE_GCM, nonce=raa[:12])
        return chiffer.decrypt_and_verify(raa[28:], raa[12:28]).decode()
    except (ValueError, KeyError):
        return None


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
        return markor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        kobling.close()


def sjekk_innlogging(brukernavn, passord):
    kobling = database.koble()
    rad = kobling.execute(
        'SELECT id, salt, passord FROM brukere WHERE brukernavn = ?', (brukernavn,)
    ).fetchone()
    kobling.close()

    if rad is None or not hmac.compare_digest(rad['passord'], hash_passord(passord, rad['salt'])):
        return None
    return rad['id']


def hent_bruker():
    kake = flask.request.cookies.get(KAKE)
    if not kake:
        return None

    id_tekst = dekrypter(kake)
    if not id_tekst or not id_tekst.isdigit():
        return None

    kobling = database.koble()
    rad = kobling.execute(
        'SELECT id, brukernavn FROM brukere WHERE id = ?', (int(id_tekst),)
    ).fetchone()
    kobling.close()
    return dict(rad) if rad else None


def logg_inn_svar(bruker_id):
    svar = flask.redirect('/')
    svar.set_cookie(
        KAKE,
        krypter(str(bruker_id)),
        max_age=KAKE_DAGER * 24 * 60 * 60,
        httponly=True,
        samesite='Lax',
    )
    return svar


def logg_ut_svar():
    svar = flask.redirect('/')
    svar.delete_cookie(KAKE)
    return svar
