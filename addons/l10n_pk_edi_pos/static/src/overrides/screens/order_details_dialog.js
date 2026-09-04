import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(OrderDetailsDialog.prototype, {
    getOrderFields() {
        const order = this.props.order;
        const fields = super.getOrderFields();
        const status = order.getFbrStatusLabel();
        fields.push(
            {
                id: "l10n_pk_edi_pos_state",
                label: _t("FBR State"),
                value: status,
                condition: Boolean(status),
            },
            {
                id: "l10n_pk_edi_pos_invoice_number",
                label: _t("FBR Invoice Number"),
                value: order.l10n_pk_edi_pos_invoice_number,
                condition: Boolean(order.l10n_pk_edi_pos_invoice_number),
            }
        );
        return fields;
    },
});
