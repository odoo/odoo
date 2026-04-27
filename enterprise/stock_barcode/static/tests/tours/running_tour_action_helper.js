/** @odoo-module **/

import { animationFrame } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { TourHelpers } from "@web_tour/tour_service/tour_helpers";

patch(TourHelpers.prototype, {
    async scan(barcode) {
        odoo.__WOWL_DEBUG__.root.env.services.barcode.bus.trigger("barcode_scanned", { barcode });
        await animationFrame();
    },

    /**
     * Simulate scan of RFID(s).
     * @param {String} data one or multiple RFID as a string. Use comma (,) to split the string into multi RFID
     */
    async scanRFID(rfid) {
        const params = { data: rfid.split(",") };
        odoo.__WOWL_DEBUG__.root.env.services.mobile.bus.trigger("mobile_reader_scanned", params);
        await animationFrame();
    },
});
