import { Component, config, plugin, Plugin, props, t, useListener } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { services } from "@web/core/services";

const DEFAULT_ID = Symbol("default");

export class MailFullscreen extends Component {
    static template = "mail.Fullscreen";

    setup() {
        super.setup();
        this.props = props({
            component: t.component(),
            props: t.record().optional(),
        });
        this.fullscreen = plugin(FullscreenPlugin);
    }
}

export class FullscreenPlugin extends Plugin {
    id = undefined;
    closeOverlay = undefined;
    isBrowserFullscreen = false;
    onExitBrowserFullscreen = undefined;
    env = config("env");

    setup(env) {
        useListener(window, "fullscreenchange", () => {
            this.isBrowserFullscreen = Boolean(
                document.webkitFullscreenElement || document.fullscreenElement
            );
            if (this.isBrowserFullscreen) {
                return;
            }
            this.onExitBrowserFullscreen?.();
        });
    }

    /**
     * Leave the browser's native fullscreen mode, if currently active.
     *
     * @returns {Promise<void>}
     */
    async leaveBrowserFullscreen() {
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

    async exit(id = this.id) {
        if (!id || id !== this.id) {
            return;
        }
        this.closeOverlay?.();
        this.id = undefined;
        this.closeOverlay = undefined;
        this.onExitBrowserFullscreen = undefined;
        await this.leaveBrowserFullscreen();
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
    async enter(
        component,
        {
            browserFullscreen = false,
            onExitBrowserFullscreen,
            props,
            rootId,
            id = DEFAULT_ID,
        } = {}
    ) {
        this.closeOverlay?.();
        this.id = id;
        this.onExitBrowserFullscreen = onExitBrowserFullscreen;
        this.closeOverlay = this.env.services.overlay.add(
            MailFullscreen,
            { component, props },
            { rootId }
        );
        const el = document.body;
        if (!browserFullscreen) {
            await this.leaveBrowserFullscreen();
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
}

services.add(FullscreenPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the mail.fullscreen service are removed
 * -----------------------------------------------------------------------------
 */
registry.category("services").add("mail.fullscreen", {
    start() {
        return plugin(FullscreenPlugin);
    }
});
