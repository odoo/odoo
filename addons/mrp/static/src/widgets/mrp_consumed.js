/** @odoo-module */

import { registry } from "@web/core/registry";
import { FloatField, floatField } from '@web/views/fields/float/float_field';
import { useRef, useEffect } from "@odoo/owl";

export class MrpConsumed extends FloatField {
    setup() {
        super.setup();
        const inputRef = useRef("numpadDecimal");

        useEffect(
            (inputEl) => {
                if (inputEl) {
                    inputEl.addEventListener("input", this.onInput.bind(this));
                    return () => {
                        inputEl.removeEventListener("input", this.onInput.bind(this));
                    };
                }
            },
            () => [inputRef.el]
        );
    }

    onInput(ev) {
        return this.props.record.update({ manual_consumption: true, picked: true });
    }
}

export const mrpConsumed = {
    ...floatField,
    component: MrpConsumed,
};

registry.category('fields').add('mrp_consumed', mrpConsumed);
