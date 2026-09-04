import { TestEPos } from "@point_of_sale/backend/test_epos/test_epos";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/* global IminPrinter */
patch(TestEPos.prototype, {
    async onClick() {
        try {
            const iminPrinter = new IminPrinter();
            // Disable automatic reconnection during printer tests, as reconnect attempts
            // block execution until a connection is established.
            iminPrinter.reconnect = () => console.warn("Skipping iMin printer auto-reconnect.");
            await this.connectWithTimeout(iminPrinter);

            const printerStatus = await iminPrinter.getPrinterStatus();
            if (printerStatus.value !== 0) {
                throw new Error();
            }

            iminPrinter.printText("This is a test receipt");
            iminPrinter.printAndLineFeed();
            iminPrinter.printAndLineFeed();
            iminPrinter.printAndLineFeed();
            iminPrinter.partialCut();
            this.notification.add(_t("Successfully printed a test receipt on the iMin printer."), {
                type: "success",
            });
        } catch {
            await super.onClick(...arguments);
        }
    },

    connectWithTimeout(iminPrinter, timeoutMs = 1000) {
        return Promise.race([
            iminPrinter.connect(),
            new Promise((_, reject) =>
                setTimeout(
                    () => reject(new Error(`Connection timed out after ${timeoutMs} ms`)),
                    timeoutMs
                )
            ),
        ]);
    },
});
