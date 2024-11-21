import { Deferred } from "@web/core/utils/concurrency";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

odoo.portalChatterReady = new Deferred();

const loader = {
    loadChatter: memoize(() => loadBundle("portal.assets_chatter")),
};
export const portalChatterBootService = {
    start() {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (chatterEl) {
            loader.loadChatter();
        }
    },
};
registry.category("services").add("portal.chatter.boot", portalChatterBootService);
