import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";

patch(PosOrder.prototype, {
    useBlackBoxSweden() {
        return !!this.config.iface_sweden_fiscal_data_module;
    },
    get_specific_tax(amount) {
        const tax = this.get_tax_details().find((tax) => tax.tax.amount === amount);

        if (tax) {
            return tax.amount;
        }

        return false;
    },
    wait_for_push_order() {
        var result = super.wait_for_push_order(...arguments);
        result = Boolean(this.useBlackBoxSweden() || result);
        return result;
    },
    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing(...arguments);
        if (!this.useBlackBoxSweden()) {
            return result;
        }

        const order = this;
        result.useBlackBoxSweden = true;
        result.blackboxSeData = {
            posID: this.config.name,
            orderSequence: order.sequence_number,
            unitID: order.sweden_blackbox_unit_id,
            blackboxSignature: order.sweden_blackbox_signature,
            isReprint: order.isReprint,
            originalOrderDate: deserializeDateTime(order.creation_date).toFormat(
                "HH:mm dd/MM/yyyy"
            ),
            productLines: order.lines.filter((orderline) => {
                return orderline.product_type !== "service";
            }),
            serviceLines: order.lines.filter((orderline) => {
                return orderline.product_type === "service";
            }),
        };
        return result;
    },
});
