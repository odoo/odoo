import { EventBus, Plugin } from "@odoo/owl";
import { services } from "@web/core/services";
import { session } from "@web/session";

export class RfidPlugin extends Plugin {
    /**
     * The socket is tied to the lifetime of whoever opened it, so leaving the
     * app the scanner was started from also drops the connection. A single
     * owner is assumed: this hands out itself, not a per-scope copy.
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
    /**
     * Kept until an open socket can carry it: the start command may be asked
     * for before the scanner answers.
     *
     * @private
     */
    wantsScan = false;

    // Only a scan in progress is retried, so a URL pointing at nothing never
    // turns into a loop hammering an endpoint.
    static RECONNECT_DELAYS_IN_MS = [1000, 2000, 4000];
    // Below this, a connection does not earn a fresh budget: a scanner that
    // drops every socket straight away would otherwise be retried forever.
    static HEALTHY_CONNECTION_IN_MS = 30000;

    /** @private */
    reconnectAttempt = 0;
    /** @private */
    reconnectTimeout = null;
    /** @private */
    connectedSince = null;

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
                console.warn("Invalid RFID Tag Extraction Regex:", error);
            }
        }
    }

    isSupported() {
        return Boolean(session.rfid_ws_url);
    }

    isConnected() {
        return this.socket?.readyState === WebSocket.OPEN;
    }

    connect() {
        if (this.socket) {
            return;
        }

        this.cancelReconnect();
        this.bindTriggerKeys();

        try {
            this.socket = new window.WebSocket(session.rfid_ws_url);
        } catch (error) {
            console.warn("RFID scanner: could not open a WebSocket:", error);
            this.wantsScan = false;
            this.bus.trigger("rfid_connection_changed", { connected: false, retrying: false });
            return;
        }

        this.socket.onopen = () => {
            this.connectedSince = Date.now();
            this.bus.trigger("rfid_connection_changed", { connected: true, retrying: false });
            if (this.wantsScan) {
                this.sendCommand(session.rfid_start_command);
            }
        };

        this.socket.onmessage = (event) => {
            const tags = this.extractTags(event?.data);
            if (tags.length) {
                this.bus.trigger("rfid_scanned", { tags });
            }
        };

        // `onerror` is left out on purpose: its event is opaque by spec, and
        // `onclose` always follows it -- including for a socket that never
        // opened, so a failed connection is reported like a dropped one.
        this.socket.onclose = (event) => {
            console.warn(`RFID scanner disconnected (${event.code}):`, event.reason);
            this.socket = null;

            const heldFor = this.connectedSince === null ? 0 : Date.now() - this.connectedSince;
            this.connectedSince = null;
            if (heldFor >= RfidPlugin.HEALTHY_CONNECTION_IN_MS) {
                this.reconnectAttempt = 0;
            }

            const delays = RfidPlugin.RECONNECT_DELAYS_IN_MS;
            const retrying = this.wantsScan && this.reconnectAttempt < delays.length;
            if (retrying) {
                const delay = delays[this.reconnectAttempt++];
                this.reconnectTimeout = setTimeout(() => {
                    this.reconnectTimeout = null;
                    if (this.wantsScan) {
                        this.connect();
                    }
                }, delay);
            } else {
                this.wantsScan = false;
            }
            this.bus.trigger("rfid_connection_changed", { connected: false, retrying });
        };
    }

    disconnect() {
        this.cancelReconnect();
        this.reconnectAttempt = 0;
        this.connectedSince = null;
        this.unbindTriggerKeys();

        if (!this.socket) {
            return;
        }

        this.stopScan();

        const socket = this.socket;
        this.socket = null;
        // Detached first: this teardown is not a drop to report back.
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
            socket.close();
        }
    }

    /** @private */
    cancelReconnect() {
        clearTimeout(this.reconnectTimeout);
        this.reconnectTimeout = null;
    }

    /**
     * Some scanners wire their physical triggers to plain HID keys (e.g. "F15")
     * rather than to their radio, which leaves them useless in a browser.
     * Listening to those keys turns them back into scan controls.
     */
    bindTriggerKeys() {
        if (!this.triggerKeys.size) {
            return;
        }
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
        // Swallowed before the barcode service sees it: that one focuses a
        // hidden input on any key, popping the mobile keyboard over the app.
        ev.preventDefault();
        ev.stopPropagation();

        if (ev.type === "keydown" && !ev.repeat) {
            this.bus.trigger("rfid_trigger_pressed");
        }
    };

    startScan() {
        this.wantsScan = true;
        this.reconnectAttempt = 0;
        this.connect();
        this.sendCommand(session.rfid_start_command);
    }

    stopScan() {
        this.wantsScan = false;
        this.sendCommand(session.rfid_stop_command);
    }

    /** @private */
    sendCommand(command) {
        if (command && this.isConnected()) {
            this.socket.send(command);
        }
    }

    /**
     * Scanners wrap their tags in a larger payload; the extraction regex says
     * where to find them, as its first capturing group or as the whole match.
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
        this.extractionRegex.lastIndex = 0;
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
