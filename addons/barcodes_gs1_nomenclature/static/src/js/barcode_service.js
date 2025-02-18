import { session } from "@web/session";
import { patch } from "@web/core/utils/patch";
import { barcodeService } from '@barcodes/barcode_service';

import { FNC1_CHAR } from "@barcodes_gs1_nomenclature/js/barcode_parser";
import { decode, isValidEpcFormat } from "@barcodes_gs1_nomenclature/js/epc_utils";


patch(barcodeService, {
    // Use the regex given by the session, else use an impossible one
    gs1SeparatorRegex: new RegExp(session.gs1_group_separator_encodings || '.^', 'g'),

    cleanBarcode(barcode) {
        barcode = barcode.replace(barcodeService.gs1SeparatorRegex, FNC1_CHAR);
        return super.cleanBarcode(barcode);
    },

    handleBarcode(bus, barcode, target) {
        // Test if barcode is an RFID in hexa
        if (isValidEpcFormat(barcode)) {
            barcode = decode(barcode);
        }
        return super.handleBarcode(bus, barcode, target);
    }
});
