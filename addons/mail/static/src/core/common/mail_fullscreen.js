import { Component, reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const DEFAULT_ID = Symbol("default");

export class MailFullscreen extends Component {
    static props = [];
    static template = "mail.Fullscreen";

    setup() {
        super.setup();
        this.fullscreen = useService("mail.fullscreen");
    }
}

export const fullscreenService = {
    start() {
        registry.category("main_components").add("mail.fullscreen", { Component: MailFullscreen });
        const state = reactive({
            component: undefined,
            props: undefined,
            id: undefined,
            exit,
            enter,
        });
        async function exit(id = state.id) {
            if (id !== state.id) {
                return;
            }
            state.component = undefined;
            state.props = undefined;
            state.id = undefined;
            const fullscreenElement =
                document.webkitFullscreenElement || document.fullscreenElement;
            if (fullscreenElement) {
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    await document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    await document.webkitCancelFullScreen();
                }
            }
        }
        /**
         * @param component
         * @param {object} [options]
         * @param [options.props]
         * @param {any} [options.id]
         * @param {boolean} [options.keepBrowserHeader] - Optional flag to specify whether to keep
         * the browser's header (address bar, tabs, etc.) visible.
         * @returns {Promise<void>}
         */
        async function enter(
            component,
            { keepBrowserHeader = false, props, id = DEFAULT_ID } = {}
        ) {
            this.exit();
            state.component = component;
            state.props = props;
            state.id = id;
            const el = document.body;
            if (keepBrowserHeader) {
                return;
            }
            try {
                if (el.requestFullscreen) {
                    await el.requestFullscreen();
                } else if (el.mozRequestFullScreen) {
                    await el.mozRequestFullScreen();
                } else if (el.webkitRequestFullscreen) {
                    await el.webkitRequestFullscreen();
                }
            } catch {
                // doing nothing, we're just in non-native fullscreen.
            }
        }
        window.addEventListener("fullscreenchange", () => {
            const isFullscreen = Boolean(
                document.webkitFullscreenElement || document.fullscreenElement
            );
            if (!isFullscreen) {
                exit();
            }
        });
        return state;
    },
};

registry.category("services").add("mail.fullscreen", fullscreenService);
