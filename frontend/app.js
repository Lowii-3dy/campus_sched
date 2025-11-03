// localStorage-based Campus Scheduler App
// All data is stored locally in the browser

const APP = {
  currentUser: null,
  schedules: [],
  events: [],
  approvals: [],
}

// Initialize app when page loads
function initApp() {
  loadUserData()
  if (!APP.currentUser) {
    showLoginPage()
  } else {
    showDashboard()
  }
}

// ==================== LOGIN / LOGOUT ====================

function showLoginPage() {
  const html = `
    <div style="max-width: 400px; margin: 50px auto; padding: 40px; background: #2a2a3e; border-radius: 8px; border: 1px solid rgba(59, 130, 246, 0.2);">
      <h1 style="color: #3b82f6; margin-bottom: 30px; text-align: center;">🎓 Campus Scheduler</h1>
      
      <div style="margin-bottom: 20px;">
        <label style="display: block; margin-bottom: 8px; font-weight: 600;">Email</label>
        <input type="email" id="loginEmail" placeholder="admin@campus.edu" style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #475569; border-radius: 4px; color: #e0e0e0; font-size: 14px;">
      </div>
      
      <div style="margin-bottom: 20px;">
        <label style="display: block; margin-bottom: 8px; font-weight: 600;">Password</label>
        <input type="password" id="loginPassword" placeholder="password123" style="width: 100%; padding: 10px; background: #1a1a2e; border: 1px solid #475569; border-radius: 4px; color: #e0e0e0; font-size: 14px;">
      </div>
      
      <button onclick="handleLogin()" style="width: 100%; padding: 10px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; margin-bottom: 15px;">Login</button>
      
      <div style="border-top: 1px solid #475569; padding-top: 20px; margin-top: 20px;">
        <p style="font-size: 12px; color: #cbd5e1; margin-bottom: 10px;"><strong>Demo Accounts:</strong></p>
        <button onclick="quickLogin('admin@campus.edu', 'admin')" style="width: 100%; padding: 8px; background: #a855f7; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-bottom: 5px;">Admin</button>
        <button onclick="quickLogin('teacher@campus.edu', 'teacher')" style="width: 100%; padding: 8px; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-bottom: 5px;">Teacher</button>
        <button onclick="quickLogin('student@campus.edu', 'student')" style="width: 100%; padding: 8px; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">Student</button>
      </div>
    </div>
  `
  document.getElementById("app").innerHTML = html
}

function handleLogin() {
  const email = document.getElementById("loginEmail").value
  const password = document.getElementById("loginPassword").value

  if (!email || !password) {
    alert("Please enter email and password")
    return
  }

  quickLogin(email, extractRole(email))
}

function quickLogin(email, role) {
  APP.currentUser = {
    id: Math.random().toString(36).substr(2, 9),
    email: email,
    role: role,
    first_name: role.charAt(0).toUpperCase() + role.slice(1),
    last_name: "User",
  }

  saveUserData()
  loadSampleData()
  showDashboard()
}

function logout() {
  APP.currentUser = null
  localStorage.clear()
  initApp()
}

function extractRole(email) {
  if (email.includes("admin")) return "admin"
  if (email.includes("teacher")) return "teacher"
  return "student"
}

// ==================== DATA PERSISTENCE ====================

function saveUserData() {
  localStorage.setItem("currentUser", JSON.stringify(APP.currentUser))
  localStorage.setItem("schedules", JSON.stringify(APP.schedules))
  localStorage.setItem("events", JSON.stringify(APP.events))
  localStorage.setItem("approvals", JSON.stringify(APP.approvals))
}

function loadUserData() {
  const user = localStorage.getItem("currentUser")
  if (user) {
    APP.currentUser = JSON.parse(user)
    APP.schedules = JSON.parse(localStorage.getItem("schedules") || "[]")
    APP.events = JSON.parse(localStorage.getItem("events") || "[]")
    APP.approvals = JSON.parse(localStorage.getItem("approvals") || "[]")
  }
}

function loadSampleData() {
  if (APP.schedules.length === 0) {
    APP.schedules = [
      {
        id: 1,
        title: "Spring 2025 Classes",
        description: "All spring classes",
        color: "#3b82f6",
        is_public: true,
        user_id: APP.currentUser.id,
      },
      {
        id: 2,
        title: "Lab Schedule",
        description: "Weekly lab sessions",
        color: "#10b981",
        is_public: false,
        user_id: APP.currentUser.id,
      },
    ]

    APP.events = [
      {
        id: 1,
        schedule_id: 1,
        title: "Math 101",
        start_time: new Date(Date.now() + 86400000).toISOString(),
        end_time: new Date(Date.now() + 90000000).toISOString(),
        location: "Room 101",
        status: "approved",
      },
      {
        id: 2,
        schedule_id: 1,
        title: "Physics Lab",
        start_time: new Date(Date.now() + 172800000).toISOString(),
        end_time: new Date(Date.now() + 176400000).toISOString(),
        location: "Lab B",
        status: "pending",
      },
    ]

    saveUserData()
  }
}

// ==================== DASHBOARD ====================

function showDashboard() {
  const dashboardHTML = `
    <style>
      body { background: #0f172a; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; }
      #app { display: flex; min-height: 100vh; }
      .sidebar { width: 250px; background: #1e293b; border-right: 1px solid #475569; padding: 20px; overflow-y: auto; }
      .sidebar h2 { color: #3b82f6; margin-bottom: 30px; }
      .menu-item { display: block; padding: 12px; margin: 5px 0; background: transparent; color: #cbd5e1; border: none; border-radius: 4px; cursor: pointer; text-align: left; transition: all 0.2s; }
      .menu-item:hover, .menu-item.active { background: #3b82f6; color: white; }
      .main { flex: 1; overflow-y: auto; padding: 30px; }
      .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
      .header h1 { margin: 0; }
      .header .user-info { display: flex; gap: 15px; align-items: center; }
      .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
      .badge-admin { background: #a855f7; color: white; }
      .badge-teacher { background: #3b82f6; color: white; }
      .badge-student { background: #10b981; color: white; }
      .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
      .card { background: #1e293b; border: 1px solid #475569; border-radius: 8px; padding: 20px; }
      .card h3 { margin-top: 0; color: #3b82f6; }
      .form { display: flex; flex-direction: column; gap: 15px; }
      .form label { display: flex; flex-direction: column; gap: 5px; font-weight: 600; }
      .form input, .form select, .form textarea { padding: 10px; background: #334155; border: 1px solid #475569; border-radius: 4px; color: #f1f5f9; }
      .btn { padding: 10px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; transition: all 0.2s; }
      .btn-primary { background: #3b82f6; color: white; }
      .btn-primary:hover { background: #1e40af; }
      .btn-danger { background: #ef4444; color: white; }
      .btn-success { background: #10b981; color: white; }
      .btn-secondary { background: #334155; color: #f1f5f9; }
      .hidden { display: none; }
      .section { display: none; }
      .section.active { display: block; }
      .event-item { background: #334155; padding: 12px; border-radius: 4px; margin: 10px 0; border-left: 4px solid #3b82f6; }
      .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
      .stat-card { background: #1e293b; border: 1px solid #475569; padding: 15px; border-radius: 8px; }
      .stat-value { font-size: 24px; font-weight: bold; color: #3b82f6; }
    </style>
    
    <div class="sidebar">
      <h2>Campus Scheduler</h2>
      <button class="menu-item active" onclick="switchSection('dashboard', this)">📊 Dashboard</button>
      <button class="menu-item" onclick="switchSection('schedules', this)">📋 My Schedules</button>
      <button class="menu-item" onclick="switchSection('events', this)">📅 My Events</button>
      ${APP.currentUser.role !== "student" ? '<button class="menu-item" onclick="switchSection(\'create\', this)">➕ Create</button>' : ""}
      ${APP.currentUser.role === "admin" ? '<button class="menu-item" onclick="switchSection(\'admin\', this)">⚙️ Admin Panel</button>' : ""}
      <button class="menu-item" onclick="logout()">🚪 Logout</button>
    </div>
    
    <div class="main">
      <div class="header">
        <h1>Campus Scheduler</h1>
        <div class="user-info">
          <span>${APP.currentUser.first_name}</span>
          <span class="badge badge-${APP.currentUser.role}">${APP.currentUser.role.toUpperCase()}</span>
        </div>
      </div>
      
      <!-- Dashboard Section -->
      <div id="dashboard" class="section active">
        <h2>Dashboard</h2>
        <div class="stats">
          <div class="stat-card">
            <div class="stat-value">${APP.schedules.length}</div>
            <div>My Schedules</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${APP.events.length}</div>
            <div>Total Events</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">${APP.events.filter((e) => e.status === "pending").length}</div>
            <div>Pending Events</div>
          </div>
        </div>
        
        <h3 style="margin-top: 30px;">Upcoming Events</h3>
        <div id="upcoming-events">
          ${APP.events
            .slice(0, 5)
            .map(
              (e) => `
            <div class="event-item">
              <strong>${e.title}</strong>
              <p>${new Date(e.start_time).toLocaleString()}</p>
              <p>${e.location}</p>
            </div>
          `,
            )
            .join("")}
        </div>
      </div>
      
      <!-- Schedules Section -->
      <div id="schedules" class="section">
        <h2>My Schedules</h2>
        <button class="btn btn-primary" onclick="switchSection('create', document.querySelector('[onclick*=\'create\']'))" style="margin-bottom: 20px;">+ New Schedule</button>
        <div class="grid">
          ${APP.schedules
            .map(
              (s) => `
            <div class="card" style="border-left: 4px solid ${s.color};">
              <h3>${s.title}</h3>
              <p>${s.description}</p>
              <p style="color: #cbd5e1; font-size: 12px;">${APP.events.filter((e) => e.schedule_id === s.id).length} events</p>
              <button class="btn btn-secondary" onclick="viewSchedule(${s.id})">View</button>
            </div>
          `,
            )
            .join("")}
        </div>
      </div>
      
      <!-- Events Section -->
      <div id="events" class="section">
        <h2>My Events</h2>
        <div id="events-list">
          ${APP.events
            .map(
              (e) => `
            <div class="event-item">
              <strong>${e.title}</strong>
              <p>${new Date(e.start_time).toLocaleString()}</p>
              <p>${e.location}</p>
              <span class="badge">${e.status}</span>
            </div>
          `,
            )
            .join("")}
        </div>
      </div>
      
      <!-- Create Section -->
      <div id="create" class="section">
        <h2>Create New Schedule</h2>
        <form class="form" onsubmit="createSchedule(event)" style="max-width: 500px;">
          <label>Schedule Title <input type="text" name="title" required></label>
          <label>Description <textarea name="description" rows="3"></textarea></label>
          <label>Color 
            <select name="color">
              <option value="#3b82f6">Blue</option>
              <option value="#10b981">Green</option>
              <option value="#f59e0b">Amber</option>
              <option value="#ef4444">Red</option>
              <option value="#a855f7">Purple</option>
            </select>
          </label>
          <label>
            <input type="checkbox" name="is_public"> Make Public
          </label>
          <button type="submit" class="btn btn-primary">Create Schedule</button>
        </form>
        
        <h2 style="margin-top: 40px;">Add Event to Schedule</h2>
        <form class="form" onsubmit="createEvent(event)" style="max-width: 500px;">
          <label>Select Schedule
            <select name="schedule_id" required>
              <option value="">-- Choose --</option>
              ${APP.schedules.map((s) => `<option value="${s.id}">${s.title}</option>`).join("")}
            </select>
          </label>
          <label>Event Title <input type="text" name="title" required></label>
          <label>Start Time <input type="datetime-local" name="start_time" required></label>
          <label>End Time <input type="datetime-local" name="end_time" required></label>
          <label>Location <input type="text" name="location"></label>
          <button type="submit" class="btn btn-primary">Create Event</button>
        </form>
      </div>
      
      <!-- Admin Section -->
      <div id="admin" class="section">
        <h2>Admin Panel</h2>
        <p>Total Users: ${3}</p>
        <p>Total Schedules: ${APP.schedules.length}</p>
        <p>Total Events: ${APP.events.length}</p>
        <p>Pending Approvals: ${APP.events.filter((e) => e.status === "pending").length}</p>
        
        <h3 style="margin-top: 30px;">Pending Event Approvals</h3>
        <div id="admin-approvals">
          ${APP.events
            .filter((e) => e.status === "pending")
            .map(
              (e) => `
            <div class="event-item">
              <strong>${e.title}</strong>
              <p>${new Date(e.start_time).toLocaleString()}</p>
              <button class="btn btn-success" onclick="approveEvent(${e.id})">Approve</button>
              <button class="btn btn-danger" onclick="declineEvent(${e.id})">Decline</button>
            </div>
          `,
            )
            .join("")}
        </div>
      </div>
    </div>
  `

  document.getElementById("app").innerHTML = dashboardHTML
}

function switchSection(section, btn) {
  document.querySelectorAll(".section").forEach((s) => s.classList.remove("active"))
  document.querySelectorAll(".menu-item").forEach((m) => m.classList.remove("active"))

  document.getElementById(section).classList.add("active")
  if (btn) btn.classList.add("active")
}

// ==================== CRUD OPERATIONS ====================

function createSchedule(e) {
  e.preventDefault()
  const form = e.target
  const schedule = {
    id: Date.now(),
    title: form.title.value,
    description: form.description.value,
    color: form.color.value,
    is_public: form.querySelector('[name="is_public"]').checked,
    user_id: APP.currentUser.id,
  }

  APP.schedules.push(schedule)
  saveUserData()
  alert("Schedule created!")
  showDashboard()
}

function createEvent(e) {
  e.preventDefault()
  const form = e.target
  const event = {
    id: Date.now(),
    schedule_id: Number.parseInt(form.schedule_id.value),
    title: form.title.value,
    start_time: new Date(form.start_time.value).toISOString(),
    end_time: new Date(form.end_time.value).toISOString(),
    location: form.location.value,
    status: APP.currentUser.role === "admin" ? "approved" : "pending",
  }

  APP.events.push(event)
  saveUserData()
  alert("Event created!")
  showDashboard()
}

function viewSchedule(id) {
  const schedule = APP.schedules.find((s) => s.id === id)
  const events = APP.events.filter((e) => e.schedule_id === id)

  const html = `
    <div style="max-width: 600px;">
      <h2>${schedule.title}</h2>
      <p>${schedule.description}</p>
      <h3>Events</h3>
      ${events
        .map(
          (e) => `
        <div class="event-item">
          <strong>${e.title}</strong>
          <p>${new Date(e.start_time).toLocaleString()}</p>
          <p>${e.location}</p>
        </div>
      `,
        )
        .join("")}
      <button class="btn btn-secondary" onclick="showDashboard()" style="margin-top: 20px;">Back</button>
    </div>
  `

  document.querySelector(".main").innerHTML = html
}

function approveEvent(id) {
  const event = APP.events.find((e) => e.id === id)
  event.status = "approved"
  saveUserData()
  alert("Event approved!")
  showDashboard()
}

function declineEvent(id) {
  const event = APP.events.find((e) => e.id === id)
  event.status = "declined"
  saveUserData()
  alert("Event declined!")
  showDashboard()
}

// Start the app
document.addEventListener("DOMContentLoaded", initApp)
