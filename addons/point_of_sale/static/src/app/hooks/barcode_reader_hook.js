import { onWillDestroy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export function useBarcodeReader(callbackMap, exclusive = false) {
    const barcodeReader = useService("barcode_reader");
    if (barcodeReader) {
        onWillDestroy(barcodeReader.register(callbackMap, exclusive));
    }
}
