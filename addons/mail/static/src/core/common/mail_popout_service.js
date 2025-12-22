import { App } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { setElementContent } from "@web/core/utils/html";

export const mailPopoutService = {
    start(env) {
        let externalWindow;
        let beforeFn = () => {};
        let afterFn = () => {};
        let app;

        /**
         * Reset the external window to its initial state:
         * - Reset the external window header from main window (for appropriate title and other meta data)
         * - clear the external window's document body
         * - destroy the current app mounted on the window
         */
        function reset() {
            if (externalWindow?.document) {
                setElementContent(externalWindow.document.head, "");
                externalWindow.document.write(window.document.head.outerHTML);
                externalWindow.document.body = externalWindow.document.createElement("body");
            }
            if (app) {
                app.destroy();
                app = null;
            }
        }

        /**
         * Poll the external window to detect when it is closed.
         * the afterPopoutClosed hook (afterFn) is then called after the window is closed
         */
        async function pollClosedWindow() {
            while (externalWindow) {
                await new Promise((r) => setTimeout(r, 1000));
                if (externalWindow.closed) {
                    externalWindow = null;
                    afterFn();
                }
            }
        }

        /**
         * This function registers hooks (before/after the window popout)
         * @param {Function} beforePopout: this function is called before the external window is created.
         * @param {Function} afterPopoutClosed: this function is called after the external window is closed.
         */
        function addHooks(beforePopout = () => {}, afterPopoutClosed = () => {}) {
            beforeFn = beforePopout;
            afterFn = afterPopoutClosed;
        }

        /**
         * Mounts the passed component (with its props) on an external window.
         * If the external window does not exist, it is created.
         * @param {class} component: The component to be mounted.
         * @param {Props} props: The props of the component.
         * @returns {Window} The external window
         */
        function popout(component, props) {
            if (!externalWindow || externalWindow.closed) {
                beforeFn();
                externalWindow = browser.open("about:blank", "_blank", "popup=yes");
                window.addEventListener("beforeunload", () => {
                    if (externalWindow && !externalWindow.closed) {
                        externalWindow.close();
                    }
                });
                pollClosedWindow();
            }

            reset();
            app = new App(component, {
                name: "Popout",
                env,
                props,
                getTemplate,
                translatableAttributes: ["data-tooltip"],
                translateFn: _t,
            });
            app.mount(externalWindow.document.body);
            return externalWindow;
        }

        return {
            get externalWindow() {
                return externalWindow && externalWindow.closed ? null : externalWindow;
            },
            popout,
            reset,
            addHooks,
        };
    },
};

registry.category("services").add("mail.popout", mailPopoutService);
