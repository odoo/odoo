import { patch } from "@web/core/utils/patch";
import { BarcodeParser } from "@barcodes/js/barcode_parser";

patch(BarcodeParser, {
    async fetchNomenclature(orm, id) {
        return id;
    },
});
