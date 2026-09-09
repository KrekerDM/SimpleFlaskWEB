import os
import sqlite3
from datetime import datetime

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hilsener.db')
KORT_LENGDE = 40

SPORRING = """
    SELECT h.id, h.tekst, h.tidspunkt, h.endret, h.svar_til, h.bruker_id,
           b.brukernavn AS navn, s.tekst AS svar_tekst
    FROM hilsener h
    LEFT JOIN hilsener s ON s.id = h.svar_til
    LEFT JOIN brukere b ON b.id = h.bruker_id
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


def lagre_hilsen(kobling, tekst, svar_til, bruker_id):
    markor = kobling.execute(
        'INSERT INTO hilsener (tekst, tidspunkt, svar_til, bruker_id) VALUES (?, ?, ?, ?)',
        (tekst, naa(), svar_til, bruker_id),
    )
    kobling.commit()
    return markor.lastrowid


def endre_tekst(kobling, hilsen_id, tekst):
    kobling.execute(
        'UPDATE hilsener SET tekst = ?, endret = ? WHERE id = ?',
        (tekst, naa(), hilsen_id),
    )
    kobling.commit()


def slett_traad(kobling, hilsen_id):
    ider = [hilsen_id]
    for forelder in ider:
        for rad in kobling.execute('SELECT id FROM hilsener WHERE svar_til = ?', (forelder,)):
            ider.append(rad['id'])

    plasser = ','.join('?' for _ in ider)
    kobling.execute(f'DELETE FROM hilsener WHERE id IN ({plasser})', ider)
    kobling.commit()
    return ider


def tell(kobling):
    return kobling.execute('SELECT COUNT(*) FROM hilsener').fetchone()[0]


def sok_i_hilsener(sokeord):
    sokeord = sokeord.lower()
    return [h for h in hent_alle() if sokeord in h['tekst'].lower()]
