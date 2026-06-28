import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(OrderDetailsDialog.prototype, {
    getOrderFields() {
        const order = this.props.order;
        const fields = super.getOrderFields();

        const sourceMap = {
            pos: _t("Point of Sale"),
            mobile: _t("Self-Order Mobile"),
            kiosk: _t("Self-Order Kiosk"),
        };

        const origin = fields.find((f) => f.id === "origin");
        if (origin) {
            Object.assign(origin, {
                value: sourceMap[order.source],
                condition: order.source in sourceMap,
            });
        }

        const table = order.getTable();
        const orderTimeIdx = fields.findIndex((f) => f.id === "order_time");
        fields.splice(
            orderTimeIdx + 1,
            0,
            {
                id: "table",
                label: _t("Table"),
                value: table ? table.floor_id.name + ", Table " + table.table_number : null,
                condition: !!table,
            },
            {
                id: "guests",
                label: _t("Guests"),
                value: order.getCustomerCount(),
                condition: !!order.getCustomerCount(),
            }
        );

        return fields;
    },
});
