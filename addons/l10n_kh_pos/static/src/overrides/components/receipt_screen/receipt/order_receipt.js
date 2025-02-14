/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { OrderTable } from "@l10n_kh_pos/overrides/components/order_table/order_table";
import { OrderTableLine } from "@l10n_kh_pos/overrides/components/order_table_line/order_table_line";
import { patch } from "@web/core/utils/patch";

patch(OrderReceipt.components, {
    ...OrderReceipt.components,
    OrderTable,
    OrderTableLine
})
