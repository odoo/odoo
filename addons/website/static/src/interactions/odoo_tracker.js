import { registry } from "@web/core/registry";
import { rpc } from '@web/core/network/rpc';
import { Interaction } from "@web/public/interaction";

export const recordRE = /^([^(]+)\((\d+)/;

export class OdooTracker extends Interaction {
    static selector = "#wrapwrap";

    start() {
        const { trackingEnabled, mainObject } = document.documentElement.dataset;
        const matches = mainObject?.match(recordRE);
        if (trackingEnabled && matches) {
            rpc('/website/odoo_track', {
                res_model: matches[1],
                res_id: matches[2],
            });
        }
    }
}


registry.category("public.interactions").add("website.tracker", OdooTracker);
