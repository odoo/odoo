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
        if (!chatterEl) {
            return;
        }
        // Defer the boot until the container is laid out.
        const observer = new ResizeObserver(() => {
            if (chatterEl.getClientRects().length && this.canBoot()) {
                observer.disconnect();
                loader.loadChatter();
            }
        });
        observer.observe(chatterEl);
    },
    /**
     * Whether the chatter can be booted once its container is laid out.
     *
     * @returns {boolean}
     */
    canBoot() {
        return true;
    },
};
registry.category("services").add("portal.chatter.boot", portalChatterBootService);
