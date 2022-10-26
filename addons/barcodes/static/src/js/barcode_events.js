/** @odoo-module **/

/**
 * BarcodeEvents has been removed and replaced by the barcode service.
 * 
 * This file is a temporary service to remap barcode events from new barcode
 * service to core.bus (which was the purpose of BarcodeEvents).
 * 
 * @TODO: remove this as soon as all barcode code is using new barcode service
 */

import { registry } from "@web/core/registry";
import core from "web.core";

export const barcodeRemapperService = {
    dependencies: ["barcode"],
    start(env, { barcode }) {
        barcode.bus.addEventListener("barcode_scanned", ev => {
            const { barcode, target } = ev.detail;
            core.bus.trigger('barcode_scanned', barcode, target);
        });
    },
};
registry.category("services").add("barcode_remapper", barcodeRemapperService);
