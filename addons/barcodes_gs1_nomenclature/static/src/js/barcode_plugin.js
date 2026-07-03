import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { BarcodePlugin } from '@barcodes/barcode_plugin';

import { FNC1_CHAR } from "@barcodes_gs1_nomenclature/js/barcode_parser";


patch(BarcodePlugin, {
    // Use the regex given by the session, else use an impossible one
    gs1SeparatorRegex: new RegExp(session.gs1_group_separator_encodings || '.^', 'g'),

    cleanBarcode(barcode) {
        barcode = barcode.replace(this.gs1SeparatorRegex, FNC1_CHAR);
        return super.cleanBarcode(barcode);
    },
});
