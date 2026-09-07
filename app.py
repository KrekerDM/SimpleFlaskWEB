import base64
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import date, datetime

import flask
from Crypto.Cipher import AES

app = flask.Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), 'hilsener.db')
NOKKEL_FIL = os.path.join(os.path.dirname(__file__), 'nokkel.bin')
MAKS_LENGDE = 200
KORT_LENGDE = 40
MIN_PASSORD = 8
RUNDER = 200000
KAKE = 'innlogging'
KAKE_DAGER = 7
NAVN_MONSTER = re.compile(r'^[A-Za-z0-9_-]{3,20}$')
FODSELSDAG = date(2009, 8, 19)

SPORRING = """
    SELECT h.id, h.tekst, h.tidspunkt, h.endret, h.svar_til, h.bruker_id,
           b.brukernavn AS navn, s.tekst AS svar_tekst
    FROM hilsener h
    LEFT JOIN hilsener s ON s.id = h.svar_til
    LEFT JOIN brukere b ON b.id = h.bruker_id
"""

SKJEMAER = {
    'registrer': {
        'tittel': 'Registrer deg',
        'knapp': 'Lag bruker',
        'annen_url': '/logg-inn',
        'annen_tekst': 'Har du bruker alt? Logg inn',
        'bilde': 'registrer.jpg',
        'bilde_tekst': 'Grisen Peppa som stirrer ut av mørket',
    },
    'logg-inn': {
        'tittel': 'Logg inn',
        'knapp': 'Logg inn',
        'annen_url': '/registrer',
        'annen_tekst': 'Ny her? Registrer deg',
        'bilde': 'logg-inn.jpg',
        'bilde_tekst': 'En T-rex og en hund som glaner rett i kamera',
    },
}


def koble():
    kobling = sqlite3.connect(DATABASE)
    kobling.row_factory = sqlite3.Row
    return kobling


def lag_tabell():
    kobling = koble()
    kobling.execute("""
        CREATE TABLE IF NOT EXISTS hilsener (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tekst TEXT NOT NULL,
            tidspunkt TEXT NOT NULL,
            svar_til INTEGER,
            endret TEXT,
            bruker_id INTEGER
        )
    """)
    kobling.execute("""
        CREATE TABLE IF NOT EXISTS brukere (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brukernavn TEXT NOT NULL UNIQUE,
            salt TEXT NOT NULL,
            passord TEXT NOT NULL,
            laget TEXT NOT NULL
        )
    """)
    kolonner = [rad['name'] for rad in kobling.execute('PRAGMA table_info(hilsener)')]
    if 'bruker_id' not in kolonner:
        kobling.execute('ALTER TABLE hilsener ADD COLUMN bruker_id INTEGER')
    kobling.commit()
    kobling.close()


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


def hent_bruker():
    kake = flask.request.cookies.get(KAKE)
    if not kake:
        return None

    id_tekst = dekrypter(kake)
    if not id_tekst or not id_tekst.isdigit():
        return None

    kobling = koble()
    rad = kobling.execute(
        'SELECT id, brukernavn FROM brukere WHERE id = ?', (int(id_tekst),)
    ).fetchone()
    kobling.close()
    return dict(rad) if rad else None


def naa():
    return datetime.now().strftime('%d.%m.%Y %H:%M')


def kort_tekst(tekst):
    if tekst and len(tekst) > KORT_LENGDE:
        return tekst[:KORT_LENGDE].rstrip() + '…'
    return tekst


def lag_hilsen(rad):
    hilsen = dict(rad)
    hilsen['svar_kort'] = kort_tekst(hilsen.pop('svar_tekst'))
    return hilsen


def hent_alle():
    kobling = koble()
    rader = kobling.execute(SPORRING + 'ORDER BY h.id DESC').fetchall()
    kobling.close()
    return [lag_hilsen(rad) for rad in rader]


def hent_en(kobling, hilsen_id):
    rad = kobling.execute(SPORRING + 'WHERE h.id = ?', (hilsen_id,)).fetchone()
    return lag_hilsen(rad) if rad else None


def tell(kobling):
    return kobling.execute('SELECT COUNT(*) FROM hilsener').fetchone()[0]


def les_tekst(data):
    tekst = str(data.get('tekst', '')).strip()
    if not tekst:
        return None, 'Du må skrive noe før du trykker Enter.'
    if len(tekst) > MAKS_LENGDE:
        return None, f'Hilsenen kan ikke være lengre enn {MAKS_LENGDE} tegn.'
    return tekst, None


def finn_traad(kobling, hilsen_id):
    ider = [hilsen_id]
    for forelder in ider:
        for rad in kobling.execute('SELECT id FROM hilsener WHERE svar_til = ?', (forelder,)):
            ider.append(rad['id'])
    return ider


def regn_alder(fodt):
    i_dag = date.today()
    alder = i_dag.year - fodt.year
    if (i_dag.month, i_dag.day) < (fodt.month, fodt.day):
        alder = alder - 1
    return alder


def vis_skjema(navn, feil=None):
    return flask.render_template(
        'skjema.html', handling='/' + navn, feil=feil, **SKJEMAER[navn]
    )


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


@app.route('/')
def forside():
    hilsener = hent_alle()
    return flask.render_template(
        'index.html',
        hilsener=hilsener,
        antall=len(hilsener),
        maks=MAKS_LENGDE,
        bruker=hent_bruker(),
        fodselsdag=FODSELSDAG.strftime('%d.%m.%Y'),
        alder=regn_alder(FODSELSDAG),
    )


@app.route('/api/hilsener')
def api():
    hilsener = hent_alle()
    return flask.jsonify({'antall': len(hilsener), 'hilsener': hilsener})


@app.route('/registrer', methods=['GET', 'POST'])
def registrer():
    if flask.request.method == 'GET':
        return vis_skjema('registrer')

    brukernavn = flask.request.form.get('brukernavn', '').strip()
    passord = flask.request.form.get('passord', '')

    if not NAVN_MONSTER.match(brukernavn):
        return vis_skjema('registrer', 'Brukernavnet må ha 3–20 tegn, og bare bokstaver, tall, - og _.'), 400

    if len(passord) < MIN_PASSORD:
        return vis_skjema('registrer', f'Passordet må ha minst {MIN_PASSORD} tegn.'), 400

    salt = os.urandom(16).hex()
    kobling = koble()

    try:
        markor = kobling.execute(
            'INSERT INTO brukere (brukernavn, salt, passord, laget) VALUES (?, ?, ?, ?)',
            (brukernavn, salt, hash_passord(passord, salt), naa()),
        )
        kobling.commit()
    except sqlite3.IntegrityError:
        kobling.close()
        return vis_skjema('registrer', 'Brukernavnet er opptatt.'), 400

    bruker_id = markor.lastrowid
    kobling.close()

    return logg_inn_svar(bruker_id)


@app.route('/logg-inn', methods=['GET', 'POST'])
def logg_inn():
    if flask.request.method == 'GET':
        return vis_skjema('logg-inn')

    brukernavn = flask.request.form.get('brukernavn', '').strip()
    passord = flask.request.form.get('passord', '')

    kobling = koble()
    rad = kobling.execute(
        'SELECT id, salt, passord FROM brukere WHERE brukernavn = ?', (brukernavn,)
    ).fetchone()
    kobling.close()

    if rad is None or not hmac.compare_digest(rad['passord'], hash_passord(passord, rad['salt'])):
        return vis_skjema('logg-inn', 'Feil brukernavn eller passord.'), 401

    return logg_inn_svar(rad['id'])


@app.route('/logg-ut', methods=['POST'])
def logg_ut():
    svar = flask.redirect('/')
    svar.delete_cookie(KAKE)
    return svar


@app.route('/hilsen', methods=['POST'])
def ny_hilsen():
    bruker = hent_bruker()
    if bruker is None:
        return flask.jsonify({'feil': 'Du må logge inn for å skrive.'}), 401

    data = flask.request.get_json(silent=True) or {}
    tekst, feil = les_tekst(data)
    if feil:
        return flask.jsonify({'feil': feil}), 400

    try:
        svar_til = int(data['svar_til']) if data.get('svar_til') is not None else None
    except (TypeError, ValueError):
        return flask.jsonify({'feil': 'Ugyldig hilsen å svare på.'}), 400

    kobling = koble()
    if svar_til is not None and hent_en(kobling, svar_til) is None:
        kobling.close()
        return flask.jsonify({'feil': 'Hilsenen du svarte på finnes ikke lenger.'}), 404

    markor = kobling.execute(
        'INSERT INTO hilsener (tekst, tidspunkt, svar_til, bruker_id) VALUES (?, ?, ?, ?)',
        (tekst, naa(), svar_til, bruker['id']),
    )
    kobling.commit()
    hilsen = hent_en(kobling, markor.lastrowid)
    hilsen['antall'] = tell(kobling)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['PUT'])
def endre_hilsen(hilsen_id):
    bruker = hent_bruker()
    if bruker is None:
        return flask.jsonify({'feil': 'Du må logge inn for å endre.'}), 401

    data = flask.request.get_json(silent=True) or {}
    tekst, feil = les_tekst(data)
    if feil:
        return flask.jsonify({'feil': feil}), 400

    kobling = koble()
    hilsen = hent_en(kobling, hilsen_id)

    if hilsen is None:
        kobling.close()
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404

    if hilsen['bruker_id'] != bruker['id']:
        kobling.close()
        return flask.jsonify({'feil': 'Du kan bare endre dine egne hilsener.'}), 403

    kobling.execute(
        'UPDATE hilsener SET tekst = ?, endret = ? WHERE id = ?',
        (tekst, naa(), hilsen_id),
    )
    kobling.commit()
    hilsen = hent_en(kobling, hilsen_id)
    hilsen['kort'] = kort_tekst(tekst)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['DELETE'])
def slett_hilsen(hilsen_id):
    bruker = hent_bruker()
    if bruker is None:
        return flask.jsonify({'feil': 'Du må logge inn for å slette.'}), 401

    kobling = koble()
    hilsen = hent_en(kobling, hilsen_id)

    if hilsen is None:
        kobling.close()
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404

    if hilsen['bruker_id'] != bruker['id']:
        kobling.close()
        return flask.jsonify({'feil': 'Du kan bare slette dine egne hilsener.'}), 403

    ider = finn_traad(kobling, hilsen_id)
    plasser = ','.join('?' for _ in ider)
    kobling.execute(f'DELETE FROM hilsener WHERE id IN ({plasser})', ider)
    kobling.commit()
    antall = tell(kobling)
    kobling.close()

    return flask.jsonify({'slettet': ider, 'antall': antall})


@app.errorhandler(404)
def ikke_funnet(feil):
    if flask.request.path.startswith('/api/') or flask.request.method != 'GET':
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404
    return flask.render_template('404.html'), 404


lag_tabell()


if __name__ == '__main__':
    app.run(debug=True)
