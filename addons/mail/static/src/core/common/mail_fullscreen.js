import { Component, reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const DEFAULT_ID = Symbol("default");

export class MailFullscreen extends Component {
    static props = ["component", "props?"];
    static template = "mail.Fullscreen";

    setup() {
        super.setup();
        this.fullscreen = useService("mail.fullscreen");
    }
}

export const fullscreenService = {
    start(env) {
        const state = reactive({ enter, exit, id: undefined, closeOverlay: undefined });
        async function exit(id = state.id) {
            if (!id || id !== state.id) {
                return;
            }
            state.closeOverlay?.();
            state.id = undefined;
            state.closeOverlay = undefined;
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
         * @param {string} [options.rootId] - Optional root id to pass to the overlay.
         * @returns {Promise<void>}
         */
        async function enter(
            component,
            { keepBrowserHeader = false, props, rootId, id = DEFAULT_ID } = {}
        ) {
            state.closeOverlay?.();
            state.id = id;
            state.closeOverlay = env.services.overlay.add(
                MailFullscreen,
                { component, props },
                { rootId }
            );
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
                state.exit();
            }
        });
        return state;
    },
};

registry.category("services").add("mail.fullscreen", fullscreenService);
