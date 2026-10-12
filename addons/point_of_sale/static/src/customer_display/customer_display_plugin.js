import { Plugin, signal } from "@odoo/owl";
import { services } from "@web/core/services";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { getOnNotified, uuidv4 } from "@point_of_sale/utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

export const CONSOLE_COLOR = "#F5B427";

/**
 * Display half of the customer display: receives the payloads a terminal sends
 * and exposes them to the UI.
 */
export class CustomerDisplayPlugin extends Plugin {
    data = signal({});

    setup() {
        this.deviceId = uuidv4();
        this.currentTheme = new URLSearchParams(location.search).get("theme") || "light";

        // Fallback communication channel used when the system connection is unavailable (e.g., network loss).
        // NOTE: Works only between contexts within the same browser (tabs/windows sharing the same origin).
        this.channel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
    }

    /**
     * @param {Object} options
     * @param {Object} options.bus - bus service, to receive payloads and pings.
     */
    init({ bus } = {}) {
        const onNotified = getOnNotified(bus, session.access_token);
        onNotified(
            `REGISTER_CUSTOMER_DISPLAY_DEVICE-${session.identifier}`,
            ({ action }) => action === "PING" && this._announce("ADD")
        );

        onNotified(
            `UPDATE_CUSTOMER_DISPLAY-${session.identifier}`,
            this._onDataReceived.bind(this)
        );
        this.channel.onmessage = this._onDataReceived.bind(this);

        this._announce("ADD");

        // `pagehide` also covers the tab being frozen or closed on mobile.
        window.addEventListener("pagehide", () => this._announce("REMOVE", true));
    }

    _announce(action, unloading = false) {
        const params = {
            config_id: session.config_id,
            identifier: session.identifier,
            access_token: session.access_token,
            payload: { device_id: this.deviceId, action },
        };
        const registerRoute = "/pos_customer_display/register-device";
        if (unloading) {
            const data = JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params });
            navigator.sendBeacon(registerRoute, new Blob([data], { type: "application/json" }));
            return;
        }
        rpc(registerRoute, params).catch((error) =>
            logPosMessage(
                "CustomerDisplay",
                "announce",
                `Failed to ${action} this customer display`,
                CONSOLE_COLOR,
                [error]
            )
        );
    }

    _onDataReceived(rawData) {
        if (typeof rawData !== "string") {
            return;
        }
        let parsedData;
        try {
            parsedData = JSON.parse(rawData);
        } catch (error) {
            logPosMessage(
                "CustomerDisplayPlugin",
                "_onDataReceived",
                "Failed to parse payload message",
                CONSOLE_COLOR,
                [error]
            );
            return;
        }
        if (parsedData.clearData) {
            this.data.set({});
            return;
        }
        this._applyTheme(parsedData.displayTheme);
        this.data.set({ ...this.data(), ...parsedData });
    }

    _applyTheme(theme) {
        if (!theme || this.currentTheme === theme) {
            return;
        }
        const searchParams = new URLSearchParams(location.search);
        searchParams.set("theme", theme);
        // Reload page to apply the new theme
        location.search = searchParams.toString();
    }
}

services.add(CustomerDisplayPlugin);
