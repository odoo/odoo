import { Plugin, computed, proxy, signal } from "@odoo/owl";
import { services } from "@web/core/services";

// ----- Log types ----- //

// Color of each type of logs: a Bootstrap color for the badge of the popup, a
// CSS color for the console.
export const LOG_TYPES = {
    lifecycle: { badge: "dark", console: "#adb5bd" },
    signal: { badge: "info", console: "#17a2b8" },
    peer: { badge: "warning", console: "#f0ad4e" },
    state: { badge: "secondary", console: "#6c757d" },
    channel: { badge: "success", console: "#28a745" },
    message: { badge: "primary", console: "#714b67" },
    error: { badge: "danger", console: "#dc3545" },
};

// Hiding a type of logs doesn't free them: keep the last ones only.
const MAX_LOGS = 500;
const SETTINGS_KEY = "point_of_sale.webrtc_log_settings";
// Pads the type and the peer so that the logs are aligned in the console.
const TYPE_WIDTH = Math.max(...Object.keys(LOG_TYPES).map((type) => type.length));
const PEER_WIDTH = 8; // length of `shortId` of a uuid

// ----- Plugin ----- //

/**
 * Logs of the WebRTC plugin, shown in the WebRTC debug popup and optionally
 * printed in the console. The settings (hidden types, console) are kept in the
 * local storage, so that they survive a reload.
 */
export class WebRtcLogPlugin extends Plugin {
    logs = signal.Array([]);
    visibleLogs = computed(() => this.logs().filter((log) => !this.isHidden(log.type)));
    settings = proxy(this.loadSettings());
    nextId = 1;

    /**
     * @param {string} type - a key of `LOG_TYPES`
     * @param {string} text
     * @param {string} [peer] - id of the other terminal, if any
     */
    log(type, text, peer = null) {
        const log = this.add(type, text, peer);
        if (this.settings.toConsole && !this.isHidden(type)) {
            this.printInConsole(log);
        }
    }

    /**
     * Always printed with `console.error`, whatever the settings.
     */
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
        try {
            const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY));
            if (Array.isArray(saved?.hiddenTypes)) {
                settings.hiddenTypes = saved.hiddenTypes.filter((type) => type in LOG_TYPES);
            }
            if (typeof saved?.toConsole === "boolean") {
                settings.toConsole = saved.toConsole;
            }
        } catch {
            // Storage unavailable or invalid value: default settings.
        }
        return settings;
    }

    isHidden(type) {
        return this.settings.hiddenTypes.includes(type);
    }

    /**
     * Shows or hides a type of logs, in the popup and in the console.
     */
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
        try {
            localStorage.setItem(SETTINGS_KEY, JSON.stringify(this.settings));
        } catch {
            // Storage unavailable (e.g. private mode): the settings last until the reload.
        }
    }

    // ----- Helpers ----- //

    /**
     * @param {string} id - id of a terminal, a uuid
     * @returns {string} the first part of the id, enough to tell the terminals apart
     */
    shortId(id) {
        // The start of the uuid (or the name of a test terminal), without the
        // tag of the session.
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
