import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { Component, Plugin, types, usePlugin, useProps, xml } from "@odoo/owl";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { HotkeyPlugin } from "@web/core/hotkeys/hotkey_plugin";
import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { services } from "@web/core/services";
import { useRootCreator } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";

const DEFAULT_ID = Symbol("default");

class OverlayWrapper extends Component {
    static template = xml`
        <t t-component="this.props.component" t-props="this.props.componentProps"/>
        <OverlayContainer/>
    `;
    static components = { OverlayContainer };
    props = useProps({
        component: types.any(),
        componentProps: types.object(),
    });
    setup() {
        this.overlay = usePlugin(OverlayPlugin);
        useOwnDebugContext();
    }
}

export const POLL_CLOSE_WINDOW_TIMEOUT = 1000;

/**
 * Manages one external window (popup or picture-in-picture) identified by `id`.
 * Obtained from `MailPopoutPlugin.createManager`.
 */
export class PopoutManager {
    #id;
    /** @type {(window: Window) => Promise<void>} */
    #addAssets;
    /** @type {ReturnType<typeof useRootCreator>} */
    #createRoot;
    #env;
    /** @type {(window: Window) => void} */
    #registerWindow;
    /** @type {Window | null} */
    #openedWindow = null;
    /**
     * @type {{
     *  beforePopout?: Function;
     *  afterPopoutClosed?: Function;
     * }}
     */
    #hooks = {};
    /** @type {import("@odoo/owl").Root | undefined} */
    #root;

    /**
     * @param {any} id - An identifier for this popout instance
     * @param {Object} params
     * @param {(window: Window) => Promise<void>} params.addAssets
     * @param {ReturnType<typeof useRootCreator>} params.createRoot
     * @param {Object} params.env
     * @param {(window: Window) => void} params.registerWindow
     */
    constructor(id, { addAssets, createRoot, env, registerWindow }) {
        this.#id = id;
        this.#addAssets = addAssets;
        this.#createRoot = createRoot;
        this.#env = env;
        this.#registerWindow = registerWindow;
    }

    get id() {
        return this.#id;
    }

    /**
     * Gets the external window of this manager.
     *
     * @returns {Window|null} The external window or null if closed/doesn't exist
     */
    get externalWindow() {
        return this.#openedWindow && !this.#openedWindow.closed ? this.#openedWindow : null;
    }

    /**
     * Registers hooks for this popout instance.
     *
     * @param {Function} beforePopout - called before the external window is created.
     * @param {Function} afterPopoutClosed - called after the external window is closed.
     */
    addHooks(beforePopout = () => {}, afterPopoutClosed = () => {}) {
        this.#hooks = { beforePopout, afterPopoutClosed };
    }

    /**
     * Reset the external window to its initial state:
     * - Reset the external window header from main window (for appropriate title and other meta data)
     * - clear the external window's document body
     * - destroy the current root mounted on the window
     *
     * @param {Object} [options]
     * @param {Boolean} [options.useAlternativeAssets]
     * @returns {Promise<void>}
     */
    async reset({ useAlternativeAssets } = {}) {
        const doc = this.#openedWindow?.document;
        if (doc) {
            doc.head.textContent = "";
            if (useAlternativeAssets) {
                await this.#addAssets(this.#openedWindow);
            } else {
                doc.write(window.document.head.outerHTML);
            }
            doc.body = doc.createElement("body");
        }
        if (this.#root) {
            this.#root.destroy();
            this.#root = undefined;
        }
    }

    /**
     * Poll the external window to detect when it is closed.
     * The afterPopoutClosed hook is then called after the window is closed.
     */
    async #pollClosedWindow() {
        while (this.#openedWindow) {
            await new Promise((r) => setTimeout(r, POLL_CLOSE_WINDOW_TIMEOUT));
            if (this.#openedWindow?.closed) {
                this.#hooks.afterPopoutClosed?.();
                this.#openedWindow = null;
            }
        }
    }

    /**
     * Creates a picture-in-picture window and mounts the component.
     *
     * @param component - The component to be mounted.
     * @param {Object} param1
     * @param {Object} [param1.props] - The props of the component.
     * @param {Object} [param1.options]
     *      If only one of width or height is provided, the other is calculated based on the aspect ratio.
     *      If neither is provided, a default height of 240px (capped to the window height) is used.
     * @param {number} [param1.options.width] - The width of the popout window.
     * @param {number} [param1.options.height] - The height of the popout window.
     * @param {number} [param1.options.aspectRatio=16/9] - The aspect ratio of the popout window.
     * @param {boolean} [param1.options.useAlternativeAssets]
     * @returns {Promise<Window>} The external window. Rejects if the window could not be opened.
     */
    async pip(
        component,
        {
            props,
            options: { width, height, aspectRatio = 16 / 9, useAlternativeAssets = false } = {},
        } = {}
    ) {
        let externalWindow = this.#openedWindow;
        if (!externalWindow || externalWindow.closed) {
            this.#hooks.beforePopout?.();
            height = height || (width ? width / aspectRatio : Math.min(240, window.innerHeight));
            width = width || height * aspectRatio;
            if (window.documentPictureInPicture) {
                externalWindow = await window.documentPictureInPicture.requestWindow({
                    width,
                    height,
                });
            } else {
                externalWindow = window.open(
                    "about:blank",
                    "_blank",
                    `popup=yes,width=${width},height=${height}`
                );
            }
            this.#openedWindow = externalWindow;
            this.#pollClosedWindow();
        }
        await this.reset({ useAlternativeAssets });
        externalWindow.document.host = { ...externalWindow.document.host, id: this.#id };
        const rootEnv = Object.assign({}, this.#env, {
            /**
             * Some sub components may need a reference to the external window to
             * access window information such as its dimensions, or to attach event listeners.
             */
            pipWindow: externalWindow,
            rootId: this.#id,
        });
        this.#root = this.#createRoot(OverlayWrapper, {
            env: rootEnv,
            props: { component, componentProps: props },
        });
        this.#root.mount(externalWindow.document.body);
        this.#registerWindow(externalWindow);
        return externalWindow;
    }

    /**
     * Creates a popup window (if it does not exist yet) and mounts the component on it.
     *
     * @param component - The component to be mounted.
     * @param {Object} props - The props of the component.
     * @returns {Window|null} The external window
     */
    popout(component, props) {
        let externalWindow = this.#openedWindow;
        if (!externalWindow || externalWindow.closed) {
            this.#hooks.beforePopout?.();
            externalWindow = window.open("about:blank", "_blank", "popup=yes");
            if (!externalWindow) {
                // The browser can refuse to open the popup (e.g. popup blocker).
                this.#hooks.afterPopoutClosed?.();
                return null;
            }
            window.addEventListener("beforeunload", () => {
                if (externalWindow && !externalWindow.closed) {
                    externalWindow.close();
                }
            });
            this.#openedWindow = externalWindow;
            this.#pollClosedWindow();
        }
        this.reset();
        this.#root = this.#createRoot(component, { props });
        this.#root.mount(externalWindow.document.body);
        return externalWindow;
    }
}

/**
 * Mounts components on external windows (popups or picture-in-picture).
 *
 * The plugin itself acts as the default popout manager. Use `createManager` to
 * handle several external windows independently.
 */
export class MailPopoutPlugin extends Plugin {
    #env = useEnv();
    #hotkey = usePlugin(HotkeyPlugin);
    #createRoot = useRootCreator();
    /** @type {Map<any, PopoutManager>} */
    #managers = new Map();
    #defaultManager = this.createManager();

    /**
     * To be overridden to add specific assets to call PiP.
     *
     * @param {Window} _window the window on which we may add assets
     */
    async addAssets(_window) {}

    /**
     * Returns the popout manager of the given ID, creating it on first call.
     * This allows using multiple popout instances with different IDs. Calls
     * with the same ID share the same manager (and thus the same window).
     *
     * @param {any} [id] - An identifier for this popout instance
     * @returns {PopoutManager}
     */
    createManager(id = DEFAULT_ID) {
        let manager = this.#managers.get(id);
        if (!manager) {
            manager = new PopoutManager(id, {
                // late-bound so that patches of addAssets apply
                addAssets: (window) => this.addAssets(window),
                createRoot: this.#createRoot,
                env: this.#env,
                registerWindow: (window) => this.#hotkey.registerWindow(window),
            });
            this.#managers.set(id, manager);
        }
        return manager;
    }

    resetAll() {
        for (const manager of this.#managers.values()) {
            manager.reset();
        }
    }

    get id() {
        return this.#defaultManager.id;
    }

    /** @returns {Window|null} */
    get externalWindow() {
        return this.#defaultManager.externalWindow;
    }

    /** @see PopoutManager.addHooks */
    addHooks(beforePopout, afterPopoutClosed) {
        this.#defaultManager.addHooks(beforePopout, afterPopoutClosed);
    }

    /** @see PopoutManager.pip */
    pip(component, params) {
        return this.#defaultManager.pip(component, params);
    }

    /** @see PopoutManager.popout */
    popout(component, props) {
        return this.#defaultManager.popout(component, props);
    }

    /** @see PopoutManager.reset */
    reset(options) {
        return this.#defaultManager.reset(options);
    }
}

services.add(MailPopoutPlugin);
