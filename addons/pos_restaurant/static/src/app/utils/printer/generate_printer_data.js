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
<<<<<<< 6fd9d2bb434bf96f19d2444d3e6a118df9e879ec
            extraData.table_name = table?.table_number || false;
            extraData.order_label = table
                ? _t("T %s", table.table_number)
                : this.order.floating_order_name || false;
||||||| 892efe11ffd04e2c9af8ab5baf2d1917970cf1c7
            extraData.table_number = table?.table_number || false;
=======
            extraData.table_name = table?.table_number || false;
>>>>>>> 1c19dc637ec68b359f204dd10f87e7e5b5117b53
            extraData.floor_name = table?.floor_id?.name || false;
        }
        return extraData;
    },
<<<<<<< 6fd9d2bb434bf96f19d2444d3e6a118df9e879ec
||||||| 892efe11ffd04e2c9af8ab5baf2d1917970cf1c7
    generatePreparationData() {
        const receipts = super.generatePreparationData(...arguments);
        for (const receipt of receipts) {
            if (receipt.extra_data.table_number) {
                receipt.extra_data.order_label = false;
            }
        }
        return receipts;
    },
=======
    generatePreparationData() {
        const receipts = super.generatePreparationData(...arguments);
        for (const receipt of receipts) {
            if (receipt.extra_data.table_name) {
                receipt.extra_data.order_label = false;
            }
        }
        return receipts;
    },
>>>>>>> 1c19dc637ec68b359f204dd10f87e7e5b5117b53
});
