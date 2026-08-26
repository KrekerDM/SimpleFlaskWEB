const felt = document.getElementById("hilsen-input");
const liste = document.getElementById("hilsen-liste");
const teller = document.getElementById("teller");
const feilmelding = document.getElementById("feilmelding");
const tomMelding = document.getElementById("tom-melding");
const antallUt = document.getElementById("antall");
const maks = felt.maxLength;

let sender = false;

function vis(tekst, tidspunkt) {
  const rad = document.createElement("li");

  const innhold = document.createElement("span");
  innhold.className = "tekst";
  innhold.textContent = tekst;

  const stempel = document.createElement("span");
  stempel.className = "tid";
  stempel.textContent = tidspunkt;

  rad.appendChild(innhold);
  rad.appendChild(stempel);
  liste.insertBefore(rad, liste.firstChild);
  tomMelding.hidden = true;
}

function nullstillFelt() {
  felt.value = "";
  teller.textContent = "0/" + maks;
  teller.classList.remove("naer-grensa");
}

felt.addEventListener("input", function () {
  const lengde = felt.value.length;
  teller.textContent = lengde + "/" + maks;
  teller.classList.toggle("naer-grensa", lengde > maks - 20);
  feilmelding.textContent = "";
});

felt.addEventListener("keydown", async function (e) {
  if (e.key !== "Enter" || sender) {
    return;
  }

  const tekst = felt.value.trim();
  if (tekst === "") {
    return;
  }

  sender = true;

  try {
    const svar = await fetch("/hilsen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tekst: tekst }),
    });
    const data = await svar.json();

    if (!svar.ok) {
      feilmelding.textContent = data.feil;
      return;
    }

    vis(data.tekst, data.tidspunkt);
    antallUt.textContent = String(data.antall).padStart(2, "0");
    nullstillFelt();
  } catch (error) {
    feilmelding.textContent = "Fikk ikke kontakt med serveren.";
  } finally {
    sender = false;
  }
});

// vise bilder 
const visning = document.getElementById("visning");
const visningBilde = document.getElementById("visning-bilde");
const visningTekst = document.getElementById("visning-tekst");

document.querySelectorAll(".vis").forEach(function (knapp) {
  knapp.addEventListener("click", function () {
    const bilde = knapp.querySelector("img");
    visningBilde.src = bilde.src;
    visningBilde.alt = bilde.alt;
    visningTekst.textContent = knapp.closest("figure").querySelector("figcaption").textContent;
    visning.showModal();
  });
});

visning.addEventListener("click", function (e) {
  if (e.target === visning) {
    visning.close();
  }
});
