/** @odoo-module **/

import { FloatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";

/**
 * This widget is used to display alongside the total quantity to consume of a production order,
 * the exact quantity that the worker should consume depending on the BoM. Ex:
 * 2 components to make 1 finished product.
 * The production order is created to make 5 finished product and the quantity producing is set to 3.
 * The widget will be '3.000 / 5.000'.
 */

const { useRef, onPatched, onMounted } = owl;
export class MrpShouldConsumeOwl extends FloatField {
    setup() {
        super.setup();
        const { data, fields } = this.props.record;
        this.shouldConsumeQty = formatFloat(data.should_consume_qty, {
            ...fields.should_consume_qty,
            ...this.nodeOptions,
        });
        this.displayShouldConsume = !["done", "draft", "cancel"].includes(data.state);
        this.inputSpanRef = useRef("numpadDecimal");
        onMounted(this._renderPrefix);
        onPatched(this._renderPrefix);
    }

    _renderPrefix() {
        if (this.displayShouldConsume && this.inputSpanRef.el) {
            this.inputSpanRef.el.classList.add(
                "o_quick_editable",
                "o_field_widget",
                "o_field_number",
                "o_field_float"
            );
        }
    }
}

MrpShouldConsumeOwl.template = "mrp.ShouldConsume";
MrpShouldConsumeOwl.displayName = "MRP Should Consume";

registry.category("fields").add("mrp_should_consume", MrpShouldConsumeOwl);
