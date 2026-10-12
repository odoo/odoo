import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";

odoo.portalChatterReady = Promise.withResolvers();

const loadChatter = memoize(() => loadBundle("portal.assets_chatter"));

export class PortalChatterBoot extends Interaction {
    static selector = ".o_portal_chatter";

    start() {
        // Defer the boot until the container is laid out.
        const observer = new ResizeObserver(() => {
            if (this.el.getClientRects().length) {
                observer.disconnect();
                this.boot();
            }
        });
        observer.observe(this.el);
        this.registerCleanup(() => observer.disconnect());
    }

    boot() {
        const root = document.createElement("div");
        root.setAttribute("id", "chatterRoot");
        this.el.appendChild(root);
        loadChatter();
    }
}

registry.category("public.interactions").add("portal.chatter.boot", PortalChatterBoot);
