import { reactive, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConnectionLostError, rpc, rpcBus } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const SELECTORS_TO_DISABLE = [
    "button:not([data-available-offline]):not([disabled])",
    "input[type='checkbox']:not([data-available-offline]):not([disabled])",
];

function offlineUI() {
    document.querySelectorAll(SELECTORS_TO_DISABLE.join(", ")).forEach((el) => {
        el.setAttribute("disabled", "");
        el.classList.add("o_disabled_offline");
    });
}

function onlineUI() {
    document.querySelectorAll(".o_disabled_offline").forEach((el) => {
        el.removeAttribute("disabled");
        el.classList.remove("o_disabled_offline");
    });
}

export const offlineService = {
    async start() {
        let timeout;
        let observer;

        async function checkConnection() {
            try {
                await rpc("/web/webclient/version_info", {});
            } catch {
                status.offline = true;
                return;
            }
            status.offline = false;
        }

        const status = reactive(
            {
                offline: false,
            },
            () => {
                if (status.offline) {
                    // Disable everything in the UI that isn't marked as available offline
                    offlineUI();
                    // Create an observer instance linked to the callback function to keep disabling
                    // buttons that would appear in the DOM while being offline
                    observer = new MutationObserver((mutationList) => {
                        if (status.offline && mutationList.find((m) => m.addedNodes.length > 0)) {
                            offlineUI();
                        }
                    });
                    observer.observe(document.body, {
                        childList: true, // listen for direct children being added/removed
                        subtree: true, // also observe descendants (not just direct children)
                    });

                    // Repeatedly check if connection is back
                    let delay = 2000;
                    const _checkConnection = async () => {
                        if (status.offline) {
                            await checkConnection();
                            // exponential backoff, with some jitter
                            delay = delay * 1.5 + 500 * Math.random();
                            timeout = browser.setTimeout(_checkConnection, delay);
                        }
                    };
                    timeout = browser.setTimeout(_checkConnection, delay);
                } else {
                    onlineUI();
                    observer?.disconnect();
                    browser.clearTimeout(timeout);
                }
            }
        );
        status.offline; // activate the reactivity!

        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            status.offline = ev.detail.error instanceof ConnectionLostError;
        });

        browser.addEventListener("offline", () => {
            if (!status.offline) {
                checkConnection();
            }
        });
        browser.addEventListener("online", () => {
            if (status.offline) {
                checkConnection();
            }
        });

        return {
            status,
            checkConnection,
        };
    },
};

registry.category("services").add("offline", offlineService);

export function useOfflineStatus() {
    return useState(useService("offline").status);
}
