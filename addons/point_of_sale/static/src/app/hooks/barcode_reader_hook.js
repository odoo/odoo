import { useComponent, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
export function useBarcodeReader(callbackMap, exclusive = false) {
    const current = useComponent();
    const barcodeReader = useService("barcode_reader");
    if (barcodeReader) {
        for (const [key, callback] of Object.entries(callbackMap)) {
            callbackMap[key] = callback.bind(current);
        }
        useEffect(
            () => barcodeReader.register(callbackMap, exclusive),
            () => [],
        );
    }
}
