import { registry } from "@web/core/registry";
import { integerField, IntegerField } from "@web/views/fields/integer/integer_field";
import { onMounted } from "@odoo/owl";

const fieldRegistry = registry.category("fields");

class IntegerAutoWidth extends IntegerField {
    static template = "hr_holidays.IntegerAutoWidth"

    setup() {
        super.setup()
        onMounted(async() => {
            this.input = document.getElementById(this.props.id)
            this.autoWidth(2)
        })
    }

    autoWidth(offset = 0){
        if (this.input) this.input.parentElement.style.width = Math.max(1, this.input.value.toString().length) + offset + "ch"
    }

    onFocusOut(){
        super.onFocusOut()
        this.autoWidth(2)
    }
}

const integerAutoWidth = { ...integerField, component: IntegerAutoWidth };

fieldRegistry.add("integer_auto_width", integerAutoWidth);
