/** @odoo-module **/

import { FloatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

const { useEffect, useRef } = owl;

export class CountedQuantityWidgetField extends FloatField {
    setup() {
        // Need to adapt useInputField to overide onInput and onChange
        super.setup();

        const inputRef = useRef("numpadDecimal");

        useEffect(
            (inputEl) => {
                if (inputEl) {
                    inputEl.addEventListener("input", this.onInput.bind(this));
                    inputEl.addEventListener("keydown", this.onKeydown.bind(this));
                    return () => {
                        inputEl.removeEventListener("input", this.onInput.bind(this));
                        inputEl.removeEventListener("keydown", this.onKeydown.bind(this));
                    };
                }
            },
            () => [inputRef.el]
        );
    }

    onInput(ev) {
        this.props.setDirty(true);
        return this.props.record.update({ inventory_quantity_set: true });
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "tab", "shift+tab"].includes(hotkey)) {
            try {
                const val = this.parse(ev.target.value);
                this.props.update(val);
            } catch (_e) {
                // ignore since it will be handled later
            }
            this.onInput(ev);
        }
    }

    get formattedValue() {
        if (
            this.props.readonly &&
            !this.props.value & !this.props.record.data.inventory_quantity_set
        ) {
            return "";
        }
        return super.formattedValue;
    }
}

registry.category("fields").add("counted_quantity_widget", CountedQuantityWidgetField);
