/**
 * Overlap Detection Module
 * Client-side overlap detection and conflict warnings
 */

const API_BASE = "https://api.example.com" // Declare API_BASE
const currentToken = "your_token_here" // Declare currentToken

const OverlapDetector = {
  /**
   * Check if event times overlap with existing events
   * Real-time overlap validation
   */
  async checkEventOverlap(scheduleId, startTime, endTime, excludeEventId = null) {
    try {
      const response = await fetch(`${API_BASE}/scheduling/check-overlap`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          schedule_id: scheduleId,
          start_time: startTime,
          end_time: endTime,
          exclude_event_id: excludeEventId,
        }),
      })

      return await response.json()
    } catch (error) {
      console.error("Error checking overlap:", error)
      return { has_overlap: false, error: error.message }
    }
  },

  /**
   * Check facility availability
   * Facility booking validation
   */
  async checkFacilityAvailability(building, roomNumber, startTime, endTime) {
    try {
      const response = await fetch(`${API_BASE}/scheduling/facility-availability`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          building,
          room_number: roomNumber,
          start_time: startTime,
          end_time: endTime,
        }),
      })

      return await response.json()
    } catch (error) {
      console.error("Error checking facility:", error)
      return { available: true, error: error.message }
    }
  },

  /**
   * Get suggested alternative times
   * Intelligent scheduling suggestions
   */
  async getSuggestedTimes(scheduleId, startTime, endTime, durationMinutes = null) {
    try {
      const response = await fetch(`${API_BASE}/scheduling/suggest-times`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          schedule_id: scheduleId,
          start_time: startTime,
          end_time: endTime,
          duration_minutes: durationMinutes,
        }),
      })

      return await response.json()
    } catch (error) {
      console.error("Error getting suggestions:", error)
      return { alternatives: [] }
    }
  },

  /**
   * Display overlap warning with options
   * User-friendly conflict dialog
   */
  displayOverlapWarning(conflictingEvent, alternatives) {
    const html = `
            <div class="overlap-warning">
                <h3>Schedule Conflict Detected!</h3>
                <p>Your event overlaps with:</p>
                <div class="conflicting-event">
                    <strong>${conflictingEvent.title}</strong>
                    <p>${new Date(conflictingEvent.start_time).toLocaleString()}</p>
                    <p>${conflictingEvent.location || "No location specified"}</p>
                </div>
                
                ${
                  alternatives && alternatives.length > 0
                    ? `
                    <div class="alternatives">
                        <h4>Suggested Alternative Times:</h4>
                        <div class="alternative-list">
                            ${alternatives
                              .slice(0, 3)
                              .map(
                                (alt, idx) => `
                                <div class="alternative-slot" onclick="selectAlternativeTime('${alt.start_time}', '${alt.end_time}')">
                                    <p>${new Date(alt.start_time).toLocaleString()}</p>
                                    <p>${alt.day_of_week}</p>
                                </div>
                            `,
                              )
                              .join("")}
                        </div>
                    </div>
                `
                    : ""
                }
                
                <div class="warning-actions">
                    <button class="btn-secondary" onclick="dismissOverlapWarning()">Choose Different Time</button>
                    <button class="btn-danger" onclick="acceptOverlap()">Accept Conflict</button>
                </div>
            </div>
        `

    showModal(html)
  },
}

/**
 * Real-time validation for event form
 * Live form validation
 */
function setupOverlapDetection() {
  const scheduleSelect = document.querySelector('select[name="schedule_id"]')
  const startTimeInput = document.querySelector('input[name="start_time"]')
  const endTimeInput = document.querySelector('input[name="end_time"]')
  const buildingInput = document.querySelector('input[name="building"]')
  const roomInput = document.querySelector('input[name="room_number"]')

  // Check overlap on time change
  ;[startTimeInput, endTimeInput, scheduleSelect].forEach((input) => {
    input?.addEventListener("change", async () => {
      if (!startTimeInput.value || !endTimeInput.value || !scheduleSelect.value) return

      const result = await OverlapDetector.checkEventOverlap(
        Number.parseInt(scheduleSelect.value),
        new Date(startTimeInput.value).toISOString(),
        new Date(endTimeInput.value).toISOString(),
      )

      updateOverlapStatus(result)
    })
  })

  // Check facility availability
  ;[startTimeInput, endTimeInput, buildingInput, roomInput].forEach((input) => {
    input?.addEventListener("change", async () => {
      if (!startTimeInput.value || !endTimeInput.value || !buildingInput.value) return

      const result = await OverlapDetector.checkFacilityAvailability(
        buildingInput.value,
        roomInput.value,
        new Date(startTimeInput.value).toISOString(),
        new Date(endTimeInput.value).toISOString(),
      )

      updateFacilityStatus(result)
    })
  })
}

/**
 * Update UI with overlap status
 * Visual feedback for conflicts
 */
function updateOverlapStatus(result) {
  const statusEl = document.getElementById("overlap-status") || createStatusElement()

  if (result.has_overlap) {
    statusEl.className = "status-warning"
    statusEl.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <span>Overlaps with "${result.conflicting_event.title}"</span>
        `
  } else if (result.error) {
    statusEl.className = "status-error"
    statusEl.innerHTML = `<span>Error checking availability</span>`
  } else {
    statusEl.className = "status-success"
    statusEl.innerHTML = `<span class="success-icon">✓</span><span>No conflicts</span>`
  }
}

function updateFacilityStatus(result) {
  const statusEl = document.getElementById("facility-status") || createFacilityStatusElement()

  if (!result.available) {
    statusEl.className = "status-warning"
    statusEl.innerHTML = `
            <span class="warning-icon">⚠️</span>
            <span>Room has ${result.conflict_count} conflict(s)</span>
        `
  } else {
    statusEl.className = "status-success"
    statusEl.innerHTML = `<span class="success-icon">✓</span><span>Room available</span>`
  }
}

function createStatusElement() {
  const el = document.createElement("div")
  el.id = "overlap-status"
  el.className = "overlap-status"
  document.querySelector("#create-event-form").insertBefore(el, document.querySelector('button[type="submit"]'))
  return el
}

function createFacilityStatusElement() {
  const el = document.createElement("div")
  el.id = "facility-status"
  el.className = "facility-status"
  document.querySelector("#create-event-form").insertBefore(el, document.querySelector('button[type="submit"]'))
  return el
}

function showModal(html) {
  // Dummy implementation for showModal
  console.log("Show Modal:", html)
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", setupOverlapDetection)
