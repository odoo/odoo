import { proxy, useEffect } from "@odoo/owl";
import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

export class CountedQuantityWidgetField extends FloatField {
    setup() {
        // Need to adapt useInputField to overide onInput and onChange
        super.setup();

        this.hasInput = proxy({ value: false });
        useEffect(() => {
            const inputEl = this.numpadDecimalRef();
            if (inputEl) {
                const boundOnInput = this.onInput.bind(this);
                const boundOnKeydown = this.onKeydown.bind(this);
                const boundOnBlur = this.onBlur.bind(this);
                inputEl.addEventListener("input", boundOnInput);
                inputEl.addEventListener("keydown", boundOnKeydown);
                inputEl.addEventListener("blur", boundOnBlur);
                return () => {
                    inputEl.removeEventListener("input", boundOnInput);
                    inputEl.removeEventListener("keydown", boundOnKeydown);
                    inputEl.removeEventListener("blur", boundOnBlur);
                };
            }
        });
    }

    updateValue(ev){
        try {
            const val = this.parse(ev.target.value);
            this.props.record.update({ [this.props.name]: val, inventory_quantity_set: true });
        } catch {} // ignore since it will be handled later
    }

    onInput(ev) {
        this.hasInput.value = true;
    }

    onBlur(ev) {
        if (this.hasInput.value) {
            this.updateValue(ev);
            this.hasInput.value = false;
        }
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
