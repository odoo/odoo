import { reactive } from "@odoo/owl";
import { _t } from "../l10n/translation";
import { ConnectionLostError, rpc, rpcBus } from "../network/rpc";
import { registry } from "../registry";
import { browser } from "../browser/browser";

const selectors = [
    "button:not([data-offline-available])",
    "input[type='checkbox']:not([disabled])", // deactivate the checkboxs.
];

function disableButtons() {
    document.querySelectorAll(selectors.join(", ")).forEach((el) => {
        el.setAttribute("disabled", "");
        el.classList.add("opacity-50");
        el.classList.add("o_offline_cursor");
    });
}

function enableButtons() {
    document.querySelectorAll(".o_offline_cursor").forEach((el) => {
        el.removeAttribute("disabled");
        el.classList.remove("opacity-50");
        el.classList.remove("o_offline_cursor");
    });
}

const offlineSerice = {
    dependencies: ["notification"],

    async start(env, { notification }) {
        // TODO: Here we are going to depend on the first RPC that crash with a ConnectionLostError
        // Maybe could be interesting to be pro-active and call checkConnection at the beginning.

        let closeNotification = () => {};
        let observer;

        const offlineS = reactive(
            {
                offline: false,
                views: ["list", "kanban", "form"],
            },
            () => {
                if (offlineS.offline) {
                    closeNotification = notification.add(_t("Connection lost"), {
                        type: "danger",
                    });
                    disableButtons();
                    // Create an observer instance linked to the callback function
                    observer = new MutationObserver((mutationList) => {
                        if (offlineS.offline && mutationList.find((m) => m.addedNodes.length > 0)) {
                            disableButtons();
                        }
                    });
                    // Start observing the target node for configured mutations
                    observer.observe(document.body, {
                        childList: true, // listen for direct children being added/removed
                        subtree: true, // also observe descendants (not just direct children)
                    });
                    // comment from here to easy test
                    let delay = 2000;
                    browser.setTimeout(function checkConnection() {
                        if (offlineS.offline) {
                            rpc("/web/webclient/version_info", {})
                                .then(function () {
                                    offlineS.offline = false;
                                })
                                .catch(() => {
                                    // exponential backoff, with some jitter
                                    delay = delay * 1.5 + 500 * Math.random();
                                    browser.setTimeout(checkConnection, delay);
                                });
                        }
                    }, delay);
                    // end of commenting for test
                } else {
                    enableButtons();
                    closeNotification();
                    observer?.disconnect();
                    env.services.notification.add(_t("Connection restored"), {
                        type: "success",
                    });
                }
            }
        );

        // Activate the reactivity!
        offlineS.offline;

        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            if (!ev.detail.error) {
                // comment to easy test
                offlineS.offline = false;
            } else {
                if (ev.detail.error instanceof ConnectionLostError) {
                    offlineS.offline = true;
                }
            }
        });

        return offlineS;
    },
};

registry.category("services").add("offline", offlineSerice);
