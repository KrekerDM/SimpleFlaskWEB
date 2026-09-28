Første gang: `pip install flask flask_login`. Deretter `python app.py`, så ligger siden på <http://127.0.0.1:5000>.
`app.py` er serveren, `index.html` er siden, `skjema.html` er innlogging og registrering, `style.css` er utseendet og `script.js` sender hilsenen.
Alle sidene arver fra `base.html` med `extends`, så hodet med skrift og stilark står bare ett sted, og hver side fyller inn blokkene `tittel`, `overskrift` og `innhold`.
En hilsen tegnes av `hilsen.html`, som både forsiden og søkesida henter inn, så en hilsen ser like ut begge steder.
I mappa `deler` ligger modulene serveren bygger på: `database.py` gjør alt mot SQLite, `sikkerhet.py` tar seg av passord og innlogging, og `kontakter.py` sjekker kontaktfeltene og tar imot bildet.
`app.py` importerer begge og inneholder bare rutene, altså hva som skal skje på hver adresse.
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
Slett spør først, og tar hilsenen sammen med dine egne svar i tråden.
Svar fra andre står igjen og mister bare sitatlinja, så ingen kan slette det andre har skrevet.
Serveren tar imot dette på `POST /hilsen`, `PUT /hilsen/<id>` og `DELETE /hilsen/<id>`, og sjekker teksten på nytt der også.

For å skrive må du ha bruker. `/registrer` lager en, `/logg-inn` logger deg inn og `/logg-ut` ut igjen.
Brukernavnet må ha 3–20 tegn, og passordet minst 8.
Selve innlogginga er `flask_login`. Den holder styr på hvem som er logget inn, `@login_required` stenger rutene som krever bruker, og i malene sjekker jeg `current_user.is_authenticated`.
Passordet lagres aldri slik du skrev det. Det køres gjennom PBKDF2 med 200 000 runder og et tilfeldig salt, og bare resultatet havner i `brukere`-tabellen.
Det er med vilje en enveisfunksjon: hadde jeg kryptert passordene i stedet, kunne den som fikk tak i nøkkelen lest alle sammen.
Sesjonskaka til `flask_login` er signert med en nøkkel som ligger i `nokkel.bin` og lages automatisk første gang serveren starter, så en tuklet kake blir bare regnet som utlogget.
Alle skjemaer sender også et CSRF-token fra sesjonen, og `sjekk_csrf` avviser POST, PUT og DELETE uten riktig token.
Både det lagrede og det innsendte tokenet må ha innhold, ellers ville to tomme strenger vært like og sjekken sluppet forbi.
Det stopper et annet nettsted fra å slette noe på dine vegne.
Hvert svar får også `X-Content-Type-Options: nosniff`, slik at nettleseren ikke kan gjette at et opplastet bilde egentlig er HTML, og `X-Frame-Options: DENY` mot klikkjacking.
Navnet ditt står ved hilsenene dine, du kan svare på alle, men bare endre og slette dine egne. Hilsener fra før innlogginga kom har ingen eier, så de står uten navn.

Oppgave 6 er kontaktlista, som ligger under lenka Kontakter.
Hver kontakt har fornavn, etternavn, by, e-post og telefon, og et bilde.
Lista viser navn og by, og knappen Detaljer åpner en egen side for den kontakten der alle feltene står sammen med bildet.
Er du ikke logget inn ser du hele lista og kan åpne detaljer, men knappene Ny, Endre og Slett finnes ikke i det hele tatt.
Er du logget inn har du alle rettigheter. Rutene er også stengt med `@login_required`, ikke bare skjult i malen, så det hjelper ikke å sende POST direkte.
Kontaktene ligger i tabellen `kontakter` i samme `hilsener.db`.
E-posten og telefonnummeret sjekkes med hvert sitt mønster, og hvert felt har en makslångde.
Bildet godtas bare hvis de første bytene i fila viser at det faktisk er JPG, PNG, GIF eller WEBP.
Jeg stoler altså ikke på filnavnet brukeren sender, men lager et nytt tilfeldig navn selv, så ingen kan skrive utenfor `static/img/kontakter`.
Filer over 2 MB blir avvist før de leses inn, og det gamle bildet slettes når du bytter det ut eller sletter kontakten.

Klikker du på et bilde åpnes det i full størrelse, og du lukker det med Esc.
Skriver du feil adresse får du min egen 404-side i stedet for feilsiden til Flask.
Nederst ligger `/api/hilsener` som viser alle hilsenene som JSON.

Øverst på hver side ligger lenka Søk. Der skriver du et ord i feltet, og `sok_i_hilsener` går gjennom alle hilsenene og tar med de som har ordet i seg.
Den leter etter ordet hvor som helst i teksten, ikke bare i starten, så søk på `dag` finner også «Gratulerer med dagen».
Store og små bokstaver spiller ingen rolle, fordi jeg gjør begge deler om til små bokstaver med `lower()` først.
Under hvert treff ligger et lite skjema, så du kan svare med en gang. Svaret lagres med `svar_til` som peker på hilsenen du svarte på, og du kommer tilbake til samme søk etterpå.
Toppmenyen ligger i `topp.html` og hentes inn i både `index.html` og `sok.html` med `include`, så den står bare ett sted.
Siden ser ut som et databladark fordi jeg driver med FPV, og alle dronedeler kommer med et sånt ark.
Skrifta er Roboto Slab.

Jeg spurte KI om hvordan `fetch` sender JSON, forskjellen på `textContent` og `innerHTML`, hva `<dialog>` er, hvordan `PUT` og `DELETE` fungerer i Flask, hvorfor passord skal hashes og ikke krypteres, og hvordan `flask_login` holder rede på hvem som er logget inn. Resten er fra w3schools.
