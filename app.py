import os
import sqlite3
from datetime import date, datetime

import flask

app = flask.Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), 'hilsener.db')
MAKS_LENGDE = 200
KORT_LENGDE = 40
FODSELSDAG = date(2009, 8, 19)

SPORRING = """
    SELECT h.id, h.tekst, h.tidspunkt, h.endret, h.svar_til, s.tekst AS svar_tekst
    FROM hilsener h
    LEFT JOIN hilsener s ON s.id = h.svar_til
"""


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
            endret TEXT
        )
    """)
    kobling.commit()
    kobling.close()


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


@app.route('/')
def forside():
    hilsener = hent_alle()
    return flask.render_template(
        'index.html',
        hilsener=hilsener,
        antall=len(hilsener),
        maks=MAKS_LENGDE,
        fodselsdag=FODSELSDAG.strftime('%d.%m.%Y'),
        alder=regn_alder(FODSELSDAG),
    )


@app.route('/api/hilsener')
def api():
    hilsener = hent_alle()
    return flask.jsonify({'antall': len(hilsener), 'hilsener': hilsener})


@app.route('/hilsen', methods=['POST'])
def ny_hilsen():
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
        'INSERT INTO hilsener (tekst, tidspunkt, svar_til) VALUES (?, ?, ?)',
        (tekst, naa(), svar_til),
    )
    kobling.commit()
    hilsen = hent_en(kobling, markor.lastrowid)
    hilsen['antall'] = tell(kobling)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['PUT'])
def endre_hilsen(hilsen_id):
    data = flask.request.get_json(silent=True) or {}
    tekst, feil = les_tekst(data)
    if feil:
        return flask.jsonify({'feil': feil}), 400

    kobling = koble()
    if hent_en(kobling, hilsen_id) is None:
        kobling.close()
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404

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
    kobling = koble()
    if hent_en(kobling, hilsen_id) is None:
        kobling.close()
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404

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
