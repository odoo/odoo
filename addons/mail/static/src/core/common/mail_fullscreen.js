import { Component, props, proxy, signal, t, useListener } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const DEFAULT_ID = Symbol("default");

const FULLSCREEN_CHANGE_EVENTS = [
    "fullscreenchange", // standard, element entered/left fullscreen
    "webkitfullscreenchange", // Safari < 16.4
    "webkitbeginfullscreen", // iOS video entered native fullscreen
    "webkitendfullscreen", // iOS video left native fullscreen
];

/**
 * Returns the element currently in fullscreen mode, if any.
 * Supports standard and WebKit-prefixed properties, as well as iOS native video
 * fullscreen which is not reflected on the document.
 *
 * @returns {Element|null}
 */
export function getFullscreenElement() {
    return (
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        [...document.querySelectorAll("video")].find(
            (videoEl) => videoEl.webkitDisplayingFullscreen
        ) ||
        null
    );
}

/**
 * Hook returning a signal informing if an element is currently fullscreen
 * updated on every fullscreen change
 *
 * @returns {import("@odoo/owl").Signal<boolean>}
 */
export function useIsFullscreen() {
    const isFullscreen = signal(Boolean(getFullscreenElement()));
    const update = () => isFullscreen.set(Boolean(getFullscreenElement()));
    for (const eventName of FULLSCREEN_CHANGE_EVENTS) {
        useListener(document, eventName, update, { capture: true });
    }
    return isFullscreen;
}

/**
 * Request fullscreen on an element across browsers, falling back to WebKit-prefixed
 * APIs and iOS video fullscreen (webkitEnterFullscreen) when explicitly opted in.
 *
 * @param {Element} el
 * @param {Object} [options]
 * @param {boolean} [options.videoFallback=false] - Whether to fall back to video.webkitEnterFullscreen
 *  if element-level fullscreen is unsupported (e.g. for video players on iOS).
 * @returns {Promise<void>}
 */
export async function requestFullscreen(el, { videoFallback = false } = {}) {
    if (!el) {
        return;
    }
    try {
        if (el.requestFullscreen) {
            await el.requestFullscreen();
            return;
        }
        if (el.webkitRequestFullscreen) {
            await el.webkitRequestFullscreen();
            return;
        }
        if (el.mozRequestFullScreen) {
            await el.mozRequestFullScreen();
            return;
        }
    } catch {
        // Element fullscreen request failed or denied. Do not fall back to video.
        return;
    }
    if (videoFallback) {
        const videoEl = el.tagName === "VIDEO" ? el : el.querySelector("video");
        if (videoEl?.webkitEnterFullscreen) {
            try {
                videoEl.webkitEnterFullscreen();
            } catch {
                // Ignore failure
            }
        }
    }
}

/**
 * Exit fullscreen across browsers, if active.
 *
 * @returns {Promise<void>}
 */
export async function exitFullscreen() {
    const fullscreenElement = getFullscreenElement();
    if (!fullscreenElement) {
        return;
    }
    try {
        if (!document.fullscreenElement && !document.webkitFullscreenElement) {
            // iOS native video fullscreen
            fullscreenElement.webkitExitFullscreen?.();
        } else if (document.exitFullscreen) {
            await document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            await document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            await document.mozCancelFullScreen();
        } else if (document.webkitCancelFullScreen) {
            await document.webkitCancelFullScreen();
        }
    } catch {
        // Ignore failure
    }
}

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
        async function exit(id = state.id) {
            if (!id || id !== state.id) {
                return;
            }
            state.closeOverlay?.();
            state.id = undefined;
            state.closeOverlay = undefined;
            state.onExitBrowserFullscreen = undefined;
            await exitFullscreen();
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
                await exitFullscreen();
                return;
            }
            await requestFullscreen(el);
        }
        const onFullscreenChange = () => {
            state.isBrowserFullscreen = Boolean(getFullscreenElement());
            if (state.isBrowserFullscreen) {
                return;
            }
            state.onExitBrowserFullscreen?.();
        };
        for (const eventName of FULLSCREEN_CHANGE_EVENTS) {
            document.addEventListener(eventName, onFullscreenChange, { capture: true });
        }
        return state;
    },
};

registry.category("services").add("mail.fullscreen", fullscreenService);
