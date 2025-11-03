/**
 * Drag and Drop Module
 * Enables drag-and-drop event editing with calendar integration
 */

const draggedEvent = null
const dragSource = null

const OverlapDetector = {
  checkEventOverlap: async (scheduleId, startTime, endTime, eventId) => {
    // Mock implementation for demonstration purposes
    return { has_overlap: false }
  },
}

const API_BASE = "https://api.example.com"
const currentToken = "your_token_here"

const loadDashboardData = () => {
  // Mock implementation for demonstration purposes
  console.log("Dashboard data loaded")
}

class DragDropManager {
  constructor() {
    this.draggedElement = null
    this.dragOffset = { x: 0, y: 0 }
    this.isOver = false
  }

  /**
   * Make calendar grid droppable
   * Enables events to be dropped on calendar dates
   */
  static initializeCalendarDragDrop() {
    const calendarDays = document.querySelectorAll(".calendar-day:not(.empty)")

    calendarDays.forEach((day) => {
      day.addEventListener("dragover", (e) => {
        e.preventDefault()
        day.classList.add("drag-over")
      })

      day.addEventListener("dragleave", () => {
        day.classList.remove("drag-over")
      })

      day.addEventListener("drop", (e) => {
        e.preventDefault()
        day.classList.remove("drag-over")

        // Get date from calendar cell
        const dayNum = Number.parseInt(day.textContent)
        const year = Number.parseInt(document.getElementById("current-month").textContent.split(" ")[1])
        const month = new Date(document.getElementById("current-month").textContent).getMonth()

        const newDate = new Date(year, month, dayNum)
        DragDropManager.handleEventDroppedOnDate(e, newDate)
      })
    })
  }

  /**
   * Handle event dropped on calendar date
   * Updates event to new date
   */
  static async handleEventDroppedOnDate(e, newDate) {
    const eventData = e.dataTransfer.getData("application/json")

    if (!eventData) return

    try {
      const event = JSON.parse(eventData)

      // Calculate new time
      const oldDate = new Date(event.start_time)
      const timeDiff = oldDate.getHours() * 60 + oldDate.getMinutes()

      const newStartTime = new Date(newDate)
      newStartTime.setHours(Math.floor(timeDiff / 60), timeDiff % 60)

      const duration = (new Date(event.end_time) - new Date(event.start_time)) / (1000 * 60)
      const newEndTime = new Date(newStartTime.getTime() + duration * 60 * 1000)

      // Check for conflicts
      const overlapResult = await OverlapDetector.checkEventOverlap(
        event.schedule_id,
        newStartTime.toISOString(),
        newEndTime.toISOString(),
        event.id,
      )

      if (overlapResult.has_overlap) {
        alert(`Cannot move event: conflicts with "${overlapResult.conflicting_event.title}"`)
        return
      }

      // Update event
      const response = await fetch(`${API_BASE}/events/${event.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          start_time: newStartTime.toISOString(),
          end_time: newEndTime.toISOString(),
        }),
      })

      if (response.ok) {
        alert("Event moved successfully")
        loadDashboardData()
      }
    } catch (error) {
      console.error("Error moving event:", error)
    }
  }

  /**
   * Make event items draggable
   * Enable drag from event list
   */
  static makeEventDraggable(eventElement, eventData) {
    eventElement.draggable = true

    eventElement.addEventListener("dragstart", (e) => {
      e.dataTransfer.effectAllowed = "move"
      e.dataTransfer.setData("application/json", JSON.stringify(eventData))

      // Custom drag image
      const dragImage = document.createElement("div")
      dragImage.style.cssText = `
                background-color: ${eventData.color || "#3b82f6"};
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                position: absolute;
                left: -1000px;
                font-weight: 600;
            `
      dragImage.textContent = eventData.title
      document.body.appendChild(dragImage)
      e.dataTransfer.setDragImage(dragImage, 0, 0)

      setTimeout(() => dragImage.remove(), 0)
    })

    eventElement.addEventListener("dragend", () => {
      eventElement.style.opacity = "1"
    })
  }
}

/**
 * Timeblock drag handler for calendar week view
 * Timeblock-based drag-and-drop
 */
class TimeblockDragDrop {
  static initializeTimeblocks() {
    const timeblocks = document.querySelectorAll(".timeblock")

    timeblocks.forEach((block) => {
      block.addEventListener("dragover", (e) => {
        e.preventDefault()
        block.style.backgroundColor = "rgba(59, 130, 246, 0.1)"
      })

      block.addEventListener("dragleave", () => {
        block.style.backgroundColor = ""
      })

      block.addEventListener("drop", (e) => {
        e.preventDefault()
        block.style.backgroundColor = ""

        const eventData = e.dataTransfer.getData("application/json")
        const slotTime = block.dataset.time

        TimeblockDragDrop.rescheduleEvent(eventData, slotTime)
      })
    })
  }

  static async rescheduleEvent(eventDataStr, newTime) {
    const eventData = JSON.parse(eventDataStr)
    const [hours, minutes] = newTime.split(":").map(Number)

    const newStartTime = new Date()
    newStartTime.setHours(hours, minutes, 0)

    const duration = (new Date(eventData.end_time) - new Date(eventData.start_time)) / (1000 * 60)
    const newEndTime = new Date(newStartTime.getTime() + duration * 60 * 1000)

    try {
      const response = await fetch(`${API_BASE}/events/${eventData.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${currentToken}`,
        },
        body: JSON.stringify({
          start_time: newStartTime.toISOString(),
          end_time: newEndTime.toISOString(),
        }),
      })

      if (response.ok) {
        alert("Event rescheduled successfully")
        loadDashboardData()
      }
    } catch (error) {
      console.error("Error rescheduling event:", error)
    }
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  DragDropManager.initializeCalendarDragDrop()
  TimeblockDragDrop.initializeTimeblocks()
})
