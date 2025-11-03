/**
 * Dashboard JavaScript
 * Handles student and teacher dashboard functionality
 */

const API_BASE = "http://localhost:5000/api"
const currentToken = localStorage.getItem("auth_token")
const currentUser = JSON.parse(localStorage.getItem("current_user") || "{}")
let currentView = "calendar"
let selectedDate = new Date()
let userSchedules = []
const allNotifications = []

// ==================== INITIALIZATION ====================

document.addEventListener("DOMContentLoaded", () => {
  initializeDashboard()
  setupEventListeners()
  loadDashboardData()
})

function initializeDashboard() {
  if (!currentToken) {
    window.location.href = "/login.html"
    return
  }

  // Display user info
  document.getElementById("user-name").textContent = `${currentUser.first_name} ${currentUser.last_name}`
  document.getElementById("user-role-display").textContent = currentUser.role.toUpperCase()
  document.getElementById("user-role-display").className = `user-role-badge badge-${currentUser.role}`

  // Show creation section for teachers and admins
  if (currentUser.role === "teacher" || currentUser.role === "admin") {
    document.getElementById("creation-section").style.display = "block"
  }

  console.log("Dashboard initialized for:", currentUser.email)
}

function setupEventListeners() {
  // View navigation
  document.querySelectorAll(".menu-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault()
      switchView(item.dataset.view)
    })
  })

  // Calendar navigation
  document.getElementById("prev-month").addEventListener("click", () => {
    selectedDate.setMonth(selectedDate.getMonth() - 1)
    renderCalendar()
  })

  document.getElementById("next-month").addEventListener("click", () => {
    selectedDate.setMonth(selectedDate.getMonth() + 1)
    renderCalendar()
  })

  // Forms
  document.getElementById("create-schedule-form").addEventListener("submit", createSchedule)
  document.getElementById("create-event-form").addEventListener("submit", createEvent)

  // Recurring checkbox
  document.querySelector('input[name="is_recurring"]').addEventListener("change", (e) => {
    document.getElementById("recurrence-options").style.display = e.target.checked ? "block" : "none"
  })

  // User menu
  document.querySelector(".btn-user-menu").addEventListener("click", (e) => {
    e.target.nextElementSibling.classList.toggle("active")
  })

  // Modal close
  document.querySelectorAll(".close-modal").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.target.closest(".modal").style.display = "none"
    })
  })

  // Browse search
  document.getElementById("browse-search").addEventListener("input", loadPublicSchedules)
}

// ==================== VIEW MANAGEMENT ====================

function switchView(view) {
  document.querySelectorAll(".view-section").forEach((s) => {
    s.classList.remove("active")
  })

  document.querySelectorAll(".menu-item").forEach((m) => {
    m.classList.remove("active")
  })

  document.getElementById(`${view}-view`).classList.add("active")
  document.querySelector(`[data-view="${view}"]`).classList.add("active")
  currentView = view

  // Load view-specific data
  switch (view) {
    case "schedules":
      loadMySchedules()
      break
    case "browse":
      loadPublicSchedules()
      break
    case "create-schedule":
      break
    case "create-event":
      loadSchedulesForDropdown()
      break
    case "notifications":
      loadNotifications()
      break
  }
}

// ==================== DASHBOARD DATA LOADING ====================

async function loadDashboardData() {
  await loadMySchedules()
  renderCalendar()
  loadNotifications()
}

async function loadMySchedules() {
  try {
    const response = await fetch(`${API_BASE}/schedules`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()
    userSchedules = data.schedules

    if (currentView === "schedules") {
      displaySchedules(userSchedules)
    }
  } catch (error) {
    console.error("Error loading schedules:", error)
  }
}

async function loadPublicSchedules() {
  const searchTerm = document.getElementById("browse-search").value || ""

  try {
    const response = await fetch(`${API_BASE}/schedules`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()
    let publicSchedules = data.schedules.filter((s) => s.is_public)

    if (searchTerm) {
      publicSchedules = publicSchedules.filter((s) => s.title.toLowerCase().includes(searchTerm.toLowerCase()))
    }

    displaySchedules(publicSchedules, "#browse-grid")
  } catch (error) {
    console.error("Error loading public schedules:", error)
  }
}

function displaySchedules(schedules, containerId = "#schedules-grid") {
  const container = document.querySelector(containerId)
  container.innerHTML = ""

  if (schedules.length === 0) {
    container.innerHTML = '<p class="empty-state">No schedules found</p>'
    return
  }

  schedules.forEach((schedule) => {
    const card = document.createElement("div")
    card.className = "schedule-card"
    card.style.borderLeftColor = schedule.color
    card.innerHTML = `
            <h3>${schedule.title}</h3>
            <p class="schedule-type">
                ${schedule.is_class_schedule ? "Class Schedule" : "Event Schedule"}
            </p>
            <p class="schedule-meta">${schedule.events_count} events</p>
            <p class="schedule-desc">${schedule.description || ""}</p>
            <div class="schedule-actions">
                <button class="btn-secondary" onclick="viewScheduleDetails(${schedule.id})">
                    View
                </button>
                ${
                  currentUser.id === schedule.user_id
                    ? `
                    <button class="btn-secondary" onclick="editSchedule(${schedule.id})">
                        Edit
                    </button>
                `
                    : ""
                }
            </div>
        `
    container.appendChild(card)
  })
}

async function viewScheduleDetails(scheduleId) {
  try {
    const response = await fetch(`${API_BASE}/schedules/${scheduleId}`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const schedule = await response.json()

    document.getElementById("schedule-title").textContent = schedule.title
    document.getElementById("schedule-description").textContent = schedule.description || "No description"

    const eventsList = document.getElementById("schedule-events-list")
    eventsList.innerHTML = ""

    if (schedule.events && schedule.events.length > 0) {
      schedule.events.forEach((event) => {
        const eventEl = document.createElement("div")
        eventEl.className = "schedule-event-item"
        const startTime = new Date(event.start_time).toLocaleString()
        eventEl.innerHTML = `
                    <strong>${event.title}</strong>
                    <p>${startTime}</p>
                    <p>${event.location || event.building || "No location"}</p>
                `
        eventsList.appendChild(eventEl)
      })
    } else {
      eventsList.innerHTML = "<p>No events in this schedule</p>"
    }

    document.getElementById("schedule-modal").style.display = "block"
  } catch (error) {
    console.error("Error loading schedule details:", error)
  }
}

async function loadSchedulesForDropdown() {
  try {
    const response = await fetch(`${API_BASE}/schedules`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()
    const select = document.querySelector('select[name="schedule_id"]')

    data.schedules.forEach((schedule) => {
      const option = document.createElement("option")
      option.value = schedule.id
      option.textContent = schedule.title
      select.appendChild(option)
    })
  } catch (error) {
    console.error("Error loading schedules:", error)
  }
}

// ==================== CALENDAR ====================

function renderCalendar() {
  const year = selectedDate.getFullYear()
  const month = selectedDate.getMonth()

  // Update header
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ]
  document.getElementById("current-month").textContent = `${monthNames[month]} ${year}`

  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const daysInMonth = lastDay.getDate()
  const startingDayOfWeek = firstDay.getDay()

  const calendarGrid = document.getElementById("calendar-grid")
  calendarGrid.innerHTML = ""

  // Add empty cells for days before month starts
  for (let i = 0; i < startingDayOfWeek; i++) {
    const emptyCell = document.createElement("div")
    emptyCell.className = "calendar-day empty"
    calendarGrid.appendChild(emptyCell)
  }

  // Add days
  for (let day = 1; day <= daysInMonth; day++) {
    const dayCell = document.createElement("div")
    dayCell.className = "calendar-day"
    dayCell.textContent = day
    dayCell.addEventListener("click", () => selectDate(new Date(year, month, day)))
    calendarGrid.appendChild(dayCell)
  }
}

function selectDate(date) {
  selectedDate = date
  const dateStr = date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
  document.getElementById("selected-day").textContent = dateStr

  // Get events for selected date
  getEventsForDate(date)
}

async function getEventsForDate(date) {
  const eventsList = document.getElementById("day-events-list")
  eventsList.innerHTML = ""

  // Get all events from all schedules
  for (const schedule of userSchedules) {
    try {
      const response = await fetch(`${API_BASE}/schedules/${schedule.id}`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      const scheduleData = await response.json()
      const dayEvents = scheduleData.events.filter((e) => {
        const eventDate = new Date(e.start_time)
        return eventDate.toDateString() === date.toDateString()
      })

      dayEvents.forEach((event) => {
        const eventEl = document.createElement("div")
        eventEl.className = "event-item"
        eventEl.style.borderLeftColor = event.color
        const startTime = new Date(event.start_time).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
        eventEl.innerHTML = `
                    <div class="event-time">${startTime}</div>
                    <div class="event-title">${event.title}</div>
                    <div class="event-location">${event.location || event.room_number || ""}</div>
                `
        eventEl.addEventListener("click", () => viewEventDetails(event))
        eventsList.appendChild(eventEl)
      })
    } catch (error) {
      console.error("Error loading events:", error)
    }
  }

  if (eventsList.innerHTML === "") {
    eventsList.innerHTML = '<p class="empty-state">No events for this date</p>'
  }
}

// ==================== EVENT MANAGEMENT ====================

async function createEvent(e) {
  e.preventDefault()

  const formData = new FormData(document.getElementById("create-event-form"))
  const data = {
    schedule_id: Number.parseInt(formData.get("schedule_id")),
    title: formData.get("title"),
    description: formData.get("description"),
    start_time: new Date(formData.get("start_time")).toISOString(),
    end_time: new Date(formData.get("end_time")).toISOString(),
    building: formData.get("building"),
    room_number: formData.get("room_number"),
    location: formData.get("location"),
    is_recurring: formData.get("is_recurring") === "on",
    recurrence_pattern: formData.get("recurrence_pattern"),
    recurrence_end_date: formData.get("recurrence_end_date"),
    requires_approval: formData.get("requires_approval") === "on",
  }

  try {
    const response = await fetch(`${API_BASE}/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify(data),
    })

    if (response.status === 409) {
      const error = await response.json()
      alert("Overlap detected! This event conflicts with another event.")
    } else if (response.ok) {
      alert("Event created successfully")
      document.getElementById("create-event-form").reset()
      switchView("calendar")
      loadDashboardData()
    } else {
      alert("Error creating event")
    }
  } catch (error) {
    console.error("Error creating event:", error)
  }
}

function viewEventDetails(event) {
  const details = document.getElementById("event-details")
  const startTime = new Date(event.start_time).toLocaleString()
  const endTime = new Date(event.end_time).toLocaleString()

  details.innerHTML = `
        <h3>${event.title}</h3>
        <p><strong>Time:</strong> ${startTime} - ${endTime}</p>
        <p><strong>Location:</strong> ${event.location || event.building + " " + event.room_number || "No location"}</p>
        <p><strong>Description:</strong> ${event.description || "No description"}</p>
        <p><strong>Status:</strong> <span class="badge badge-${event.approval_status}">${event.approval_status}</span></p>
    `

  const actions = document.getElementById("event-actions")
  actions.innerHTML = ""

  if (event.organizer_id === currentUser.id) {
    actions.innerHTML = `
            <button class="btn-secondary" onclick="editEvent(${event.id})">Edit</button>
            <button class="btn-danger" onclick="deleteEvent(${event.id})">Delete</button>
        `
  }

  document.getElementById("event-modal").style.display = "block"
}

// ==================== SCHEDULE MANAGEMENT ====================

async function createSchedule(e) {
  e.preventDefault()

  const formData = new FormData(document.getElementById("create-schedule-form"))
  const data = {
    title: formData.get("title"),
    description: formData.get("description"),
    is_class_schedule: formData.get("type") === "true",
    color: formData.get("color"),
    is_public: formData.get("is_public") === "on",
  }

  try {
    const response = await fetch(`${API_BASE}/schedules`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify(data),
    })

    if (response.ok) {
      alert("Schedule created successfully")
      document.getElementById("create-schedule-form").reset()
      switchView("schedules")
      loadMySchedules()
    } else {
      alert("Error creating schedule")
    }
  } catch (error) {
    console.error("Error creating schedule:", error)
  }
}

// ==================== NOTIFICATIONS ====================

async function loadNotifications() {
  try {
    // For now, return empty array - this would be fetched from backend
    const notificationsList = document.getElementById("notifications-list")

    if (allNotifications.length === 0) {
      notificationsList.innerHTML = '<p class="empty-state">No notifications</p>'
      return
    }

    notificationsList.innerHTML = ""
    allNotifications.forEach((notif) => {
      const notifEl = document.createElement("div")
      notifEl.className = `notification-item ${notif.is_read ? "read" : "unread"}`
      notifEl.innerHTML = `
                <h4>${notif.type.toUpperCase()}</h4>
                <p>${notif.message}</p>
                <small>${new Date(notif.sent_at).toLocaleString()}</small>
            `
      notificationsList.appendChild(notifEl)
    })
  } catch (error) {
    console.error("Error loading notifications:", error)
  }
}

// ==================== UTILITY ====================

function logout() {
  localStorage.clear()
  window.location.href = "/login.html"
}

function openSettings() {
  alert("Settings page - coming soon")
}
