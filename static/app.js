const authCard = document.getElementById("authCard");
const dashboard = document.getElementById("dashboard");
const authMessage = document.getElementById("authMessage");
const submissionMessage = document.getElementById("submissionMessage");
const allocationMessage = document.getElementById("allocationMessage");
const meInfo = document.getElementById("meInfo");
const submissionsBody = document.getElementById("submissionsBody");
const allocationBody = document.getElementById("allocationBody");
const roommateFields = document.getElementById("roommateFields");
const adminCard = document.getElementById("adminCard");

let currentUser = null;

function getToken() {
  return localStorage.getItem("token");
}

function setToken(token) {
  localStorage.setItem("token", token);
}

function clearAuth() {
  localStorage.removeItem("token");
  currentUser = null;
}

async function api(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

function renderAuthMessage(text, isError = false) {
  authMessage.textContent = text;
  authMessage.className = isError ? "error" : "success";
}

function renderSubmissionMessage(text, isError = false) {
  submissionMessage.textContent = text;
  submissionMessage.className = isError ? "error" : "success";
}

function renderAllocationMessage(text, isError = false) {
  allocationMessage.textContent = text;
  allocationMessage.className = isError ? "error" : "success";
}

function toggleRoommateFields() {
  const wantsChange = document.getElementById("wantsChange").value === "true";
  roommateFields.classList.toggle("hidden", !wantsChange);
}

function renderDashboard() {
  if (!currentUser) return;
  authCard.classList.add("hidden");
  dashboard.classList.remove("hidden");
  meInfo.textContent = `${currentUser.full_name} (${currentUser.scholar_number}) | ${currentUser.hostel_number} / Room ${
    currentUser.room_number
  }${currentUser.is_admin ? " | Admin" : ""}`;
  adminCard.classList.toggle("hidden", !currentUser.is_admin);
}

async function loadMe() {
  currentUser = await api("/api/me");
  renderDashboard();
}

async function loadMySubmission() {
  const mySubmission = await api("/api/submission");
  if (!mySubmission) {
    document.getElementById("wantsChange").value = "false";
    document.getElementById("wantedName").value = "";
    document.getElementById("wantedScholar").value = "";
    document.getElementById("notes").value = "";
    toggleRoommateFields();
    return;
  }
  document.getElementById("wantsChange").value = String(mySubmission.wants_change);
  document.getElementById("wantedName").value = mySubmission.wanted_roommate_name || "";
  document.getElementById("wantedScholar").value = mySubmission.wanted_roommate_scholar_number || "";
  document.getElementById("notes").value = mySubmission.notes || "";
  toggleRoommateFields();
}

function renderSubmissions(rows) {
  submissionsBody.innerHTML = "";
  for (const item of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.student_name}</td>
      <td>${item.student_scholar_number}</td>
      <td>${item.student_hostel_number}</td>
      <td>${item.student_room_number}</td>
      <td>${item.wants_change ? "Yes" : "No"}</td>
      <td>${item.wanted_roommate_name || "-"}</td>
      <td>${item.wanted_roommate_scholar_number || "-"}</td>
      <td>${new Date(item.updated_at).toLocaleString()}</td>
    `;
    submissionsBody.appendChild(tr);
  }
}

function renderAllocations(rows) {
  allocationBody.innerHTML = "";
  for (const item of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${item.hostel_number}</td>
      <td>${item.room_number}</td>
      <td>${item.student_one_name} (${item.student_one_scholar_number})</td>
      <td>${item.student_two_name} (${item.student_two_scholar_number})</td>
    `;
    allocationBody.appendChild(tr);
  }
}

async function loadSubmissions() {
  const rows = await api("/api/submissions");
  renderSubmissions(rows);
}

async function loadAllocations() {
  if (!currentUser || !currentUser.is_admin) return;
  const rows = await api("/api/admin/allocations");
  renderAllocations(rows);
}

document.getElementById("signupForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({
        scholar_number: document.getElementById("signupScholar").value,
        password: document.getElementById("signupPassword").value,
      }),
    });
    setToken(data.access_token);
    currentUser = data.user;
    renderAuthMessage("Signup successful");
    await loadMe();
    await loadMySubmission();
    await loadSubmissions();
    await loadAllocations();
  } catch (err) {
    renderAuthMessage(err.message, true);
  }
});

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        scholar_number: document.getElementById("loginScholar").value,
        password: document.getElementById("loginPassword").value,
      }),
    });
    setToken(data.access_token);
    currentUser = data.user;
    renderAuthMessage("Login successful");
    await loadMe();
    await loadMySubmission();
    await loadSubmissions();
    await loadAllocations();
  } catch (err) {
    renderAuthMessage(err.message, true);
  }
});

document.getElementById("wantsChange").addEventListener("change", toggleRoommateFields);

document.getElementById("submissionForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const wantsChange = document.getElementById("wantsChange").value === "true";
    await api("/api/submission", {
      method: "PUT",
      body: JSON.stringify({
        wants_change: wantsChange,
        wanted_roommate_name: wantsChange ? document.getElementById("wantedName").value : null,
        wanted_roommate_scholar_number: wantsChange ? document.getElementById("wantedScholar").value : null,
        notes: document.getElementById("notes").value || null,
      }),
    });
    renderSubmissionMessage("Submission saved");
    await loadSubmissions();
  } catch (err) {
    renderSubmissionMessage(err.message, true);
  }
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  clearAuth();
  location.reload();
});

document.getElementById("downloadCsvBtn").addEventListener("click", () => {
  const token = getToken();
  fetch("/api/admin/submissions/export.csv", {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (!res.ok) throw new Error("CSV export failed");
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "submissions.csv";
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch((err) => renderSubmissionMessage(err.message, true));
});

document.getElementById("runAllocationBtn").addEventListener("click", async () => {
  try {
    const result = await api("/api/admin/allocations/run", { method: "POST" });
    renderAllocationMessage(
      `Allocations complete: ${result.allocations.length} room(s) allocated, ${result.unallocated_pairs.length} pair(s) pending`,
    );
    await loadAllocations();
  } catch (err) {
    renderAllocationMessage(err.message, true);
  }
});

async function init() {
  if (!getToken()) return;
  try {
    await loadMe();
    await loadMySubmission();
    await loadSubmissions();
    await loadAllocations();
  } catch (_) {
    clearAuth();
  }
}

init();
