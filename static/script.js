const felt = document.getElementById("hilsen-input");
const liste = document.getElementById("hilsen-liste");
const teller = document.getElementById("teller");
const feilmelding = document.getElementById("feilmelding");
const tomMelding = document.getElementById("tom-melding");
const antallUt = document.getElementById("antall");
const svarLinje = document.getElementById("svarer");
const svarTekst = document.getElementById("svarer-tekst");
const avbrytKnapp = document.getElementById("avbryt-svar");
const maks = felt ? felt.maxLength : 0;

let sender = false;
let svarerTil = null;
let redigerer = null;

async function send(url, metode, kropp) {
  const svar = await fetch(url, {
    method: metode,
    headers: kropp ? { "Content-Type": "application/json" } : {},
    body: kropp ? JSON.stringify(kropp) : null,
  });
  return { ok: svar.ok, data: await svar.json() };
}

function lag(tag, klasse, tekst) {
  const element = document.createElement(tag);
  element.className = klasse;
  if (tekst !== undefined) {
    element.textContent = tekst;
  }
  return element;
}

function lagSitat(id, kort) {
  const sitat = lag("span", "sitat", "Svar til: " + kort);
  sitat.dataset.svarTil = id;
  return sitat;
}

function lagEndret(tidspunkt) {
  const merke = lag("span", "endret", "endret");
  merke.title = "Endret " + tidspunkt;
  return merke;
}

function lagRad(hilsen) {
  const rad = lag("li", "");
  rad.dataset.id = hilsen.id;

  const innhold = lag("div", "innhold");
  if (hilsen.svar_kort) {
    innhold.appendChild(lagSitat(hilsen.svar_til, hilsen.svar_kort));
  }
  innhold.appendChild(lag("span", "tekst", hilsen.tekst));

  const handlinger = lag("span", "handlinger");
  ["Svar", "Rediger", "Slett"].forEach(function (navn) {
    const knapp = lag("button", "", navn);
    knapp.type = "button";
    knapp.dataset.handling = navn.toLowerCase();
    handlinger.appendChild(knapp);
  });
  innhold.appendChild(handlinger);

  rad.appendChild(innhold);
  rad.appendChild(lag("span", "tid", hilsen.navn + " · " + hilsen.tidspunkt));
  return rad;
}

function finnSvar(id) {
  return liste.querySelectorAll('.sitat[data-svar-til="' + id + '"]');
}

function settAntall(antall) {
  antallUt.textContent = String(antall).padStart(2, "0");
  tomMelding.hidden = antall > 0;
}

function startSvar(rad) {
  svarerTil = Number(rad.dataset.id);
  svarTekst.textContent = rad.querySelector(".tekst").textContent;
  svarLinje.hidden = false;
  feilmelding.textContent = "";
  felt.focus();
}

function stoppSvar() {
  svarerTil = null;
  svarTekst.textContent = "";
  svarLinje.hidden = true;
}

function stoppRediger() {
  if (!redigerer) {
    return;
  }

  const rad = redigerer;
  redigerer = null;
  rad.querySelector(".rediger-felt").remove();
  rad.querySelector(".rediger-hjelp").remove();
  rad.querySelector(".tekst").hidden = false;
  rad.querySelector(".handlinger").hidden = false;
}

async function lagreRediger(rad, redigerFelt) {
  const tekst = redigerFelt.value.trim();
  const tekstUt = rad.querySelector(".tekst");
  const id = Number(rad.dataset.id);

  if (tekst === "") {
    return;
  }

  if (tekst === tekstUt.textContent) {
    stoppRediger();
    felt.focus();
    return;
  }

  try {
    const svar = await send("/hilsen/" + id, "PUT", { tekst: tekst });

    if (!svar.ok) {
      feilmelding.textContent = svar.data.feil;
      return;
    }

    tekstUt.textContent = svar.data.tekst;

    const merke = rad.querySelector(".endret");
    if (merke) {
      merke.remove();
    }
    tekstUt.after(lagEndret(svar.data.endret));

    finnSvar(id).forEach(function (sitat) {
      sitat.textContent = "Svar til: " + svar.data.kort;
    });

    if (svarerTil === id) {
      svarTekst.textContent = svar.data.tekst;
    }

    feilmelding.textContent = "";
    stoppRediger();
    felt.focus();
  } catch (error) {
    feilmelding.textContent = "Fikk ikke kontakt med serveren.";
  }
}

function startRediger(rad) {
  if (redigerer === rad) {
    return;
  }

  stoppRediger();
  redigerer = rad;

  const tekst = rad.querySelector(".tekst");
  const redigerFelt = lag("input", "rediger-felt");
  redigerFelt.type = "text";
  redigerFelt.maxLength = maks;
  redigerFelt.value = tekst.textContent;
  redigerFelt.setAttribute("aria-label", "Endre hilsenen");

  redigerFelt.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      stoppRediger();
      felt.focus();
    } else if (e.key === "Enter") {
      lagreRediger(rad, redigerFelt);
    }
  });

  tekst.hidden = true;
  rad.querySelector(".handlinger").hidden = true;
  rad.querySelector(".innhold").append(
    redigerFelt,
    lag("span", "rediger-hjelp", "Esc for å avbryte · Enter for å lagre")
  );

  redigerFelt.focus();
  redigerFelt.setSelectionRange(maks, maks);
}

async function slett(rad) {
  const id = Number(rad.dataset.id);
  const sporsmal = finnSvar(id).length > 0
    ? "Slette hilsenen og svarene på den?"
    : "Slette denne hilsenen?";

  if (!window.confirm(sporsmal)) {
    return;
  }

  try {
    const svar = await send("/hilsen/" + id, "DELETE");

    if (!svar.ok) {
      feilmelding.textContent = svar.data.feil;
      return;
    }

    svar.data.slettet.forEach(function (slettetId) {
      const slettetRad = liste.querySelector('li[data-id="' + slettetId + '"]');

      if (redigerer === slettetRad) {
        redigerer = null;
      }
      if (svarerTil === slettetId) {
        stoppSvar();
      }
      if (slettetRad) {
        slettetRad.remove();
      }
    });

    settAntall(svar.data.antall);
    feilmelding.textContent = "";
  } catch (error) {
    feilmelding.textContent = "Fikk ikke kontakt med serveren.";
  }
}

function wireGjestebok() {
  liste.addEventListener("click", function (e) {
    const knapp = e.target.closest("button[data-handling]");
    if (!knapp) {
      return;
    }

    const rad = knapp.closest("li");
    if (knapp.dataset.handling === "svar") {
      startSvar(rad);
    } else if (knapp.dataset.handling === "rediger") {
      startRediger(rad);
    } else {
      slett(rad);
    }
  });

  avbrytKnapp.addEventListener("click", function () {
    stoppSvar();
    felt.focus();
  });

  felt.addEventListener("input", function () {
    teller.textContent = felt.value.length + "/" + maks;
    teller.classList.toggle("naer-grensa", felt.value.length > maks - 20);
    feilmelding.textContent = "";
  });

  felt.addEventListener("keydown", async function (e) {
    if (e.key === "Escape") {
      stoppSvar();
      return;
    }

    const tekst = felt.value.trim();
    if (e.key !== "Enter" || sender || tekst === "") {
      return;
    }

    sender = true;

    try {
      const svar = await send("/hilsen", "POST", { tekst: tekst, svar_til: svarerTil });

      if (!svar.ok) {
        feilmelding.textContent = svar.data.feil;
        return;
      }

      liste.insertBefore(lagRad(svar.data), liste.firstChild);
      settAntall(svar.data.antall);
      stoppSvar();
      felt.value = "";
      teller.textContent = "0/" + maks;
      teller.classList.remove("naer-grensa");
    } catch (error) {
      feilmelding.textContent = "Fikk ikke kontakt med serveren.";
    } finally {
      sender = false;
    }
  });
}

if (felt) {
  wireGjestebok();
}

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
