import { registry } from "@web/core/registry";
import { App } from "@odoo/owl";
import { getTemplate } from "@web/core/templates";
import { browser } from "@web/core/browser/browser";

export const mailPopoutService = {
    start(env) {
        let externalWindow;
        let beforeFn;
        let afterFn;
        let app;

        /**
         * Reset the external window to its initial state:
         * - Reset the external window header from main window (for appropriate title and other meta data)
         * - clear the external window's document body
         * - destroy the current app mounted on the window
         */
        function reset() {
            if (externalWindow) {
                externalWindow.document.head.innerHTML = "";
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
         * the afterPopout hook (afterFn) is then called after the window is closed
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
         * @param {Function} beforePopout: this function is called before the component is initially mounted on the external window.
         * @param {Function} afterPopout: this function is called after the external window is closed.
         */
        function addHooks(beforePopout = () => {}, afterPopout = () => {}) {
            beforeFn = beforePopout;
            afterFn = afterPopout;
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
                externalWindow = browser.open("about:blank", "_blank", "popup=yes");
                window.addEventListener("beforeunload", () => {
                    if (externalWindow && !externalWindow.closed) {
                        externalWindow.close();
                    }
                });
                pollClosedWindow();
            }

            beforeFn();
            reset();
            app = new App(component, {
                name: "Popout",
                env,
                props,
                getTemplate,
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
