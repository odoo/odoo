/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { deserializeDate, formatDate } from "@web/core/l10n/dates";

patch(OrderReceipt.prototype, {
    formatLocalizedDate(date) {
        return formatDate(deserializeDate(date));
    },
})
