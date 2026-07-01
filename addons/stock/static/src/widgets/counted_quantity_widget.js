import { useListener } from "@odoo/owl";
import { useRef } from "@web/owl2/utils";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class CountedQuantityWidgetField extends FloatField {
    setup() {
        // Need to adapt useInputField to overide onInput and onChange
        super.setup();

        const inputRef = useRef("numpadDecimal");

        useListener(() => inputRef.el, "keydown", this.onKeydown.bind(this));
        useListener(() => inputRef.el, "blur", this.onBlur.bind(this));
    }

    updateValue(ev){
        try {
            const val = this.parse(ev.target.value);
            this.props.record.update({ [this.props.name]: val, inventory_quantity_set: true });
        } catch {} // ignore since it will be handled later
    }

    onBlur(ev) {
        this.updateValue(ev);
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "tab", "shift+tab"].includes(hotkey)) {
            this.updateValue(ev);
        }
    }

    get formattedValue() {
        if (
            this.props.readonly &&
            !this.props.record.data[this.props.name] & !this.props.record.data.inventory_quantity_set
        ) {
            return "";
        }
        return super.formattedValue;
    }
}

export const countedQuantityWidgetField = {
    ...floatField,
    component: CountedQuantityWidgetField,
};

registry.category("fields").add("counted_quantity_widget", countedQuantityWidgetField);
