import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";
import { patch } from "@web/core/utils/patch";

patch(OrderDetailsDialog.prototype, {
    getCustomerFields() {
        const fields = super.getCustomerFields();
        // A self-order customer who identified keeps their own contact as the order's
        // customer, the order is delivered to one of their addresses
        const address = this.props.order.delivery_partner_id;
        if (!address) {
            return fields;
        }
        const value = [address.street, address.zip && address.city, address.country_id?.name]
            .filter(Boolean)
            .join(", ");
        return fields.map((field) =>
            field.id === "address" ? { ...field, value, condition: !!value } : field
        );
    },
});
