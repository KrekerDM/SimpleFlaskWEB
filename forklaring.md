Første gang: `pip install flask pycryptodome`. Deretter `python app.py`, så ligger siden på <http://127.0.0.1:5000>.
`app.py` er serveren, `index.html` er siden, `skjema.html` er innlogging og registrering, `style.css` er utseendet og `script.js` sender hilsenen.
`skjema.html` brukes til begge skjemaene, og hvilken tittel, knapp og bilde som skal stå der hentes fra `SKJEMAER` i `app.py`.

Oppgave 1: navn, telefon, e-post, fødselsdag og interesser står til høyre, bildet av meg til venstre
Oppgave 2: alt av farger, ramme og plassering ligger i `style.css`, og de sju fargene står som variabler øverst i fila
Oppgave 3: trykker du Enter i feltet sender `script.js` teksten til serveren
Oppgave 4: hilsenene ligger i en liste med den nyeste øverst
Oppgave 5: de lagres i `hilsener.db` og hentes opp igjen når siden lastes

Under hver hilsen ligger knappene Svar, Rediger og Slett.
Svar setter en linje over skrivefeltet som viser hva du svarer på, og hilsenen lagres med `svar_til` i databasen.
Da får svaret en sitatlinje som viser starten av hilsenen det hører til, og Esc eller Avbryt stopper svaret.
Rediger bytter teksten med et felt der Enter lagrer og Esc avbryter.
Serveren skriver da tidspunktet i `endret`, og lista viser ordet endret som du kan holde musa over for å se når.
Slett spør først, og tar hilsenen sammen med svarene som ligger under den, slik at ingen sitatlinjer peker på noe som er borte.
Serveren tar imot dette på `POST /hilsen`, `PUT /hilsen/<id>` og `DELETE /hilsen/<id>`, og sjekker teksten på nytt der også.

For å skrive må du ha bruker. `/registrer` lager en, `/logg-inn` logger deg inn og `/logg-ut` ut igjen.
Brukernavnet må ha 3–20 tegn, og passordet minst 8.
Passordet lagres aldri slik du skrev det. Det køres gjennom PBKDF2 med 200 000 runder og et tilfeldig salt, og bare resultatet havner i `brukere`-tabellen.
Det er med vilje en enveisfunksjon: hadde jeg kryptert passordene i stedet, kunne den som fikk tak i nøkkelen lest alle sammen.
AES-GCM bruker jeg der det hører hjemme, nemlig på innloggingskaka. Den inneholder bruker-ID-en min, kryptert med en 256-bits nøkkel som ligger i `nokkel.bin` og lages automatisk første gang serveren starter.
GCM sjekker også at kaka ikke er tuklet med, så en endret kake blir bare regnet som utlogget.
Navnet ditt står ved hilsenene dine, du kan svare på alle, men bare endre og slette dine egne. Hilsener fra før innlogginga kom har ingen eier, så de står uten navn.

Klikker du på et bilde åpnes det i full størrelse, og du lukker det med Esc.
Skriver du feil adresse får du min egen 404-side i stedet for feilsiden til Flask.
Nederst ligger `/api/hilsener` som viser alle hilsenene som JSON.
Siden ser ut som et databladark fordi jeg driver med FPV, og alle dronedeler kommer med et sånt ark.
Skrifta er Inter.

Jeg spurte KI om hvordan `fetch` sender JSON, forskjellen på `textContent` og `innerHTML`, hva `<dialog>` er, hvordan `PUT` og `DELETE` fungerer i Flask, og hvorfor passord skal hashes og ikke krypteres. Resten er fra w3schools.
