/** @odoo-module native */
import { AssetsLoadingError, loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";

odoo.portalChatterReady = new Deferred();

const loader = {
    loadChatter: memoize(() => loadBundle("portal.assets_chatter")),
};
export const portalChatterBootService = {
    start() {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (chatterEl) {
            // Loading the bundle waits for deferred service registration, which
            // itself waits for this startup pass. Keep startup nonblocking.
            loader.loadChatter().catch((error) => {
                odoo.portalChatterReady.resolve(false);
                if (error instanceof AssetsLoadingError) {
                    return;
                }
                console.error("Portal chatter bundle failed to load", error);
            });
        } else {
            odoo.portalChatterReady.resolve(false);
        }
    },
};
registry.category("services").add("portal.chatter.boot", portalChatterBootService);
