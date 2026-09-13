// @ts-check
/** @odoo-module native */

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import {
    isBrowserSafari,
    isDisplayStandalone,
    isIOS,
    isMacOS,
} from "@web/core/browser/feature_detection";
import {
    isPlainObject,
    readJSONStorage,
    writeJSONStorage,
} from "@web/core/browser/storage_json";
import { makeLogger } from "@web/core/debug/debug_logger";
import { get } from "@web/core/network/http_service";
import { registry } from "@web/core/registry";

import { InstallPrompt } from "./install_prompt.js";

const serviceRegistry = registry.category("services");

const INSTALLATION_STATE_KEY = "pwaService.installationState";

const log = makeLogger("web.ui.pwa");

/** @type {Event | null} */
let pendingPrompt = null;
/** @type {Map<symbol, PwaService>} */
const activeServices = new Map();

browser.addEventListener("beforeinstallprompt", (ev) => {
    pendingPrompt = ev;
    log.lifecycle("prompt received", () => ({ services: activeServices.size }));
    for (const service of activeServices.values()) {
        service._handleBeforeInstallPrompt(ev, service._getInstallationState());
    }
});

export function _resetPwaInstallPrompt() {
    pendingPrompt = null;
    activeServices.clear();
}

class PwaService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ dialog: any }} services
     */
    constructor(env, { dialog }) {
        this.env = env;
        this._registration = Symbol();
        this.dialog = dialog;
        /** @type {any} */
        this._manifest = undefined;
        /** @type {Promise<any> | null} */
        this._manifestPromise = null;
        /** @type {any} */
        this.nativePrompt = undefined;

        this.canPromptToInstall = false;
        this.isAvailable = false;
        this.isScopedApp = browser.location.href.includes("/scoped_app");
        this.isSupportedOnBrowser = false;
        this.startUrl = "/odoo";
    }

    setup() {
        if (this.isScopedApp) {
            if (browser.location.pathname === "/scoped_app") {
                const path = new URL(browser.location.href).searchParams.get("path");
                this.startUrl = path ? `/${path}` : this.startUrl;
            } else {
                this.startUrl = browser.location.pathname;
            }
        }

        this.isSupportedOnBrowser =
            browser.BeforeInstallPromptEvent !== undefined ||
            (isBrowserSafari() &&
                !isDisplayStandalone() &&
                (isIOS() ||
                    (isMacOS() &&
                        Number(
                            browser.navigator.userAgent.match(/Version\/(\d+)/)?.[1],
                        ) >= 17)));

        const installationState = this._getInstallationState();

        if (this.isSupportedOnBrowser) {
            activeServices.set(this._registration, this);
            if (pendingPrompt) {
                this._handleBeforeInstallPrompt(pendingPrompt, installationState);
            }
            log.lifecycle("subscribe", () => ({ services: activeServices.size }));
            if (isBrowserSafari()) {
                this.canPromptToInstall = installationState !== "dismissed";
                this.isAvailable = true;
            }
        }
    }

    /** @returns {Record<string, string>} */
    _readState() {
        return readJSONStorage(INSTALLATION_STATE_KEY, {
            fallback: /** @type {Record<string, string>} */ ({}),
            validate: isPlainObject,
        });
    }

    /**
     * @param {string} [scope]
     * @returns {string}
     */
    _getInstallationState(scope = this.startUrl) {
        return this._readState()[scope] || "";
    }

    /** @param {string} value */
    _setInstallationState(value) {
        const ls = this._readState();
        ls[this.startUrl] = value;
        writeJSONStorage(INSTALLATION_STATE_KEY, ls);
    }

    _removeInstallationState() {
        const ls = this._readState();
        delete ls[this.startUrl];
        writeJSONStorage(INSTALLATION_STATE_KEY, ls);
    }

    /**
     * @param {Event} ev
     * @param {string} installationState
     */
    _handleBeforeInstallPrompt(ev, installationState) {
        this.nativePrompt = ev;
        if (installationState === "accepted") {
            if (!isDisplayStandalone()) {
                this._removeInstallationState();
            }
        }
        this.canPromptToInstall = installationState !== "dismissed";
        this.isAvailable = true;
    }

    /** @returns {Promise<Object>} */
    async getManifest() {
        if (this._manifest) {
            return this._manifest;
        }
        if (!this._manifestPromise) {
            const href = document
                .querySelector("link[rel=manifest]")
                ?.getAttribute("href");
            if (!href) {
                this._manifest = {};
                return this._manifest;
            }
            this._manifestPromise = get(href, "text", { rejectHtml: true })
                .then((/** @type {string} */ manifest) => {
                    this._manifest = JSON.parse(manifest);
                    return this._manifest;
                })
                .finally(() => {
                    this._manifestPromise = null;
                });
        }
        return this._manifestPromise;
    }

    /**
     * @param {string} scope
     * @returns {boolean}
     */
    hasScopeBeenInstalled(scope) {
        return this._getInstallationState(scope) === "accepted";
    }

    /** @param {{ onDone?: Function }} [options] */
    async show({ onDone } = {}) {
        if (!this.isAvailable) {
            return;
        }
        if (this.nativePrompt) {
            const prompt = this.nativePrompt;
            // A browser prompt belongs to the window and may be consumed only once,
            // even when several service instances expose an install action.
            if (pendingPrompt === prompt) {
                pendingPrompt = null;
            }
            for (const service of activeServices.values()) {
                if (service.nativePrompt === prompt) {
                    service.nativePrompt = null;
                    service.canPromptToInstall = false;
                    service.isAvailable = false;
                }
            }
            log.lifecycle("prompt consumed", () => ({ services: activeServices.size }));
            const res = await prompt.prompt();
            this._setInstallationState(res.outcome);
            await onDone?.(res);
        } else if (isBrowserSafari()) {
            this.dialog.add(
                InstallPrompt,
                {},
                {
                    onClose: async () => {
                        try {
                            await onDone?.({});
                        } finally {
                            this.decline();
                        }
                    },
                },
            );
        }
    }

    decline() {
        this._setInstallationState("dismissed");
        this.canPromptToInstall = false;
        for (const service of activeServices.values()) {
            if (service.startUrl === this.startUrl) {
                service.canPromptToInstall = false;
            }
        }
    }

    destroy() {
        activeServices.delete(this._registration);
        this.nativePrompt = null;
        this.canPromptToInstall = false;
        this.isAvailable = false;
        log.lifecycle("destroy", () => ({ services: activeServices.size }));
    }
}

export const pwaService = {
    dependencies: ["dialog"],
    async: ["getManifest", "show"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ dialog: any }} services
     * @returns {PwaService}
     */
    start(env, services) {
        const service = reactive(new PwaService(env, services));
        service.setup();
        return service;
    },
};

serviceRegistry.add("pwa", pwaService);
