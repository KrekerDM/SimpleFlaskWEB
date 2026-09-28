import re
from datetime import date

import flask
import flask_login

from deler import database, kontakter, sikkerhet

app = flask.Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = kontakter.MAKS_BILDE + 64 * 1024
sikkerhet.koble_til_app(app)

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


def finn_egen_hilsen(kobling, hilsen_id, handling):
    hilsen = database.hent_en(kobling, hilsen_id)

    if hilsen is None:
        return None, (flask.jsonify({'feil': 'Fant ikke hilsenen.'}), 404)

    if hilsen['bruker_id'] != flask_login.current_user.id:
        return None, (flask.jsonify({'feil': f'Du kan bare {handling} dine egne hilsener.'}), 403)

    return hilsen, None


def vis_sok(sokeord, feil=None):
    return flask.render_template(
        'sok.html',
        sokeord=sokeord,
        treff=database.sok_i_hilsener(sokeord) if sokeord else [],
        maks=MAKS_LENGDE,
        feil=feil,
    )


def vis_skjema(navn, feil=None):
    return flask.render_template(
        'skjema.html', handling='/' + navn, feil=feil, **SKJEMAER[navn]
    )


def vis_kontaktskjema(tittel, kontakt, feil=None):
    return flask.render_template(
        'kontaktskjema.html', tittel=tittel, kontakt=kontakt, felter=kontakter.FELTER, feil=feil
    )


@app.route('/')
def forside():
    hilsener = database.hent_alle()
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
    hilsener = database.hent_alle()
    return flask.jsonify({'antall': len(hilsener), 'hilsener': hilsener})


@app.route('/kontakter')
def kontaktliste():
    return flask.render_template('kontakter.html', kontakter=database.hent_kontakter())


@app.route('/kontakter/<int:kontakt_id>')
def kontaktdetaljer(kontakt_id):
    kontakt = database.hent_kontakt(kontakt_id)
    if kontakt is None:
        flask.abort(404)
    return flask.render_template('kontakt.html', kontakt=kontakt)


@app.route('/kontakter/ny', methods=['GET', 'POST'])
@flask_login.login_required
def ny_kontakt():
    if flask.request.method == 'GET':
        return vis_kontaktskjema('Ny kontakt', {})

    felter, feil = kontakter.les_felter(flask.request.form)
    if feil:
        return vis_kontaktskjema('Ny kontakt', flask.request.form, feil), 400

    filnavn, feil = kontakter.lagre_bilde(flask.request.files.get('bilde'))
    if feil:
        return vis_kontaktskjema('Ny kontakt', flask.request.form, feil), 400

    kontakt_id = database.lagre_kontakt(felter, filnavn)
    return flask.redirect(flask.url_for('kontaktdetaljer', kontakt_id=kontakt_id))


@app.route('/kontakter/<int:kontakt_id>/endre', methods=['GET', 'POST'])
@flask_login.login_required
def endre_kontakt(kontakt_id):
    kontakt = database.hent_kontakt(kontakt_id)
    if kontakt is None:
        flask.abort(404)

    if flask.request.method == 'GET':
        return vis_kontaktskjema('Endre kontakt', kontakt)

    felter, feil = kontakter.les_felter(flask.request.form)
    if feil:
        return vis_kontaktskjema('Endre kontakt', flask.request.form, feil), 400

    filnavn, feil = kontakter.lagre_bilde(flask.request.files.get('bilde'))
    if feil:
        return vis_kontaktskjema('Endre kontakt', flask.request.form, feil), 400

    database.endre_kontakt(kontakt_id, felter)

    if filnavn:
        database.sett_bilde(kontakt_id, filnavn)
        kontakter.slett_bilde(kontakt['bilde'])

    return flask.redirect(flask.url_for('kontaktdetaljer', kontakt_id=kontakt_id))


@app.route('/kontakter/<int:kontakt_id>/slett', methods=['POST'])
@flask_login.login_required
def slett_kontakt(kontakt_id):
    kontakt = database.hent_kontakt(kontakt_id)
    if kontakt is None:
        flask.abort(404)

    database.slett_kontakt(kontakt_id)
    kontakter.slett_bilde(kontakt['bilde'])

    return flask.redirect('/kontakter')


@app.route('/sok')
def sok():
    return vis_sok(flask.request.args.get('ord', '').strip())


@app.route('/svar/<int:hilsen_id>', methods=['POST'])
@flask_login.login_required
def svar_pa(hilsen_id):
    sokeord = flask.request.form.get('ord', '').strip()

    tekst, feil = les_tekst(flask.request.form)
    if feil:
        return vis_sok(sokeord, feil), 400

    kobling = database.koble()

    if database.hent_en(kobling, hilsen_id) is None:
        kobling.close()
        return vis_sok(sokeord, 'Fant ikke hilsenen.'), 404

    database.lagre_hilsen(kobling, tekst, hilsen_id, flask_login.current_user.id)
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

    bruker = sikkerhet.lag_bruker(brukernavn, passord)
    if bruker is None:
        return vis_skjema('registrer', 'Brukernavnet er opptatt.'), 400

    flask_login.login_user(bruker)
    return flask.redirect(sikkerhet.trygg_neste())


@app.route('/logg-inn', methods=['GET', 'POST'])
def logg_inn():
    if flask.request.method == 'GET':
        return vis_skjema('logg-inn')

    brukernavn = flask.request.form.get('brukernavn', '').strip()
    passord = flask.request.form.get('passord', '')

    bruker = sikkerhet.sjekk_innlogging(brukernavn, passord)
    if bruker is None:
        return vis_skjema('logg-inn', 'Feil brukernavn eller passord.'), 401

    flask_login.login_user(bruker)
    return flask.redirect(sikkerhet.trygg_neste())


@app.route('/logg-ut', methods=['POST'])
@flask_login.login_required
def logg_ut():
    flask_login.logout_user()
    return flask.redirect('/')


@app.route('/hilsen', methods=['POST'])
@flask_login.login_required
def ny_hilsen():
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

    ny_id = database.lagre_hilsen(kobling, tekst, svar_til, flask_login.current_user.id)
    hilsen = database.hent_en(kobling, ny_id)
    hilsen['antall'] = database.tell(kobling)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['PUT'])
@flask_login.login_required
def endre_hilsen(hilsen_id):
    data = flask.request.get_json(silent=True) or {}
    tekst, feil = les_tekst(data)
    if feil:
        return flask.jsonify({'feil': feil}), 400

    kobling = database.koble()
    hilsen, feilsvar = finn_egen_hilsen(kobling, hilsen_id, 'endre')

    if feilsvar:
        kobling.close()
        return feilsvar

    database.endre_tekst(kobling, hilsen_id, tekst)
    hilsen = database.hent_en(kobling, hilsen_id)
    hilsen['kort'] = database.kort_tekst(tekst)
    kobling.close()

    return flask.jsonify(hilsen)


@app.route('/hilsen/<int:hilsen_id>', methods=['DELETE'])
@flask_login.login_required
def slett_hilsen(hilsen_id):
    kobling = database.koble()
    hilsen, feilsvar = finn_egen_hilsen(kobling, hilsen_id, 'slette')

    if feilsvar:
        kobling.close()
        return feilsvar

    ider = database.slett_traad(kobling, hilsen_id, flask_login.current_user.id)
    antall = database.tell(kobling)
    kobling.close()

    return flask.jsonify({'slettet': ider, 'antall': antall})


@app.errorhandler(404)
def ikke_funnet(feil):
    if flask.request.path.startswith('/api/') or flask.request.method != 'GET':
        return flask.jsonify({'feil': 'Fant ikke siden.'}), 404
    return flask.render_template('404.html'), 404


@app.errorhandler(413)
def for_stor(feil):
    return flask.jsonify({'feil': 'Filen er for stor. Bildet kan være maks 2 MB.'}), 413


database.lag_tabell()


if __name__ == '__main__':
    app.run(debug=True)
