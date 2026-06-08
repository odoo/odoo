import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { ShareTargetDialog } from "@web/webclient/share_target/share_target_dialog";

export const shareTargetService = {
    dependencies: ["dialog"],
    /**
     * @return {Promise<File[]>}
     */
    async _getShareTargetFiles() {
        return new Promise((resolve) => {
            if (
                !(
                    browser.navigator.serviceWorker?.controller &&
                    new URL(browser.location).searchParams.get("share_target") === "trigger"
                )
            ) {
                return resolve([]);
            }
            const onmessage = (event) => {
                if (event.data.action === "odoo_share_target_ack") {
                    resolve(event.data.shared_files);
                    browser.navigator.serviceWorker.removeEventListener("message", onmessage);
                }
            };
            browser.navigator.serviceWorker.addEventListener("message", onmessage);
            browser.navigator.serviceWorker.controller.postMessage("odoo_share_target");
        });
    },

    _displayShareTarget(files, { dialog }) {
        if (files?.length) {
            dialog.add(ShareTargetDialog, {
                files: Array.from(files),
                close: () => {},
            });
        }
    },

    start(env, services) {
        const shareTargetItems = registry.category("share_target_items").getAll();
        const hasShareTargetItems = shareTargetItems.length;
        if (hasShareTargetItems) {
            env.bus.addEventListener(
                "WEB_CLIENT_READY",
                async () => {
                    const files = await shareTargetService._getShareTargetFiles();
                    shareTargetService._displayShareTarget(files, services);
                },
                { once: true }
            );
        }
        return {
            hasShareTargetItems,
            display: (files) => shareTargetService._displayShareTarget(files, services),
        };
    },
};

registry.category("services").add("share_target", shareTargetService);
