import { proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

export const CustomerDisplayDataService = {
    dependencies: ["webrtc"],
    async start(env, services) {
        return this.setup(...arguments);
    },
    async setup(env, { webrtc }) {
        const data = proxy({});
        const pairedDeviceUuid = localStorage.getItem("device_uuid");

        const currentTheme = new URLSearchParams(browser.location.search).get("theme") || "light";

        const _processDisplayUpdate = (payload) => {
            const { displayTheme: posTheme } = payload;
            if (posTheme && currentTheme !== posTheme) {
                const searchParams = new URLSearchParams(browser.location.search);
                searchParams.set("theme", posTheme);
                // Reload page to apply the new theme
                browser.location.search = searchParams.toString();
                return;
            }
            Object.assign(data, payload);
        };

        webrtc.register("update_customer_display", (peer, data) => {
            if (
                webrtc.group === "customer_display" &&
                peer.group === "terminal" &&
                peer.deviceUuid === pairedDeviceUuid
            ) {
                _processDisplayUpdate(data);
            }
        });

        webrtc.registerSnapshot("update_customer_display", {
            build: () => null,
            apply: (peer, payload) => {
                if (
                    webrtc.group === "customer_display" &&
                    peer.group === "terminal" &&
                    peer.deviceUuid === pairedDeviceUuid
                ) {
                    _processDisplayUpdate(payload);
                }
            },
        });

        return data;
    },
};

registry.category("services").add("customer_display_data", CustomerDisplayDataService);
