/**
 * Notifications Module
 * Handles in-app notifications and approval management
 */

const API_BASE = "https://example.com/api" // Declare API_BASE variable
const currentToken = "your_token_here" // Declare currentToken variable

const NotificationManager = {
  pollInterval: null,
  unreadCount: 0,

  /**
   * Initialize notification system
   * Starts polling for new notifications
   */
  init(pollFrequency = 30000) {
    this.loadNotifications()
    this.startPolling(pollFrequency)
    this.setupNotificationUI()
  },

  /**
   * Start polling for new notifications
   */
  startPolling(frequency) {
    this.pollInterval = setInterval(() => {
      this.loadNotifications()
    }, frequency)
  },

  /**
   * Load notifications from server
   */
  async loadNotifications() {
    try {
      const response = await fetch(`${API_BASE}/approvals/notifications?per_page=50`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      const data = await response.json()
      this.unreadCount = data.unread_count
      this.updateNotificationUI(data.notifications)
      this.updateBadge()
    } catch (error) {
      console.error("Error loading notifications:", error)
    }
  },

  /**
   * Update notification badge with count
   */
  updateBadge() {
    const badge = document.getElementById("notif-badge")
    if (badge) {
      if (this.unreadCount > 0) {
        badge.textContent = this.unreadCount
        badge.style.display = "block"
      } else {
        badge.style.display = "none"
      }
    }
  },

  /**
   * Setup notification UI elements
   */
  setupNotificationUI() {
    const container = document.getElementById("notifications-list")
    if (!container) return

    container.addEventListener("click", (e) => {
      if (e.target.closest(".btn-mark-read")) {
        const notifId = e.target.closest(".notification-item").dataset.notifId
        this.markAsRead(notifId)
      }
    })
  },

  /**
   * Update notification display
   */
  updateNotificationUI(notifications) {
    const container = document.getElementById("notifications-list")
    if (!container) return

    if (notifications.length === 0) {
      container.innerHTML = '<p class="empty-state">No notifications</p>'
      return
    }

    container.innerHTML = notifications
      .map(
        (notif) => `
            <div class="notification-item ${notif.is_read ? "read" : "unread"}" data-notif-id="${notif.id}">
                <div class="notification-content">
                    <span class="notification-type badge badge-${notif.type}">${notif.type}</span>
                    <p class="notification-message">${notif.message}</p>
                    <small class="notification-time">${new Date(notif.sent_at).toLocaleString()}</small>
                </div>
                <div class="notification-actions">
                    ${
                      !notif.is_read
                        ? `
                        <button class="btn-mark-read btn-small">Mark as read</button>
                    `
                        : ""
                    }
                </div>
            </div>
        `,
      )
      .join("")
  },

  /**
   * Mark notification as read
   */
  async markAsRead(notifId) {
    try {
      await fetch(`${API_BASE}/approvals/notifications/${notifId}/read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
      })
      this.loadNotifications()
    } catch (error) {
      console.error("Error marking notification as read:", error)
    }
  },

  /**
   * Mark all notifications as read
   */
  async markAllAsRead() {
    try {
      await fetch(`${API_BASE}/approvals/notifications/mark-all-read`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
      })
      this.loadNotifications()
    } catch (error) {
      console.error("Error marking all as read:", error)
    }
  },
}

/**
 * Approval Management Module
 * Handles event approvals and rejection
 */
const ApprovalManager = {
  /**
   * Request approval for an event
   */
  async requestApproval(eventId, reason = "") {
    try {
      const response = await fetch(`${API_BASE}/approvals/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          event_id: eventId,
          reason,
        }),
      })

      if (response.ok) {
        alert("Approval requested successfully")
        return true
      } else {
        alert("Error requesting approval")
        return false
      }
    } catch (error) {
      console.error("Error requesting approval:", error)
      return false
    }
  },

  /**
   * Get approval status for event
   */
  async getApprovalStatus(eventId) {
    try {
      const response = await fetch(`${API_BASE}/approvals/event/${eventId}`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      return await response.json()
    } catch (error) {
      console.error("Error getting approval status:", error)
      return null
    }
  },

  /**
   * Approve an event (admin only)
   */
  async approveEvent(approvalId, reason = "") {
    try {
      const response = await fetch(`${API_BASE}/approvals/${approvalId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({ reason }),
      })

      if (response.ok) {
        alert("Event approved successfully")
        return true
      } else {
        alert("Error approving event")
        return false
      }
    } catch (error) {
      console.error("Error approving event:", error)
      return false
    }
  },

  /**
   * Decline an event approval (admin only)
   */
  async declineEvent(approvalId, reason) {
    if (!reason) {
      alert("Please provide a reason for decline")
      return false
    }

    try {
      const response = await fetch(`${API_BASE}/approvals/${approvalId}/decline`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({ reason }),
      })

      if (response.ok) {
        alert("Event declined successfully")
        return true
      } else {
        alert("Error declining event")
        return false
      }
    } catch (error) {
      console.error("Error declining event:", error)
      return false
    }
  },

  /**
   * Request changes to event
   */
  async requestChanges(approvalId, reason) {
    try {
      const response = await fetch(`${API_BASE}/approvals/${approvalId}/request-changes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({ reason }),
      })

      if (response.ok) {
        alert("Change request sent to organizer")
        return true
      }
    } catch (error) {
      console.error("Error requesting changes:", error)
      return false
    }
  },

  /**
   * Resubmit event for approval
   */
  async resubmitForApproval(approvalId) {
    try {
      const response = await fetch(`${API_BASE}/approvals/${approvalId}/resubmit`, {
        method: "POST",
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      if (response.ok) {
        alert("Event resubmitted for approval")
        return true
      }
    } catch (error) {
      console.error("Error resubmitting event:", error)
      return false
    }
  },

  /**
   * Display approval status UI
   */
  displayApprovalStatus(status, eventElement) {
    const statusEl = document.createElement("div")
    statusEl.className = `approval-status badge-${status}`
    statusEl.textContent = status.toUpperCase()
    eventElement.appendChild(statusEl)
  },
}

// Initialize notification system
document.addEventListener("DOMContentLoaded", () => {
  NotificationManager.init(30000) // Poll every 30 seconds
})
