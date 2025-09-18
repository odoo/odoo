// @ts-check

/** @module @web/webclient/share_target/share_target_service - Service receiving shared files from the PWA service worker (Web Share Target API) */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
/**
 * Request shared file data from the PWA service worker via postMessage.
 * Resolves once the worker responds with `odoo_share_target_ack`.
 * @returns {Promise<File[]>}
 */
const getShareTargetDataFromServiceWorker = () =>
    new Promise((resolve) => {
        const onmessage = (event) => {
            if (event.data.action === "odoo_share_target_ack") {
                resolve(event.data.shared_files);
                browser.navigator.serviceWorker.removeEventListener(
                    "message",
                    onmessage,
                );
            }
        };
        browser.navigator.serviceWorker.addEventListener("message", onmessage);
        browser.navigator.serviceWorker.controller.postMessage("odoo_share_target");
    });

export const shareTargetService = {
    dependencies: ["menu"],
    /**
     * If the page was opened via the Web Share Target API, listen for the
     * WEB_CLIENT_READY event, fetch shared files from the service worker,
     * and navigate to the expenses app.
     * @param {Object} env - Odoo environment
     * @param {{ menu: Object }} services - injected service dependencies
     * @returns {{ hasSharedFiles: () => boolean, getSharedFilesToUpload: () => File[] | null }}
     */
    start(env, { menu }) {
        let sharedFiles = null;
        if (
            browser.navigator.serviceWorker &&
            new URL(browser.location).searchParams.get("share_target") === "trigger"
        ) {
            const app = menu.getApps().find((app) => "expenses" === app.actionPath);
            if (app) {
                const clientReadyListener = async () => {
                    sharedFiles = await getShareTargetDataFromServiceWorker();
                    if (sharedFiles?.length) {
                        await menu.selectMenu(app);
                    }
                    env.bus.removeEventListener(
                        "WEB_CLIENT_READY",
                        clientReadyListener,
                    );
                };
                env.bus.addEventListener("WEB_CLIENT_READY", clientReadyListener);
            }
        }
        return {
            /**
             * Return true if we receive share target files from service worker
             * @return {boolean}
             */
            hasSharedFiles: () => !!sharedFiles?.length,
            /**
             * Return the shared files retrieve for upload
             * @return {null|File[]}
             */
            getSharedFilesToUpload: () => {
                const files = sharedFiles;
                sharedFiles = null;
                return files;
            },
        };
    },
};

registry.category("services").add("shareTarget", shareTargetService);
