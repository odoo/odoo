import { patch } from "@web/core/utils/patch";
import { BarcodeParser } from "@barcodes/js/barcode_parser";
import { _t } from "@web/core/l10n/translation";


patch(BarcodeParser, {
    async fetchNomenclature(orm, id) {
        return id;
    }
});
