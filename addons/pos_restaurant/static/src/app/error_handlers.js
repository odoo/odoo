/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { urlToMessage } from "@point_of_sale/app/error_handlers/error_handlers";
import { _lt } from "@web/core/l10n/translation";

patch(urlToMessage, "pos_restaurant.urlToMessage", {
    "/web/dataset/call_kw/pos.order/get_table_draft_orders": _lt(
        "The orders for the table could not be loaded because you are offline"
    ),
    "/web/dataset/call_kw/pos.config/get_tables_order_count": _lt(
        "Couldn't synchronize the orders for the tables because you are offline"
    ),
});
