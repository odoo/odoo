import { useLayoutEffect } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { useComponent } from "@odoo/owl";

export function useBarcodeReader(callbackMap, exclusive = false) {
    const current = useComponent();
    const barcodeReader = useService("barcode_reader");
    if (barcodeReader) {
        for (const [key, callback] of Object.entries(callbackMap)) {
            callbackMap[key] = callback.bind(current);
        }
        useLayoutEffect(
            () => barcodeReader.register(callbackMap, exclusive),
            () => []
        );
    }
}
