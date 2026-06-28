import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";

/**
 * This class is a JS copy of the class PosOrderReceipt in Python.
 */
patch(GeneratePrinterData.prototype, {
    get commonExtraData() {
        const extraData = super.commonExtraData;
        if (this.config.module_pos_restaurant) {
            const table = this.order.table_id;
            extraData.table_name = table?.table_number || false;
            extraData.order_label = table
                ? _t("T %s", table.table_number)
                : this.order.floating_order_name || false;
            extraData.floor_name = table?.floor_id?.name || false;
        }
        return extraData;
    },
});
