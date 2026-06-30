import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get changes() {
        const change = this.order_id.uiState.lineChanges[this.uuid];

        if (!change) {
            return {
                qty: this.qty,
                customer_note: this.customer_note,
                attribute_value_ids: JSON.stringify(
                    this.attribute_value_ids.map((a) => a.id).sort()
                ),
                custom_attribute_value_ids: JSON.stringify(
                    this.custom_attribute_value_ids.map((a) => a.id).sort()
                ),
            };
        }

        const diff = {
            qty: this.qty !== change.qty ? this.qty - change.qty : false,
            customer_note:
                this.customer_note !== change.customer_note ? change.customer_note : false,
            attribute_value_ids:
                JSON.stringify(this.attribute_value_ids.map((a) => a.id).sort()) !==
                change.attribute_value_ids
                    ? change.attribute_value_ids
                    : false,
            custom_attribute_value_ids:
                JSON.stringify(this.custom_attribute_value_ids.map((a) => a.id).sort()) !==
                change.custom_attribute_value_ids
                    ? change.custom_attribute_value_ids
                    : false,
        };
        return diff;
    },
    isLotTracked() {
        return false;
    },
    getDisplayPriceWithQty(qty) {
        const prices = this.order_id._constructPriceData({ baseLineOpts: { quantity: qty } })
            .baseLineByLineUuids[this.uuid].tax_details;

        if (this.config.iface_tax_included === "total") {
            return prices.total_included;
        } else {
            return prices.total_excluded;
        }
    },
});
