Kjør `python app.py`, så ligger siden på <http://127.0.0.1:5000>.
`app.py` er serveren, `index.html` er siden, `style.css` er utseendet og `script.js` sender hilsenen.

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

Klikker du på et bilde åpnes det i full størrelse, og du lukker det med Esc.
Skriver du feil adresse får du min egen 404-side i stedet for feilsiden til Flask.
Nederst ligger `/api/hilsener` som viser alle hilsenene som JSON.
Siden ser ut som et databladark fordi jeg driver med FPV, og alle dronedeler kommer med et sånt ark.
Skrifta er Inter.

Jeg spurte KI om hvordan `fetch` sender JSON, forskjellen på `textContent` og `innerHTML`, hva `<dialog>` er, hvordan `PUT` og `DELETE` fungerer i Flask. Resten er fra w3schools.
