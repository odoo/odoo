import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

patch(OrderDetailsDialog.prototype, {
    setup() {
        super.setup();
        Object.assign(this.sources, {
            mobile: _t("Self-Order Mobile"),
            kiosk: _t("Self-Order Kiosk"),
        });
    },
    getOrderFields() {
        const table = this.props.order.getTable();
        return [
            ...super.getOrderFields(),
            {
                label: _t("Table"),
                value: table ? `${table.floor_id.name}, Table ${table.table_number}` : "",
            },
            { label: _t("Guests"), value: this.props.order.getCustomerCount() },
        ];
    },
});
