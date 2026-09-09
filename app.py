import re
from datetime import date

import flask

from deler import database, sikkerhet

app = flask.Flask(__name__)

MAKS_LENGDE = 200
MIN_PASSORD = 8
NAVN_MONSTER = re.compile(r'^[A-Za-z0-9_-]{3,20}$')
FODSELSDAG = date(2009, 8, 19)

SKJEMAER = {
    'registrer': {
        'tittel': 'Registrer deg',
        'knapp': 'Lag bruker',
        'annen_url': '/logg-inn',
        'annen_tekst': 'Logg inn',
        'bilde': 'registrer.jpg',
        'bilde_tekst': 'Grisen Peppa som stirrer ut av mørket',
    },
    'logg-inn': {
        'tittel': 'Logg inn',
        'knapp': 'Logg inn',
        'annen_url': '/registrer',
        'annen_tekst': 'Registrer deg',
        'bilde': 'logg-inn.jpg',
        'bilde_tekst': 'En T-rex og en hund som glaner rett i kamera',
    },
}


def les_tekst(data):
    tekst = str(data.get('tekst', '')).strip()
    if not tekst:
        return None, 'Du må skrive noe først.'
    if len(tekst) > MAKS_LENGDE:
        return None, f'Hilsenen kan ikke være lengre enn {MAKS_LENGDE} tegn.'
    return tekst, None


def regn_alder(fodt):
    i_dag = date.today()
    alder = i_dag.year - fodt.year
    if (i_dag.month, i_dag.day) < (fodt.month, fodt.day):
        alder = alder - 1
    return alder


def finn_egen_hilsen(kobling, hilsen_id, bruker, handling):
    hilsen = database.hent_en(kobling, hilsen_id)

    if hilsen is None:
        return None, (flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404)

    if hilsen['bruker_id'] != bruker['id']:
        return None, (flask.jsonify({'feil': f'Du kan bare {handling} dine egne hilsener.'}), 403)

    return hilsen, None


def vis_sok(sokeord, feil=None):
    return flask.render_template(
        'sok.html',
        sokeord=sokeord,
        treff=database.sok_i_hilsener(sokeord) if sokeord else [],
        bruker=sikkerhet.hent_bruker(),
        maks=MAKS_LENGDE,
        feil=feil,
    )


def vis_skjema(navn, feil=None):
    return flask.render_template(
        'skjema.html', handling='/' + navn, feil=feil, **SKJEMAER[navn]
    )


@app.route('/')
def forside():
    hilsener = database.hent_alle()
    return flask.render_template(
        'index.html',
        hilsener=hilsener,
        antall=len(hilsener),
        maks=MAKS_LENGDE,
        bruker=sikkerhet.hent_bruker(),
        fodselsdag=FODSELSDAG.strftime('%d.%m.%Y'),
        alder=regn_alder(FODSELSDAG),
    )


@app.route('/api/hilsener')
def api():
    hilsener = database.hent_alle()
    return flask.jsonify({'antall': len(hilsener), 'hilsener': hilsener})


@app.route('/sok')
def sok():
    return vis_sok(flask.request.args.get('ord', '').strip())


@app.route('/svar/<int:hilsen_id>', methods=['POST'])
def svar_pa(hilsen_id):
    sokeord = flask.request.form.get('ord', '').strip()
    bruker = sikkerhet.hent_bruker()

    if bruker is None:
        return vis_sok(sokeord, 'Du må logge inn for å svare.'), 401

    tekst, feil = les_tekst(flask.request.form)
    if feil:
        return vis_sok(sokeord, feil), 400

    kobling = database.koble()

    if database.hent_en(kobling, hilsen_id) is None:
        kobling.close()
        return vis_sok(sokeord, 'Fant ikke hilsenen.'), 404

    database.lagre_hilsen(kobling, tekst, hilsen_id, bruker['id'])
    kobling.close()

    return flask.redirect(flask.url_for('sok', ord=sokeord))


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

    bruker_id = sikkerhet.lag_bruker(brukernavn, passord)
    if bruker_id is None:
        return vis_skjema('registrer', 'Brukernavnet er opptatt.'), 400

    return sikkerhet.logg_inn_svar(bruker_id)


@app.route('/logg-inn', methods=['GET', 'POST'])
def logg_inn():
    if flask.request.method == 'GET':
        return vis_skjema('logg-inn')

    brukernavn = flask.request.form.get('brukernavn', '').strip()
    passord = flask.request.form.get('passord', '')

    bruker_id = sikkerhet.sjekk_innlogging(brukernavn, passord)
    if bruker_id is None:
        return vis_skjema('logg-inn', 'Feil brukernavn eller passord.'), 401

    return sikkerhet.logg_inn_svar(bruker_id)


@app.route('/logg-ut', methods=['POST'])
def logg_ut():
    return sikkerhet.logg_ut_svar()


@app.route('/hilsen', methods=['POST'])
def ny_hilsen():
    bruker = sikkerhet.hent_bruker()
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

    kobling = database.koble()

    if svar_til is not None and database.hent_en(kobling, svar_til) is None:
        kobling.close()
        return flask.jsonify({'feil': 'Hilsenen du svarte på finnes ikke lenger.'}), 404

    ny_id = database.lagre_hilsen(kobling, tekst, svar_til, bruker['id'])
    hilsen = database.hent_en(kobling, ny_id)
    hilsen['antall'] = database.tell(kobling)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['PUT'])
def endre_hilsen(hilsen_id):
    bruker = sikkerhet.hent_bruker()
    if bruker is None:
        return flask.jsonify({'feil': 'Du må logge inn for å endre.'}), 401

    data = flask.request.get_json(silent=True) or {}
    tekst, feil = les_tekst(data)
    if feil:
        return flask.jsonify({'feil': feil}), 400

    kobling = database.koble()
    hilsen, feilsvar = finn_egen_hilsen(kobling, hilsen_id, bruker, 'endre')

    if feilsvar:
        kobling.close()
        return feilsvar

    database.endre_tekst(kobling, hilsen_id, tekst)
    hilsen = database.hent_en(kobling, hilsen_id)
    hilsen['kort'] = database.kort_tekst(tekst)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['DELETE'])
def slett_hilsen(hilsen_id):
    bruker = sikkerhet.hent_bruker()
    if bruker is None:
        return flask.jsonify({'feil': 'Du må logge inn for å slette.'}), 401

    kobling = database.koble()
    hilsen, feilsvar = finn_egen_hilsen(kobling, hilsen_id, bruker, 'slette')

    if feilsvar:
        kobling.close()
        return feilsvar

    ider = database.slett_traad(kobling, hilsen_id)
    antall = database.tell(kobling)
    kobling.close()

    return flask.jsonify({'slettet': ider, 'antall': antall})


@app.errorhandler(404)
def ikke_funnet(feil):
    if flask.request.path.startswith('/api/') or flask.request.method != 'GET':
        return flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404
    return flask.render_template('404.html'), 404


database.lag_tabell()


if __name__ == '__main__':
    app.run(debug=True)
