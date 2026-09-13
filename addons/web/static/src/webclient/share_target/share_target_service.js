// @ts-check
/** @odoo-module native */

import { browser } from "@web/core/browser/browser";
import { AppEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
const SHARE_TARGET_ACK_TIMEOUT = 5000;

/** @param {AbortSignal} signal
 * @returns {Promise<File[] | null>} */
const getShareTargetDataFromServiceWorker = (signal) =>
    new Promise((resolve, reject) => {
        const { serviceWorker } = browser.navigator;
        if (!serviceWorker.controller || signal.aborted) {
            resolve(null);
            return;
        }
        const cleanup = () => {
            browser.clearTimeout(timeoutId);
            serviceWorker.removeEventListener("message", onmessage);
            signal.removeEventListener("abort", onAbort);
        };
        const onAbort = () => {
            cleanup();
            resolve(null);
        };
        const onmessage = (/** @type {MessageEvent} */ event) => {
            if (event.data?.action === "odoo_share_target_ack") {
                cleanup();
                resolve(
                    Array.isArray(event.data.shared_files)
                        ? event.data.shared_files
                        : null,
                );
            }
        };
        const timeoutId = browser.setTimeout(() => {
            cleanup();
            resolve(null);
        }, SHARE_TARGET_ACK_TIMEOUT);
        signal.addEventListener("abort", onAbort, { once: true });
        serviceWorker.addEventListener("message", onmessage);
        try {
            serviceWorker.controller.postMessage("odoo_share_target");
        } catch (error) {
            cleanup();
            reject(error);
        }
    });

const shareTargetRegistry = registry.category("share_target_apps");

shareTargetRegistry.addValidation((entry) => typeof entry === "string");

/**
 * @param {{ getApps: () => Record<string, any>[] }} menu
 * @returns {Record<string, any> | undefined}
 */
function findShareTargetApp(menu) {
    const apps = menu.getApps();
    for (const actionPath of shareTargetRegistry.getAll()) {
        const app = apps.find((app) => app.actionPath === actionPath);
        if (app) {
            return app;
        }
    }
}

class ShareTargetService {
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ menu: Object }} services
     */
    constructor(env, { menu }) {
        this.env = env;
        this.controller = new AbortController();
        this.menu = menu;
        /** @type {File[] | null} */
        this.sharedFiles = null;
        if (
            browser.navigator.serviceWorker &&
            new URL(browser.location.href).searchParams.get("share_target") ===
                "trigger"
        ) {
            const app = findShareTargetApp(/** @type {any} */ (menu));
            if (app) {
                env.bus.addEventListener(
                    AppEvent.WEB_CLIENT_READY,
                    () => this.receiveSharedFiles(app),
                    { once: true, signal: this.controller.signal },
                );
            }
        }
    }

    /** @param {any} app */
    async receiveSharedFiles(app) {
        try {
            this.sharedFiles = await getShareTargetDataFromServiceWorker(
                this.controller.signal,
            );
            if (!this.controller.signal.aborted && this.sharedFiles?.length) {
                await /** @type {any} */ (this.menu).selectMenu(app);
            }
        } catch (error) {
            console.warn("Failed to receive shared files", error);
        }
    }

    destroy() {
        this.controller.abort();
        this.sharedFiles = null;
    }

    /** @return {boolean} */
    hasSharedFiles() {
        return !!this.sharedFiles?.length;
    }

    /** @return {null|File[]} */
    getSharedFilesToUpload() {
        const files = this.sharedFiles;
        this.sharedFiles = null;
        return files;
    }
}

export const shareTargetService = {
    dependencies: ["menu"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ menu: Object }} services
     * @returns {ShareTargetService}
     */
    start(env, services) {
        return new ShareTargetService(env, services);
    },
};

registry.category("services").add("shareTarget", shareTargetService);
