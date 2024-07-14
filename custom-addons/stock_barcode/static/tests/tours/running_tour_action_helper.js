/** @odoo-module **/

import { RunningTourActionHelper } from "@web_tour/tour_service/tour_utils";
import { patch } from "@web/core/utils/patch";

patch(RunningTourActionHelper.prototype, {
    scan(barcode) {
        odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger('barcode_scanned', { barcode });
    },
});
