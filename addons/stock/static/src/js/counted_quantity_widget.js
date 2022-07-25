/** @odoo-module alias=stock.counted_quantity_widget **/

import { FloatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

export class CountedQuantityWidgetField extends FloatField{

    get formattedValue() {
        if (this.props.record.data.inventory_quantity_set) {
            return super.formattedValue;
        }
        return "";
    }

}

CountedQuantityWidgetField.displayName = _lt("Counted Quantity");

registry.category("fields").add('counted_quantity_widget', CountedQuantityWidgetField);
