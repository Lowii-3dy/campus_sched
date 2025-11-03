/**
 * Admin Panel JavaScript
 * Handles admin dashboard functionality, user management, and event approvals
 */

const API_BASE = "http://localhost:5000/api"
const currentToken = localStorage.getItem("auth_token")
const currentUser = JSON.parse(localStorage.getItem("current_user") || "{}")

// ==================== INITIALIZATION ====================

document.addEventListener("DOMContentLoaded", () => {
  initializeAdmin()
  setupEventListeners()
  loadDashboardData()
})

function initializeAdmin() {
  if (!currentUser.role || currentUser.role !== "admin") {
    window.location.href = "/login.html"
    return
  }

  console.log("Admin panel initialized for:", currentUser.email)
}

function setupEventListeners() {
  // Navigation
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault()
      switchSection(item.dataset.section)
    })
  })

  // User management
  document.getElementById("btn-add-user").addEventListener("click", openUserModal)
  document.getElementById("user-form").addEventListener("submit", saveUser)

  // Filters
  document.getElementById("filter-role").addEventListener("change", loadUsers)
  document.getElementById("filter-active").addEventListener("change", loadUsers)
  document.getElementById("filter-search").addEventListener("input", loadUsers)
  document.getElementById("filter-approval-status").addEventListener("change", loadApprovals)

  // Modal close
  document.querySelectorAll(".close-modal").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.target.closest(".modal").style.display = "none"
    })
  })

  // Logout
  document.querySelector(".btn-logout").addEventListener("click", logout)
}

// ==================== SECTION NAVIGATION ====================

function switchSection(sectionName) {
  document.querySelectorAll(".content-section").forEach((s) => {
    s.classList.remove("active")
  })

  document.querySelectorAll(".nav-item").forEach((n) => {
    n.classList.remove("active")
  })

  document.getElementById(sectionName).classList.add("active")
  document.querySelector(`[data-section="${sectionName}"]`).classList.add("active")

  // Update title
  const titles = {
    dashboard: "Dashboard",
    users: "User Management",
    approvals: "Event Approvals",
    facilities: "Facilities Management",
    statistics: "Platform Statistics",
  }
  document.getElementById("section-title").textContent = titles[sectionName]

  // Load section data
  switch (sectionName) {
    case "users":
      loadUsers()
      break
    case "approvals":
      loadApprovals()
      break
    case "facilities":
      loadFacilities()
      break
    case "statistics":
      loadStatistics()
      break
  }
}

// ==================== DASHBOARD ====================

async function loadDashboardData() {
  try {
    const response = await fetch(`${API_BASE}/admin/statistics`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()

    document.getElementById("stat-total-users").textContent = data.users.total
    document.getElementById("stat-active-users").textContent = data.users.active
    document.getElementById("stat-total-schedules").textContent = data.schedules.total
    document.getElementById("stat-class-schedules").textContent = data.schedules.class_schedules
    document.getElementById("stat-total-events").textContent = data.events.total
    document.getElementById("stat-pending-approvals").textContent = data.events.pending_approval
    document.getElementById("stat-admins").textContent = data.users.by_role.admins
    document.getElementById("stat-teachers").textContent = data.users.by_role.teachers
    document.getElementById("stat-students").textContent = data.users.by_role.students
  } catch (error) {
    console.error("Error loading dashboard data:", error)
  }
}

// ==================== USER MANAGEMENT ====================

async function loadUsers() {
  const role = document.getElementById("filter-role").value
  const active = document.getElementById("filter-active").value
  const search = document.getElementById("filter-search").value

  const params = new URLSearchParams()
  if (role) params.append("role", role)
  if (active) params.append("is_active", active)
  params.append("page", 1)
  params.append("per_page", 20)

  try {
    const response = await fetch(`${API_BASE}/admin/users?${params}`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()

    const tbody = document.getElementById("users-table-body")
    tbody.innerHTML = ""

    data.users.forEach((user) => {
      const row = document.createElement("tr")
      row.innerHTML = `
                <td>${user.email}</td>
                <td>${user.first_name} ${user.last_name}</td>
                <td><span class="badge badge-${user.role}">${user.role}</span></td>
                <td>${user.department || "-"}</td>
                <td>
                    <input type="checkbox" ${user.can_create_schedule ? "checked" : ""} 
                           onchange="toggleUserPermission(${user.id}, this.checked)">
                </td>
                <td><span class="badge ${user.is_active ? "badge-active" : "badge-inactive"}">
                    ${user.is_active ? "Active" : "Inactive"}
                </span></td>
                <td>
                    <button class="btn-small btn-edit" onclick="editUser(${user.id})">Edit</button>
                    <button class="btn-small btn-danger" onclick="deactivateUser(${user.id})">Deactivate</button>
                </td>
            `
      tbody.appendChild(row)
    })
  } catch (error) {
    console.error("Error loading users:", error)
  }
}

function openUserModal() {
  document.getElementById("user-form").reset()
  document.getElementById("user-id").value = ""
  document.getElementById("user-modal").style.display = "block"
}

function editUser(userId) {
  fetch(`${API_BASE}/admin/users/${userId}`, {
    headers: { Authorization: `Bearer ${currentToken}` },
  })
    .then((r) => r.json())
    .then((user) => {
      document.getElementById("user-id").value = user.id
      document.getElementById("user-email").value = user.email
      document.getElementById("user-first-name").value = user.first_name
      document.getElementById("user-last-name").value = user.last_name
      document.getElementById("user-role").value = user.role
      document.getElementById("user-department").value = user.department || ""
      document.getElementById("user-can-create").checked = user.can_create_schedule
      document.getElementById("user-is-active").checked = user.is_active
      document.getElementById("user-modal").style.display = "block"
    })
}

async function saveUser(e) {
  e.preventDefault()

  const userId = document.getElementById("user-id").value
  const endpoint = userId ? `${API_BASE}/admin/users/${userId}/permissions` : `${API_BASE}/auth/register`

  const userData = {
    email: document.getElementById("user-email").value,
    first_name: document.getElementById("user-first-name").value,
    last_name: document.getElementById("user-last-name").value,
    role: document.getElementById("user-role").value,
    department: document.getElementById("user-department").value,
    can_create_schedule: document.getElementById("user-can-create").checked,
    is_active: document.getElementById("user-is-active").checked,
  }

  try {
    const response = await fetch(endpoint, {
      method: userId ? "PUT" : "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify(userData),
    })

    if (response.ok) {
      alert("User saved successfully")
      document.getElementById("user-modal").style.display = "none"
      loadUsers()
    } else {
      alert("Error saving user")
    }
  } catch (error) {
    console.error("Error saving user:", error)
  }
}

async function toggleUserPermission(userId, hasPermission) {
  try {
    await fetch(`${API_BASE}/admin/users/${userId}/permissions`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify({ can_create_schedule: hasPermission }),
    })
  } catch (error) {
    console.error("Error updating permission:", error)
  }
}

async function deactivateUser(userId) {
  if (!confirm("Are you sure you want to deactivate this user?")) return

  try {
    await fetch(`${API_BASE}/admin/users/${userId}/deactivate`, {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
    })
    loadUsers()
  } catch (error) {
    console.error("Error deactivating user:", error)
  }
}

// ==================== EVENT APPROVALS ====================

async function loadApprovals() {
  const status = document.getElementById("filter-approval-status").value

  try {
    const response = await fetch(`${API_BASE}/admin/approvals?status=${status}`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()
    const container = document.getElementById("approvals-list")
    container.innerHTML = ""

    data.approvals.forEach((approval) => {
      const event = approval.event
      const card = document.createElement("div")
      card.className = "approval-card"
      card.innerHTML = `
                <div class="approval-header">
                    <h3>${event.title}</h3>
                    <span class="badge badge-${approval.status}">${approval.status}</span>
                </div>
                <p><strong>Organizer:</strong> ${approval.organizer.first_name} ${approval.organizer.last_name}</p>
                <p><strong>Time:</strong> ${new Date(event.start_time).toLocaleString()}</p>
                <p><strong>Location:</strong> ${event.building || "N/A"} - ${event.room_number || "N/A"}</p>
                <p>${event.description}</p>
                ${
                  approval.status === "pending"
                    ? `
                    <div class="approval-actions">
                        <button class="btn-success" onclick="approveEvent(${approval.id})">Approve</button>
                        <button class="btn-danger" onclick="declineEvent(${approval.id})">Decline</button>
                    </div>
                `
                    : ""
                }
            `
      container.appendChild(card)
    })
  } catch (error) {
    console.error("Error loading approvals:", error)
  }
}

async function approveEvent(approvalId) {
  try {
    const response = await fetch(`${API_BASE}/admin/approvals/${approvalId}/approve`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify({ reason: "Approved by admin" }),
    })

    if (response.ok) {
      alert("Event approved")
      loadApprovals()
    }
  } catch (error) {
    console.error("Error approving event:", error)
  }
}

async function declineEvent(approvalId) {
  const reason = prompt("Enter reason for decline:")
  if (!reason) return

  try {
    const response = await fetch(`${API_BASE}/admin/approvals/${approvalId}/decline`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentToken}`,
      },
      body: JSON.stringify({ reason }),
    })

    if (response.ok) {
      alert("Event declined")
      loadApprovals()
    }
  } catch (error) {
    console.error("Error declining event:", error)
  }
}

// ==================== FACILITIES ====================

async function loadFacilities() {
  try {
    const response = await fetch(`${API_BASE}/admin/facilities`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const data = await response.json()
    const grid = document.getElementById("facilities-grid")
    grid.innerHTML = ""

    data.facilities.forEach((facility) => {
      const card = document.createElement("div")
      card.className = "facility-card"
      card.innerHTML = `
                <h3>${facility.building} - Room ${facility.room_number}</h3>
                <p>Active Events: ${facility.event_count}</p>
                <button class="btn-small" onclick="viewFacilitySchedule('${facility.building}', '${facility.room_number}')">
                    View Schedule
                </button>
            `
      grid.appendChild(card)
    })
  } catch (error) {
    console.error("Error loading facilities:", error)
  }
}

// ==================== STATISTICS ====================

async function loadStatistics() {
  await loadDashboardData()

  try {
    const deptResponse = await fetch(`${API_BASE}/admin/departments`, {
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    const deptData = await deptResponse.json()
    const deptList = document.getElementById("departments-list")
    deptList.innerHTML = ""

    deptData.departments.forEach((dept) => {
      const item = document.createElement("p")
      item.textContent = `${dept.name}: ${dept.user_count} users`
      deptList.appendChild(item)
    })
  } catch (error) {
    console.error("Error loading statistics:", error)
  }
}

// ==================== UTILITY ====================

function logout() {
  localStorage.clear()
  window.location.href = "/login.html"
}
