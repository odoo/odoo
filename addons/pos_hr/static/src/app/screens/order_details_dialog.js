import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";
import { patch } from "@web/core/utils/patch";

patch(OrderDetailsDialog.prototype, {
    getOrderFields() {
        const order = this.props.order;
        const fields = super.getOrderFields();

        const servedBy = fields.find((f) => f.id === "served_by");
        if (servedBy) {
            Object.assign(servedBy, {
                value: order.employee_id?.name,
                condition: !!order.employee_id?.name,
            });
        }

        return fields;
    },
});
