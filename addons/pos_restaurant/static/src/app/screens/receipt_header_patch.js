import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ReceiptHeader.prototype, {
    /** @returns {string} */
    get tableName() {
        if (this.order.table_id && this.order.customer_count) {
            return _t("Table %(number)s, Guests: %(count)s", {
                number: this.order.table_id.table_number,
                count: this.order.customer_count,
            });
        }
        if (this.order.table_id) {
            return _t("Table %(number)s", { number: this.order.table_id.table_number });
        }
        return "";
    },
});
