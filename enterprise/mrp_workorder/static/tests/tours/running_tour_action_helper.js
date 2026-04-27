/** @odoo-module **/

import { animationFrame } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { TourHelpers } from "@web_tour/tour_service/tour_helpers";

patch(TourHelpers.prototype, {
    async scan(barcode) {
        odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
        await animationFrame();
    },
});
