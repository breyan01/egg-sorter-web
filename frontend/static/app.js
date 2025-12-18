async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("Failed to fetch stats");
    const data = await res.json();
    updateDashboard(data);
  } catch (err) {
    console.error(err);
  }
}

function updateDashboard(data) {
  // Total
  document.getElementById("total-eggs").textContent = data.total ?? 0;

  // Sizes
  const sizeSpans = document.querySelectorAll("#size-list span[data-size]");
  sizeSpans.forEach((span) => {
    const key = span.getAttribute("data-size");
    span.textContent = data.sizes[key] ?? 0;
  });

  // Quality
  const qualitySpans = document.querySelectorAll(
    "#quality-list span[data-quality]"
  );
  qualitySpans.forEach((span) => {
    const key = span.getAttribute("data-quality");
    span.textContent = data.quality[key] ?? 0;
  });

  // Recent table
  const tbody = document.getElementById("recent-table-body");
  tbody.innerHTML = "";

  (data.recent || []).forEach((egg) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${egg.id}</td>
      <td>${egg.size}</td>
      <td>${egg.color}</td>
      <td>${egg.quality}</td>
      <td>${formatTimestamp(egg.timestamp)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function formatTimestamp(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts; // fallback
  return d.toLocaleString();
}

async function addEgg(event) {
  event.preventDefault();
  const form = event.target;
  const status = document.getElementById("form-status");
  status.textContent = "";
  status.className = "";

  const payload = {
    size: form.size.value,
    color: form.color.value,
    quality: form.quality.value,
  };

  try {
    const res = await fetch("/api/egg", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || "Failed to add egg");
    }

    status.textContent = "Egg added!";
    status.classList.add("ok");
    await fetchStats();
  } catch (err) {
    console.error(err);
    status.textContent = err.message;
    status.classList.add("error");
  }
}

async function resetData() {
  if (!confirm("Reset all egg data?")) return;
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset");
    await fetchStats();
  } catch (err) {
    console.error(err);
    alert("Error resetting data: " + err.message);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  fetchStats();

  // Refresh button
  document.getElementById("refresh-btn").addEventListener("click", fetchStats);

  // Reset button
  document.getElementById("reset-btn").addEventListener("click", resetData);

  // Add-egg form
  document
    .getElementById("add-egg-form")
    .addEventListener("submit", addEgg);

  // Optional: auto-refresh every 5 seconds
  setInterval(fetchStats, 5000);
});
