import os
import sqlite3
from datetime import date, datetime

import flask

app = flask.Flask(__name__)

DATABASE = os.path.join(os.path.dirname(__file__), 'hilsener.db')
MAKS_LENGDE = 200
FODSELSDAG = date(2009, 8, 19)


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
            tidspunkt TEXT NOT NULL
        )
    """)
    kobling.commit()
    kobling.close()


def hent_alle():
    kobling = koble()
    rader = kobling.execute(
        'SELECT tekst, tidspunkt FROM hilsener ORDER BY id DESC'
    ).fetchall()
    kobling.close()
    return [dict(rad) for rad in rader]


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
    tekst = str(data.get('tekst', '')).strip()

    if not tekst:
        return flask.jsonify({'feil': 'Du må skrive noe før du trykker Enter.'}), 400

    if len(tekst) > MAKS_LENGDE:
        return flask.jsonify({
            'feil': f'Hilsenen kan ikke være lengre enn {MAKS_LENGDE} tegn.'
        }), 400

    tidspunkt = datetime.now().strftime('%d.%m.%Y %H:%M')

    kobling = koble()
    kobling.execute(
        'INSERT INTO hilsener (tekst, tidspunkt) VALUES (?, ?)',
        (tekst, tidspunkt),
    )
    kobling.commit()
    antall = kobling.execute('SELECT COUNT(*) FROM hilsener').fetchone()[0]
    kobling.close()

    return flask.jsonify({'tekst': tekst, 'tidspunkt': tidspunkt, 'antall': antall})


@app.errorhandler(404)
def ikke_funnet(feil):
    return flask.render_template('404.html'), 404


lag_tabell()


if __name__ == '__main__':
    app.run(debug=True)
