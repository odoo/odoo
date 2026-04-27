import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { scanBarcode } from "@web/core/barcode/barcode_dialog";

export class BarcodeScannerWidget extends CharField {
    static template = "product_barcodelookup.barcodeformbarcode";
    setup() {
        super.setup();
    }
    async onBarcodeBtnClick() {
        const barcode = await scanBarcode(this.env);
        if (barcode) {
            await this.props.record.update({
                barcode: barcode,
            });
        }
    }
}

export const barcodeScannerWidget = {
    ...charField,
    component: BarcodeScannerWidget,
};

registry.category("fields").add("productScanner", barcodeScannerWidget);
