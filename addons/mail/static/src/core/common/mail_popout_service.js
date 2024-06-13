import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";

export const mailPopoutService = {
    dependencies: ["ui"],
    start(env, { ui }) {
        const anchor = document.createElement("div");
        let externalWindow;
        let currentReplacement;

        /**
         * Reset the external window to its initial state:
         * - put the current replacement back in the document
         * - clear the external window's document body
         * - set the current replacement to null
         */
        function reset() {
            if (externalWindow?.document?.body?.firstChild && anchor.isConnected) {
                anchor.after(externalWindow.document.body.firstChild);
            }
            if (externalWindow) {
                externalWindow.document.body = externalWindow.document.createElement("body");
            }
            currentReplacement = null;
        }

        /**
         * Poll the external window to detect when it is closed.
         * Trigger a resize event on the main window when the external window is closed.
         */
        async function pollClosedWindow() {
            while (externalWindow) {
                await new Promise((r) => setTimeout(r, 1000));
                if (externalWindow.closed) {
                    reset();
                    externalWindow = null;
                    ui.bus.trigger("resize");
                }
            }
        }

        /**
         * Swap the given element to the external window.
         * If the external window does not exist, it is created.
         * If an element was already swapped, it is put back in the document before the new element is swapped.
         * @param {Element} element: The element to swap to the external window
         * @param {Boolean} triggerResize: Whether to trigger a resize event on the main window
         * @returns {Window} The external window
         */
        function popout(element, triggerResize = true) {
            if (!externalWindow || externalWindow.closed) {
                externalWindow = window.open("about:blank", "_blank", "popup=yes");
                window.addEventListener("beforeunload", () => {
                    if (externalWindow && !externalWindow.closed) {
                        externalWindow.close();
                    }
                });
                pollClosedWindow();
                externalWindow.document.write(window.document.head.outerHTML);
            }
            if (element !== currentReplacement) {
                reset();
                if (element) {
                    currentReplacement = element;
                    element.after(anchor);
                    externalWindow.document.body.append(element);
                }
            }
            if (triggerResize) {
                ui.bus.trigger("resize");
            }
            return externalWindow;
        }

        return reactive({
            get externalWindow() {
                return externalWindow && externalWindow.closed ? null : externalWindow;
            },
            popout,
            reset,
        });
    },
};

registry.category("services").add("mail.popout", mailPopoutService);
