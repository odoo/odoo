import { _t } from "@web/core/l10n/translation";
import { TestEPos } from "@point_of_sale/backend/test_epos/test_epos";
import { patch } from "@web/core/utils/patch";

/* global IminPrinter */
patch(TestEPos.prototype, {
    async getPrinterDataImin(printer_id) {
        if (printer_id) {
            const response = await this.orm.read(
                "pos.printer",
                [printer_id],
                ["name", "printer_type"]
            );
            return response[0];
        } else {
            const data = this.props.record.data;
            return {
                id: this.props.record.resId || null,
                name: data.name,
                printer_type: data.printer_type,
            };
        }
    },

    async _printTo(printer_id = null) {
        const printer = await this.getPrinterDataImin(printer_id);
        if (printer.printer_type !== "imin") {
            return super._printTo(...arguments);
        }
        try {
            const iminPrinter = new IminPrinter();
            await iminPrinter.connect();
            const printerStatus = await iminPrinter.getPrinterStatus();
            if (printerStatus.value !== 0) {
                throw new Error();
            }
            iminPrinter.printText(`Test print for printer ${printer.name}`);
            iminPrinter.printAndLineFeed();
            iminPrinter.printAndLineFeed();
            iminPrinter.printAndLineFeed();
            iminPrinter.partialCut();
        } catch {
            this.notification.add(`${printer.name}: ${_t("Cannot reach the iMin printer.")}`, {
                type: "danger",
            });
        }
    },
});
