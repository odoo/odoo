/** @odoo-module **/

import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { barcodeService } from '@barcodes/barcode_service';

import { FNC1_CHAR } from "barcodes_gs1_nomenclature/static/src/js/barcode_parser.js";


patch(barcodeService, 'barcodes_gs1_nomenclature', {
    // Use the regex given by the session, else use an impossible one
    gs1SeparatorRegex: new RegExp(session.gs1_group_separator_encodings || '.^', 'g'),

    cleanBarcode: function(barcode) {
        barcode = barcode.replace(barcodeService.gs1SeparatorRegex, FNC1_CHAR);
        return this._super(barcode);
    },
});
