import { useService } from "@web/core/utils/hooks";
import { useLayoutEffect } from "@web/owl2/utils";

export function useBarcodeReader(callbackMap, exclusive = false) {
    const barcodeReader = useService("barcode_reader");
    if (barcodeReader) {
        useLayoutEffect(
            () => barcodeReader.register(callbackMap, exclusive),
            () => []
        );
    }
}
