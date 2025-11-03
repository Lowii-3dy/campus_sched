/**
 * Color Coding System
 * Manages color assignment and theme for schedules and events
 */

const ColorCodeing = {
  // Predefined color palette
  colors: [
    { hex: "#3b82f6", name: "Blue", category: "primary" },
    { hex: "#10b981", name: "Green", category: "success" },
    { hex: "#f59e0b", name: "Amber", category: "warning" },
    { hex: "#ef4444", name: "Red", category: "danger" },
    { hex: "#a855f7", name: "Purple", category: "secondary" },
    { hex: "#06b6d4", name: "Cyan", category: "info" },
    { hex: "#ec4899", name: "Pink", category: "accent" },
    { hex: "#f97316", name: "Orange", category: "secondary" },
  ],

  /**
   * Get color by hex code
   */
  getColor(hex) {
    return this.colors.find((c) => c.hex === hex) || this.colors[0]
  },

  /**
   * Get all colors
   */
  getAllColors() {
    return this.colors
  },

  /**
   * Apply color to element
   */
  applyColor(element, hex, isDark = true) {
    element.style.backgroundColor = hex
    element.style.borderLeftColor = hex

    // Automatically adjust text color based on background
    const textColor = this.getContrastColor(hex)
    element.style.color = textColor
  },

  /**
   * Get contrasting text color (black or white)
   */
  getContrastColor(hexColor) {
    const hex = hexColor.replace("#", "")
    const r = Number.parseInt(hex.substring(0, 2), 16)
    const g = Number.parseInt(hex.substring(2, 4), 16)
    const b = Number.parseInt(hex.substring(4, 6), 16)

    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    return luminance > 0.5 ? "#000000" : "#ffffff"
  },

  /**
   * Create color picker UI
   */
  createColorPicker(selectedColor = "#3b82f6", onColorChange = null) {
    const picker = document.createElement("div")
    picker.className = "color-picker"

    this.colors.forEach((color) => {
      const option = document.createElement("label")
      option.className = "color-option"
      option.innerHTML = `
                <input 
                    type="radio" 
                    name="event-color" 
                    value="${color.hex}" 
                    ${color.hex === selectedColor ? "checked" : ""}
                    onchange="${onColorChange ? `${onColorChange}('${color.hex}')` : ""}"
                >
                <span class="color-swatch" style="background-color: ${color.hex};" title="${color.name}"></span>
                <span class="color-name">${color.name}</span>
            `
      picker.appendChild(option)
    })

    return picker
  },

  /**
   * Apply gradient based on event status
   */
  applyStatusGradient(element, status) {
    const gradients = {
      pending: "linear-gradient(135deg, #f59e0b, #f97316)",
      approved: "linear-gradient(135deg, #10b981, #059669)",
      declined: "linear-gradient(135deg, #ef4444, #dc2626)",
      draft: "linear-gradient(135deg, #6b7280, #4b5563)",
    }

    if (gradients[status]) {
      element.style.background = gradients[status]
    }
  },
}

/**
 * Schedule Color Manager
 * Per-schedule color management
 */
class ScheduleColorManager {
  constructor() {
    this.scheduleColors = new Map()
  }

  /**
   * Set color for schedule
   */
  setScheduleColor(scheduleId, hex) {
    this.scheduleColors.set(scheduleId, hex)
  }

  /**
   * Get color for schedule
   */
  getScheduleColor(scheduleId) {
    return this.scheduleColors.get(scheduleId) || "#3b82f6"
  }

  /**
   * Load schedule colors from API
   */
  async loadScheduleColors(API_BASE, currentToken) {
    try {
      const response = await fetch(`${API_BASE}/schedules`, {
        headers: { Authorization: `Bearer ${currentToken}` },
      })

      const data = await response.json()
      data.schedules.forEach((schedule) => {
        this.setScheduleColor(schedule.id, schedule.color)
      })
    } catch (error) {
      console.error("Error loading schedule colors:", error)
    }
  }

  /**
   * Apply color to all events in schedule
   */
  applyScheduleColorsToEvents() {
    document.querySelectorAll("[data-schedule-id]").forEach((element) => {
      const scheduleId = Number.parseInt(element.dataset.scheduleId)
      const color = this.getScheduleColor(scheduleId)
      ColorCodeing.applyColor(element, color)
    })
  }
}

/**
 * Initialize color system
 */
document.addEventListener("DOMContentLoaded", () => {
  const API_BASE = "https://api.example.com" // Declare API_BASE here
  const currentToken = "your_token_here" // Declare currentToken here
  const colorManager = new ScheduleColorManager()
  colorManager.loadScheduleColors(API_BASE, currentToken).then(() => {
    colorManager.applyScheduleColorsToEvents()
  })
})
