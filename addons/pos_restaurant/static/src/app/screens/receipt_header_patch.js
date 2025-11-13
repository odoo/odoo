import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ReceiptHeader.prototype, {
    /** @returns {string} */
    get tableName() {
        const table = this.order.table_id || this.order.self_ordering_table_id;
        if (table && this.order.customer_count) {
            return _t("Table %(number)s, Guests: %(count)s", {
                number: table.table_number,
                count: this.order.customer_count,
            });
        }
        if (table) {
            return _t("Table %(number)s", { number: table.table_number });
        }
        return "";
    },
});
