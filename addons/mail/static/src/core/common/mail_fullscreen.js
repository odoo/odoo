import { Component, props, proxy, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const DEFAULT_ID = Symbol("default");

export class MailFullscreen extends Component {
    static template = "mail.Fullscreen";

    setup() {
        super.setup();
        this.props = props({
            component: t.component(),
            props: t.record().optional(),
        });
        this.fullscreen = useService("mail.fullscreen");
    }
}

export const fullscreenService = {
    start(env) {
        const state = proxy({
            enter,
            exit,
            id: undefined,
            closeOverlay: undefined,
            isBrowserFullscreen: false,
            onExitBrowserFullscreen: undefined,
        });
        /**
         * Leave the browser's native fullscreen mode, if currently active.
         *
         * @returns {Promise<void>}
         */
        async function leaveBrowserFullscreen() {
            const fullscreenElement =
                document.webkitFullscreenElement || document.fullscreenElement;
            if (!fullscreenElement) {
                return;
            }
            if (document.exitFullscreen) {
                await document.exitFullscreen();
            } else if (document.mozCancelFullScreen) {
                await document.mozCancelFullScreen();
            } else if (document.webkitCancelFullScreen) {
                await document.webkitCancelFullScreen();
            }
        }
        async function exit(id = state.id) {
            if (!id || id !== state.id) {
                return;
            }
            state.closeOverlay?.();
            state.id = undefined;
            state.closeOverlay = undefined;
            state.onExitBrowserFullscreen = undefined;
            await leaveBrowserFullscreen();
        }
        /**
         * @param component
         * @param {object} [options]
         * @param [options.props]
         * @param {any} [options.id]
         * @param {boolean} [options.browserFullscreen] - Optional flag to request the browser's
         * native fullscreen mode, hiding its header (address bar, tabs, etc.). When falsy, the
         * overlay is shown while keeping the browser header visible.
         * @param {() => void} [options.onExitBrowserFullscreen] - Optional callback invoked instead of
         * `exit()` when the browser's native fullscreen mode is left (e.g. with ESC) while this
         * overlay is active, letting the owner decide whether to close or keep the overlay.
         * @param {string} [options.rootId] - Optional root id to pass to the overlay.
         * @returns {Promise<void>}
         */
        async function enter(
            component,
            {
                browserFullscreen = false,
                onExitBrowserFullscreen,
                props,
                rootId,
                id = DEFAULT_ID,
            } = {}
        ) {
            state.closeOverlay?.();
            state.id = id;
            state.onExitBrowserFullscreen = onExitBrowserFullscreen;
            state.closeOverlay = env.services.overlay.add(
                MailFullscreen,
                { component, props },
                { rootId }
            );
            const el = document.body;
            if (!browserFullscreen) {
                await leaveBrowserFullscreen();
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
            state.isBrowserFullscreen = Boolean(
                document.webkitFullscreenElement || document.fullscreenElement
            );
            if (state.isBrowserFullscreen) {
                return;
            }
            state.onExitBrowserFullscreen?.();
        });
        return state;
    },
};

registry.category("services").add("mail.fullscreen", fullscreenService);
