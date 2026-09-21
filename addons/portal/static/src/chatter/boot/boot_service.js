import { Deferred } from "@web/core/utils/concurrency";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

odoo.portalChatterReady = new Deferred();

const loader = {
    loadChatter: memoize(() => loadBundle("portal.assets_chatter")),
};

/**
 * Whether the element currently generates a layout box, i.e. neither it nor one
 * of its ancestors is `display: none`.
 *
 * @param {HTMLElement} el
 * @returns {boolean}
 */
function isRendered(el) {
    return el.getClientRects().length > 0;
}

export const portalChatterBootService = {
    start() {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (!chatterEl) {
            return;
        }
        if (isRendered(chatterEl)) {
            loader.loadChatter();
            return;
        }
        // Defer the boot until the container is actually laid out.
        const observer = new ResizeObserver(() => {
            if (isRendered(chatterEl)) {
                observer.disconnect();
                loader.loadChatter();
            }
        });
        observer.observe(chatterEl);
    },
};
registry.category("services").add("portal.chatter.boot", portalChatterBootService);
