import { BarcodeDialog } from "@web/core/barcode/barcode_dialog";
import { BarcodeInput } from "./barcode_input";

export class ManualBarcodeScanner extends BarcodeDialog {
    static template = "barcodes.ManualBarcodeScanner";
    static components = {
        ...BarcodeDialog.components,
        BarcodeInput,
    };
    static props = [...BarcodeDialog.props, "placeholder?"];
}
