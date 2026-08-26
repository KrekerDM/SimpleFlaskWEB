Kjør `python app.py`, så ligger siden på <http://127.0.0.1:5000>.
`app.py` er serveren, `index.html` er siden, `style.css` er utseendet og `script.js` sender hilsenen.

Oppgave 1: navn, telefon, e-post, fødselsdag og interesser står til høyre, bildet av meg til venstre
Oppgave 2: alt av farger, ramme og plassering ligger i `style.css`
Oppgave 3: trykker du Enter i feltet sender `script.js` teksten til serveren
Oppgave 4: hilsenene ligger i en liste med den nyeste øverst
Oppgave 5: de lagres i `hilsener.db` og hentes opp igjen når siden lastes

Klikker du på et bilde åpnes det i full størrelse, og du lukker det med Esc.
Skriver du feil adresse får du min egen 404-side i stedet for feilsiden til Flask.
Nederst ligger `/api/hilsener` som viser alle hilsenene som JSON.
Siden ser ut som et databladark fordi jeg driver med FPV, og alle dronedeler kommer med et sånt ark.

Jeg spurte KI om hvordan `fetch` sender JSON, forskjellen på `textContent` og `innerHTML`, og hva `<dialog>` er. Resten er fra w3schools.
