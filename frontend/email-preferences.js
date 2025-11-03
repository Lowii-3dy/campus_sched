/**
 * Email Preferences Module
 * Handles user email notification settings
 */

const API_BASE = "https://api.example.com"
const currentToken = "your_token_here"

const EmailPreferences = {
  /**
   * Load user email preferences
   */
  async loadPreferences() {
    try {
      const response = await fetch(`${API_BASE}/email/preferences`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      const prefs = await response.json()

      // Set form values
      document.getElementById("approval-emails").checked = prefs.receive_approval_emails
      document.getElementById("reminders").checked = prefs.receive_reminders
      document.getElementById("schedule-updates").checked = prefs.receive_schedule_updates
      document.getElementById("reminder-hours").value = prefs.reminder_hours_before
    } catch (error) {
      console.error("Error loading preferences:", error)
    }
  },

  /**
   * Save user email preferences
   */
  async savePreferences(data) {
    try {
      const response = await fetch(`${API_BASE}/email/preferences`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify(data),
      })

      if (response.ok) {
        showStatus("Preferences saved successfully", "success")
        return true
      } else {
        showStatus("Error saving preferences", "error")
        return false
      }
    } catch (error) {
      console.error("Error saving preferences:", error)
      showStatus("Error saving preferences", "error")
      return false
    }
  },
}

/**
 * Send test email
 */
async function sendTestEmail() {
  try {
    const response = await fetch(`${API_BASE}/email/test`, {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
    })

    if (response.ok) {
      showStatus("Test email sent successfully", "success")
    } else {
      showStatus("Error sending test email", "error")
    }
  } catch (error) {
    console.error("Error sending test email:", error)
    showStatus("Error sending test email", "error")
  }
}

function showStatus(message, type) {
  const statusEl = document.getElementById("preference-status")
  statusEl.textContent = message
  statusEl.className = `status-message status-${type}`
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  EmailPreferences.loadPreferences()

  document.getElementById("email-preferences-form").addEventListener("submit", async (e) => {
    e.preventDefault()

    const formData = new FormData(document.getElementById("email-preferences-form"))
    const data = {
      receive_approval_emails: formData.get("receive_approval_emails") === "on",
      receive_reminders: formData.get("receive_reminders") === "on",
      receive_schedule_updates: formData.get("receive_schedule_updates") === "on",
      reminder_hours_before: Number.parseInt(formData.get("reminder_hours_before")),
    }

    await EmailPreferences.savePreferences(data)
  })
})
