import os
import re
import secrets

BILDEMAPPE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'img', 'kontakter')
MAKS_BILDE = 2 * 1024 * 1024

FELTER = [
    ('fornavn', 'Fornavn', 40),
    ('etternavn', 'Etternavn', 40),
    ('by', 'By', 40),
    ('epost', 'E-post', 60),
    ('telefon', 'Telefon', 20),
]

SIGNATURER = [
    (b'\xff\xd8\xff', '.jpg'),
    (b'\x89PNG\r\n\x1a\n', '.png'),
    (b'GIF87a', '.gif'),
    (b'GIF89a', '.gif'),
]

EPOST_MONSTER = re.compile(r'^[^@\s]+@[^@\s]+\.[A-Za-zÆØÅæøå]{2,}$')
TELEFON_MONSTER = re.compile(r'^[0-9 +]{5,20}$')
FILNAVN_MONSTER = re.compile(r'^[0-9a-f]{32}\.(jpg|png|gif|webp)$')


def les_felter(skjema):
    verdier = {}

    for navn, merkelapp, lengde in FELTER:
        verdi = skjema.get(navn, '').strip()

        if not verdi:
            return None, f'{merkelapp} må fylles ut.'
        if len(verdi) > lengde:
            return None, f'{merkelapp} kan ikke være lengre enn {lengde} tegn.'

        verdier[navn] = verdi

    if not EPOST_MONSTER.match(verdier['epost']):
        return None, 'E-posten må se ut som navn@domene.no.'

    if not TELEFON_MONSTER.match(verdier['telefon']):
        return None, 'Telefonnummeret kan bare ha tall, mellomrom og +.'

    return verdier, None


def finn_type(start):
    for signatur, etternavn in SIGNATURER:
        if start.startswith(signatur):
            return etternavn

    if start[:4] == b'RIFF' and start[8:12] == b'WEBP':
        return '.webp'

    return None


def lagre_bilde(fil):
    if fil is None or not fil.filename:
        return None, None

    innhold = fil.read(MAKS_BILDE + 1)

    if len(innhold) > MAKS_BILDE:
        return None, 'Bildet kan ikke være større enn 2 MB.'

    etternavn = finn_type(innhold[:16])
    if etternavn is None:
        return None, 'Bildet må være JPG, PNG, GIF eller WEBP.'

    os.makedirs(BILDEMAPPE, exist_ok=True)
    filnavn = secrets.token_hex(16) + etternavn

    with open(os.path.join(BILDEMAPPE, filnavn), 'wb') as ut:
        ut.write(innhold)

    return filnavn, None


def slett_bilde(filnavn):
    if not filnavn or not FILNAVN_MONSTER.match(filnavn):
        return

    sti = os.path.join(BILDEMAPPE, filnavn)
    if os.path.isfile(sti):
        os.remove(sti)
