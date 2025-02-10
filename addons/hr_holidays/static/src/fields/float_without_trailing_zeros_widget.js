import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";
import { onMounted } from "@odoo/owl";

const fieldRegistry = registry.category("fields");

class FloatWithoutTrailingZeros extends FloatField {
    static template = "hr_holidays.FloatWithoutTrailingZeros"

    setup() {
        super.setup()
        onMounted(async() => {
            this.input = document.getElementById(this.props.id)
            this.autoWidth(2)
        })
    }

    get formattedValue() {
        return super.formattedValue.replace(/\.*0+$/, '');
    }

    autoWidth(offset = 0){
        if (this.input) this.input.parentElement.style.width = Math.max(1, this.input.value.toString().length) + offset + "ch"
    }

    onFocusOut(){
        super.onFocusOut()
        this.autoWidth(2)
    }
}

const floatWithoutTrailingZeros = { ...floatField, component: FloatWithoutTrailingZeros };

fieldRegistry.add("float_without_trailing_zeros", floatWithoutTrailingZeros);
