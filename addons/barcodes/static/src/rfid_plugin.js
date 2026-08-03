import { EventBus, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { session } from "@web/session";

export class RfidPlugin extends Plugin {
    /**
     * The socket is tied to the lifetime of whoever opened it, so leaving the
     * app the scanner was started from also drops the connection.
     */
    static scoped(self, scope) {
        scope.onDestroy(() => self.disconnect());
        return self;
    }

    bus = new EventBus();

    /** @private */
    socket = null;
    /** @private */
    extractionRegex = null;
    /** @private */
    triggerKeys = new Set();

    setup() {
        this.triggerKeys = new Set(
            (session.rfid_trigger_keys || "")
                .split(",")
                .map((key) => key.trim())
                .filter(Boolean)
        );

        if (session.rfid_tag_extraction_regex) {
            try {
                this.extractionRegex = new RegExp(session.rfid_tag_extraction_regex, "g");
            } catch (error) {
                console.error("Invalid RFID Tag Extraction Regex:", error);
            }
        }
    }

    // A scanner is usable only once an URL was configured to reach it.
    get isSupported() {
        return Boolean(session.rfid_ws_url);
    }

    connect({ onReady } = {}) {
        if (this.socket?.readyState === WebSocket.OPEN) {
            this.bindTriggerKeys();
            onReady?.();
            return;
        }

        this.disconnect(); // Unbinds the trigger keys, so bind them back after.
        this.bindTriggerKeys();

        try {
            this.socket = new window.WebSocket(session.rfid_ws_url);
        } catch (error) {
            console.error("WebSocket connection error:", error);
            return;
        }

        this.socket.onopen = () => {
            console.log("RFID Scanner connected.");
            onReady?.();
        };

        this.socket.onmessage = (event) => {
            const tags = this.extractTags(event?.data);
            if (tags.length) {
                this.bus.trigger("rfid_scanned", { tags });
            }
        };

        this.socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
        };

        this.socket.onclose = (event) => {
            console.log("RFID Scanner disconnected:", event.reason);
            this.socket = null;
        };
    }

    disconnect() {
        this.unbindTriggerKeys();

        if (!this.socket) {
            return;
        }

        this.stopScan();

        this.socket.onopen = null;
        this.socket.onmessage = null;
        this.socket.onerror = null;
        this.socket.onclose = null;

        if (
            this.socket.readyState === WebSocket.OPEN ||
            this.socket.readyState === WebSocket.CONNECTING
        ) {
            this.socket.close();
        }
        this.socket = null;
    }

    /**
     * Some scanners expose their physical triggers as plain HID keys (e.g. "F15")
     * instead of wiring them to their radio, which leaves those triggers useless
     * in a browser. Listening to those keys turns them back into scan controls.
     * A handle usually has several of them, all doing the same thing.
     */
    bindTriggerKeys() {
        if (!this.triggerKeys.size) {
            return;
        }
        // Same handler and phase on each call, so binding twice is a no-op.
        window.addEventListener("keydown", this.onTriggerKey, { capture: true });
        window.addEventListener("keyup", this.onTriggerKey, { capture: true });
    }

    unbindTriggerKeys() {
        window.removeEventListener("keydown", this.onTriggerKey, { capture: true });
        window.removeEventListener("keyup", this.onTriggerKey, { capture: true });
    }

    /** @private */
    onTriggerKey = (ev) => {
        if (!this.triggerKeys.has(ev.code)) {
            return;
        }
        // Swallowed during the capture phase, before the barcode service sees it:
        // that one focuses a hidden input on any key, which pops the mobile
        // keyboard open over the app.
        ev.preventDefault();
        ev.stopPropagation();

        // Holding the trigger down repeats the key, and releasing it is not a
        // second press.
        if (ev.type === "keydown" && !ev.repeat) {
            this.bus.trigger("rfid_trigger_pressed");
        }
    };

    startScan() {
        const command = session.rfid_start_command;
        if (this.socket?.readyState === WebSocket.OPEN && command) {
            console.log("Starting RFID scan...");
            this.socket.send(command);
        }
    }

    stopScan() {
        const command = session.rfid_stop_command;
        if (this.socket?.readyState === WebSocket.OPEN && command) {
            console.log("Stopping RFID scan...");
            this.socket.send(command);
        }
    }

    /**
     * Scanners usually wrap the tags they read into a larger payload. The
     * extraction regex tells where to find them, either as its first capturing
     * group or as the whole match.
     *
     * @private
     * @param {string} data raw message sent by the scanner
     * @returns {string[]}
     */
    extractTags(data) {
        const tags = [];
        if (!this.extractionRegex || !data) {
            return tags;
        }
        this.extractionRegex.lastIndex = 0; // Reset regex state before processing new data.
        let match;
        while ((match = this.extractionRegex.exec(data)) !== null) {
            if (match.index === this.extractionRegex.lastIndex) {
                // Zero-width match, advance manually to avoid an infinite loop.
                this.extractionRegex.lastIndex++;
            }
            const tag = match[1] || match[0];
            if (tag) {
                tags.push(tag);
            }
        }
        return tags;
    }
}

services.add(RfidPlugin);
