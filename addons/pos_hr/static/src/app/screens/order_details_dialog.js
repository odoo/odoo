import { patch } from "@web/core/utils/patch";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";
import { _t } from "@web/core/l10n/translation";

patch(OrderDetailsDialog.prototype, {
    getOrderFields() {
        const fields = super.getOrderFields();
        fields.find((f) => f.label === _t("Served By")).value = this.props.order.employee_id.name;
        return fields;
    },
});
