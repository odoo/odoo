import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { formatFloat } from "@web/views/fields/formatters";
import { registry } from "@web/core/registry";
import { useRef, onPatched, onMounted, useState } from "@odoo/owl";

/**
 * This widget is used to display alongside the total quantity to consume of a production order,
 * the exact quantity that the worker should consume depending on the BoM. Ex:
 * 2 components to make 1 finished product.
 * The production order is created to make 5 finished product and the quantity producing is set to 3.
 * The widget will be '3.000 / 5.000'.
 */

export class MrpShouldConsumeOwl extends FloatField {
    static template = "mrp.ShouldConsume";
    setup() {
        super.setup();
        this.fields = this.props.record.fields;
        this.record = useState(this.props.record);
        this.displayShouldConsume = !["done", "draft", "cancel"].includes(this.record.data.state);
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

    get shouldConsumeQty() {
        return formatFloat(this.record.data.should_consume_qty, {
            ...this.fields.should_consume_qty,
            ...this.nodeOptions,
        });
    }
}

export const mrpShouldConsumeOwl = {
    ...floatField,
    component: MrpShouldConsumeOwl,
    displayName: "MRP Should Consume",
};

registry.category("fields").add("mrp_should_consume", mrpShouldConsumeOwl);
