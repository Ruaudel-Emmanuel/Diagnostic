const API_BASE_URL = "https://api.rennesdev.fr";

const form = document.getElementById("diagnostic-form");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("result");
const resultLevel = document.getElementById("result-level");
const resultScore = document.getElementById("result-score");
const resultActions = document.getElementById("result-actions");
const resultJson = document.getElementById("result-json");
const submitBtn = document.getElementById("submit-btn");

function getCheckedValues(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((el) => el.value);
}

function buildPayload() {
  return {
    answers: {
      Q01: document.getElementById("Q01").value,
      Q03: document.getElementById("Q03").value,
      Q05: getCheckedValues("Q05"),
      Q08: document.getElementById("Q08").value,
      Q10: document.getElementById("Q10").value,
      Q12: document.getElementById("Q12").value,
      Q15: document.getElementById("Q15").value,
      Q16B: document.getElementById("Q16B").value,
      Q16C: document.getElementById("Q16C").value,
      Q17: document.getElementById("Q17").value,
      Q18: document.getElementById("Q18").value,
      Q19A: document.getElementById("Q19A").value,
      Q19B: document.getElementById("Q19B").value,
      Q20: Number(document.getElementById("Q20").value)
    },
    max_actions: 3
  };
}

function renderResult(data) {
  resultLevel.textContent = data.level || "-";
  resultLevel.className = `big level-${data.level || ""}`;
  resultScore.textContent = String(data.score ?? "-");

  resultActions.innerHTML = "";
  (data.top_actions || []).forEach((action) => {
    const li = document.createElement("li");
    li.textContent = action;
    resultActions.appendChild(li);
  });

  resultJson.textContent = JSON.stringify(data, null, 2);
  resultSection.classList.remove("hidden");
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = buildPayload();
  statusEl.textContent = "Analyse en cours...";
  submitBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE_URL}/diagnostic`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(JSON.stringify(data));
    }

    renderResult(data);
    statusEl.textContent = "Diagnostic généré avec succès.";
  } catch (error) {
    resultSection.classList.remove("hidden");
    resultLevel.textContent = "Erreur";
    resultLevel.className = "big level-en_retard";
    resultScore.textContent = "-";
    resultActions.innerHTML = "<li>Vérifiez que l’API VPS est bien accessible et que le CORS est configuré si nécessaire.</li>";
    resultJson.textContent = String(error);
    statusEl.textContent = "Échec de l’appel API.";
  } finally {
    submitBtn.disabled = false;
  }
});
