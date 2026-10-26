import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class EventSponsorCard extends Interaction {
    static selector = ".o_wevent_sponsor_card";

    setup() {
        usePlugin(BootstrapInstance).getOrCreateInstance(window.Popover, this.el);
    }
}

registry
    .category("public.interactions")
    .add("website_event_exhibitor.event_sponsor_card", EventSponsorCard);
