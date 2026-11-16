// Safe HTML escaper to prevent XSS from user notes, location names, or advisories
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeExternalUrl(value) {
  try {
    const url = new URL(value, window.location.origin);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

// Parse FastAPI HTTPException strings or 422 validation error arrays
function formatApiError(errorData, status) {
  if (!errorData || !errorData.detail) {
    return `Request failed with status ${status}`;
  }
  if (Array.isArray(errorData.detail)) {
    return errorData.detail
      .map((err) => {
        const field = err.loc ? err.loc[err.loc.length - 1] : "field";
        return `${field}: ${err.msg}`;
      })
      .join(" | ");
  }
  return String(errorData.detail);
}

function showError(message) {
  const banner = document.getElementById("error-banner");
  const text = document.getElementById("error-text");
  text.textContent = message;
  banner.style.display = "flex";
}

function hideError() {
  document.getElementById("error-banner").style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  loadHistory();
});

function appendMessage(role, htmlContent) {
  const chat = document.getElementById("chat");
  const msgDiv = document.createElement("div");
  msgDiv.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === "user" ? "You" : "Weather";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = htmlContent;

  msgDiv.appendChild(avatar);
  msgDiv.appendChild(bubble);
  chat.appendChild(msgDiv);
  chat.scrollTop = chat.scrollHeight;
}

// CRUD: Create
async function handleSend(event) {
  if (event) event.preventDefault();
  hideError();

  const inputEl = document.getElementById("location-input");
  const sendBtn = document.getElementById("send-btn");
  const query = inputEl.value.trim();
  if (!query) return;

  appendMessage("user", escapeHtml(query));
  inputEl.value = "";
  sendBtn.disabled = true;
  sendBtn.textContent = "Fetching...";

  try {
    const res = await fetch("/chat-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data, res.status));
    }

    renderWeatherBubble(data);
    await loadHistory();
  } catch (err) {
    const msg = err.message || "Failed to fetch weather data.";
    showError(msg);
    const heading = "Request error";
    appendMessage("assistant", `<span class="error-inline"><strong>${heading}:</strong> ${escapeHtml(msg)}</span>`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = "Send";
  }
}

function renderWeatherBubble(record) {
  const weather = record.weather_summary || {};
  const daily = Array.isArray(weather.daily) ? weather.daily : [];

  let dailyHtml = "";
  if (daily.length > 0) {
    dailyHtml =
      `<div class="weather-grid">` +
      daily
        .map(
          (d) => `
          <div class="day-card">
            <strong>${escapeHtml(d.date)}</strong><br/>
            🌡️ ${escapeHtml(d.temp_min_c)}° – ${escapeHtml(d.temp_max_c)}°C<br/>
            🌧️ ${escapeHtml(d.precipitation_mm ?? 0)} mm<br/>
            ☀️ UV: ${escapeHtml(d.uv_index_max ?? "N/A")}
          </div>
        `
        )
        .join("") +
      `</div>`;
  }

  let linksHtml = `<div class="links-row">`;
  if (record.google_maps_url) {
    linksHtml += `<a href="${escapeHtml(safeExternalUrl(record.google_maps_url))}" target="_blank" rel="noopener noreferrer">🗺️ Open in Google Maps ↗</a>`;
  }
  const ytLinks = weather.youtube_videos || [];
  if (Array.isArray(ytLinks)) {
    ytLinks.forEach((yt) => {
      if (yt.url && yt.title) {
        linksHtml += `<a href="${escapeHtml(safeExternalUrl(yt.url))}" target="_blank" rel="noopener noreferrer">▶️ ${escapeHtml(yt.title)} ↗</a>`;
      }
    });
  }
  linksHtml += `</div>`;

  const locationTitle = escapeHtml(
    record.resolved_location || record.raw_location_input
  );

  const html = `
    <div><strong>📍 ${locationTitle}</strong> ${record.country ? `(${escapeHtml(record.country)})` : ""}</div>
    <div class="weather-meta-line">
      Range: ${escapeHtml(record.start_date)} to ${escapeHtml(record.end_date)}
      ${
        record.current_temp_c !== null
          ? ` • Local time: <strong>${escapeHtml(weather.local_time || "Unavailable")}</strong> • Now: <strong>${escapeHtml(record.current_temp_c)}°C</strong> (Humidity: ${escapeHtml(weather.current_humidity_pct)}%, Wind: ${escapeHtml(weather.current_wind_kmh)} km/h)`
          : ""
      }
    </div>
    ${dailyHtml}
    ${record.travel_advisory ? `<div class="advisory-box"><strong>🧭 Travel Advisory:</strong><br/>${escapeHtml(record.travel_advisory)}</div>` : ""}
    ${linksHtml}
  `;

  appendMessage("assistant", html);
}

// Browser Geolocation Handler
function useCurrentLocation() {
  const geoBtn = document.getElementById("geo-btn");
  const locationInput = document.getElementById("location-input");
  hideError();

  if (!navigator.geolocation) {
    showError("Geolocation is not supported by your browser.");
    return;
  }

  geoBtn.disabled = true;
  geoBtn.textContent = "Locating...";

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude.toFixed(4);
      const lon = position.coords.longitude.toFixed(4);
      locationInput.value = `${lat}, ${lon}`;

      geoBtn.disabled = false;
      geoBtn.textContent = "📍 Current Location";

      handleSend();
    },
    (error) => {
      geoBtn.disabled = false;
      geoBtn.textContent = "📍 Current Location";

      const messages = {
        1: "Location permission denied. Please allow access or enter a location manually.",
        2: "Location information is unavailable right now.",
        3: "Location request timed out. Please try again."
      };
      showError(messages[error.code] || "Unable to retrieve your location.");
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
  );
}

// CRUD: Read All
async function loadHistory() {
  const listEl = document.getElementById("historyList");
  try {
    const res = await fetch("/weather-queries");
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data, res.status));
    }

    listEl.innerHTML = "";
    if (!Array.isArray(data) || data.length === 0) {
      listEl.innerHTML = `<div class="history-empty">No saved queries yet.</div>`;
      return;
    }

    data.forEach((rec) => {
      const item = document.createElement("div");
      item.className = "history-item";
      const displayName = escapeHtml(
        rec.resolved_location || rec.raw_location_input
      );

      item.innerHTML = `
        <div class="history-item-header">
          <span>${displayName}</span>
          <span>${rec.current_temp_c !== null && rec.current_temp_c !== undefined ? `${escapeHtml(rec.current_temp_c)}°C` : "Historical"}</span>
        </div>
        <div class="history-meta">${escapeHtml(rec.start_date)} → ${escapeHtml(rec.end_date)}</div>
        ${rec.user_notes ? `<div class="history-note">Note: ${escapeHtml(rec.user_notes)}</div>` : ""}
        <div class="history-actions">
          <button type="button" class="btn" data-action="view">View</button>
          <button type="button" class="btn" data-action="note">Note</button>
          <button type="button" class="btn btn-danger" data-action="delete">Delete</button>
        </div>
      `;

      // Bind event listeners safely instead of inline string interpolation
      item.querySelector('[data-action="view"]').addEventListener("click", () => viewRecord(rec.id));
      item.querySelector('[data-action="note"]').addEventListener("click", () => editNote(rec.id, rec.user_notes || ""));
      item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteRecord(rec.id));

      listEl.appendChild(item);
    });
  } catch (err) {
    showError(err.message);
  }
}

// CRUD: Read One
async function viewRecord(id) {
  hideError();
  try {
    const res = await fetch(`/weather-queries/${id}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data, res.status));
    }
    renderWeatherBubble(data);
  } catch (err) {
    showError(err.message);
  }
}

// CRUD: Update Note
async function editNote(id, currentNote) {
  const newNote = prompt("Enter travel note for this record:", currentNote);
  if (newNote === null) return;
  hideError();

  try {
    const res = await fetch(`/weather-queries/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_notes: newNote })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(data, res.status));
    }
    await loadHistory();
  } catch (err) {
    showError(err.message);
  }
}

// CRUD: Delete
async function deleteRecord(id) {
  if (!confirm("Delete this weather record?")) return;
  hideError();

  try {
    const res = await fetch(`/weather-queries/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(formatApiError(data, res.status));
    }
    await loadHistory();
  } catch (err) {
    showError(err.message);
  }
}

// Export
function exportData(format) {
  window.open(`/weather-queries/export?format=${encodeURIComponent(format)}`, "_blank");
}

// About Info
async function showAbout() {
  hideError();
  try {
    const res = await fetch("/about");
    const info = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(formatApiError(info, res.status));
    }
    appendMessage(
      "assistant",
      `
      <strong>ℹ️ About This Project</strong><br/>
      • <strong>Developer:</strong> ${escapeHtml(info.developer || "Nitin Madanala")}<br/>
      • <strong>Track:</strong> ${escapeHtml(info.role_track || "PM Accelerator Tech Assessment")}<br/>
      • <strong>Program:</strong> ${escapeHtml(info.pm_accelerator_description || info.organization || "Product Manager Accelerator")}
    `
    );
  } catch (err) {
    showError(err.message);
  }
}