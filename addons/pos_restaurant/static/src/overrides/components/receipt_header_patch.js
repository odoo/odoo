import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ReceiptHeader.prototype, {
    /** @returns {string} */
    get tableName() {
        if (this.props.data.table && this.props.data.customer_count) {
            return _t("Table %(number)s, Guests: %(count)s", {
                number: this.props.data.table,
                count: this.props.data.customer_count,
            });
        }
        if (this.props.data.table) {
            return _t("Table %(number)s", { number: this.props.data.table });
        }
        return "";
    },
});
