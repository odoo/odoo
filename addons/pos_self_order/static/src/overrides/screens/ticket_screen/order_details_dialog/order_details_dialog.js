import { patch } from "@web/core/utils/patch";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

patch(OrderDetailsDialog.prototype, {
    getTableInfo() {
        return super.getTableInfo() || this.props.order.self_ordering_table_id;
    },
});
