import { Plugin, computed, proxy, signal } from "@odoo/owl";
import { services } from "@web/core/services";

// Color of each type of logs
export const LOG_TYPES = {
    lifecycle: { badge: "dark", console: "#adb5bd" },
    signal: { badge: "info", console: "#17a2b8" },
    peer: { badge: "warning", console: "#f0ad4e" },
    state: { badge: "secondary", console: "#6c757d" },
    channel: { badge: "success", console: "#28a745" },
    message: { badge: "primary", console: "#714b67" },
    error: { badge: "danger", console: "#dc3545" },
};

// Storage of the logs and of their settings.
const MAX_LOGS = 500;
const SETTINGS_KEY = "point_of_sale.webrtc_log_settings";

// Column widths, so that the console logs are aligned.
const TYPE_WIDTH = Math.max(...Object.keys(LOG_TYPES).map((type) => type.length));
const PEER_WIDTH = 8;

// ----- Plugin ----- //

/**
 * Keeps the logs of the WebRTC plugin, to show in the debug popup or in the
 * console what happened between the devices.
 */
export class WebRtcLogPlugin extends Plugin {
    logs = signal.Array([]);
    visibleLogs = computed(() => this.logs().filter((log) => !this.isHidden(log.type)));
    settings = proxy(this.loadSettings());
    nextId = 1;

    log(type, text, peer = null) {
        const log = this.add(type, text, peer);
        if (this.settings.toConsole && !this.isHidden(type)) {
            this.printInConsole(log);
        }
    }

    logError(text, error, peer = null) {
        this.add("error", `${text}: ${error?.message || error}`, peer);
        console.error(`[WebRTC] ${text}${peer ? ` (${peer})` : ""}`, error);
    }

    add(type, text, peer) {
        const log = { id: this.nextId++, time: new Date(), type, text, peer };
        const logs = this.logs();
        logs.push(log);
        if (logs.length > MAX_LOGS) {
            logs.splice(0, logs.length - MAX_LOGS);
        }
        return log;
    }

    clear() {
        this.logs.set([]);
    }

    // ----- Settings ----- //

    loadSettings() {
        const settings = { hiddenTypes: [], toConsole: false };
        const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY));
        if (Array.isArray(saved?.hiddenTypes)) {
            settings.hiddenTypes = saved.hiddenTypes.filter((type) => type in LOG_TYPES);
        }
        if (typeof saved?.toConsole === "boolean") {
            settings.toConsole = saved.toConsole;
        }
        return settings;
    }

    isHidden(type) {
        return this.settings.hiddenTypes.includes(type);
    }

    toggleType(type) {
        const { hiddenTypes } = this.settings;
        if (this.isHidden(type)) {
            hiddenTypes.splice(hiddenTypes.indexOf(type), 1);
        } else {
            hiddenTypes.push(type);
        }
        this.saveSettings();
    }

    setToConsole(toConsole) {
        this.settings.toConsole = toConsole;
        this.saveSettings();
    }

    saveSettings() {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings));
    }

    // ----- Helpers ----- //

    shortId(id) {
        return id.split(/[-.]/)[0];
    }

    printInConsole({ type, text, peer }) {
        const bold = "font-weight:bold;margin-right:4px;";
        const typeText = type.padEnd(TYPE_WIDTH);
        const peerText = (peer ? this.shortId(peer) : "").padEnd(PEER_WIDTH);
        console.info(
            `%c[WebRTC]%c${typeText}%c${peerText}%c- ${text}`,
            `color:#e83e8c;${bold}`,
            `color:${LOG_TYPES[type].console};${bold}`,
            bold,
            ""
        );
    }
}

services.add(WebRtcLogPlugin);
