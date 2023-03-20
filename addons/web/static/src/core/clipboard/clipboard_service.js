/** @odoo-module **/

import { registry } from "../registry";
import { browser } from "@web/core/browser/browser";

/**
 *  @typedef {{
 *      writeText(
 *          String: text,
 *          options?: ...       TODO
 *      ): () => void;
 *  }}
 */

export const clipboardService = {

    /** @returns {void} */
    start(env) {

        function writeText(text, options = {}) {
            setTimeout(async () => { // Use a timeout for the Safari write to clipboard to work
                try {
                    await browser.navigator.clipboard.writeText(text);
                    env.services.notification.add(env._t("Link copied to clipboard."), {type: "success"});
                    if (options.onSuccess) {
                        options.onSuccess();
                    }
                } catch (error) {
                    env.services.notification.add(env._t("Error copying to clipboard."), {type: "danger"});
                    console.error('Error copying to clipboard:', error);
                    if (options.onError) {
                        options.onError();
                    }
                }
            });
        }

        return { writeText };
    },
};

registry.category("services").add("clipboard", clipboardService);
