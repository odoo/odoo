/** @odoo-module */

import { registry } from "@web/core/registry";
import { FloatField } from '@web/views/fields/float/float_field';

const { useRef, useEffect } = owl;

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
        this.props.setDirty(true);
        return this.props.record.update({ manual_consumption: true });
    }
}

registry.category('fields').add('mrp_consumed', MrpConsumed);
