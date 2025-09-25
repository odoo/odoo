import { registry } from "@web/core/registry";
import { FloatField, floatField } from '@web/views/fields/float/float_field';

export class MaxQtyToOrderField extends FloatField {
    get value() {
        if (this.props.record.selected && !this.props.record.data.qty_to_order_manual) {
            return this.props.record.data.qty_to_order_to_max
        } else {
            return super.value;
        }
    }
}

export const maxQtyToOrderField = {
    ...floatField,
    component: MaxQtyToOrderField,
}

registry.category("fields").add("stock.max_qty_to_order", maxQtyToOrderField);
