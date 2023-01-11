/** @odoo-module */

import { registry } from "@web/core/registry";
import { FloatField } from '@web/views/fields/float/float_field';

const { useRef, useEffect } = owl;

export class MrpConsumed extends FloatField {
    setup() {
        super.setup();
        const inputRef = useRef("numpadDecimal");
        const readonlyRef = useRef("readonly");

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

        useEffect(
            (readonlyEl) => {
                if (readonlyEl) {
                    if (this.props.record.data.manual_consumption) {
                        readonlyEl.parentElement.parentElement.classList.remove('o_non_manual_consumption');
                    } else {
                        readonlyEl.parentElement.parentElement.classList.add('o_non_manual_consumption');
                    }
                }
            },
            () => [readonlyRef.el]
        );
    }

    onInput(ev) {
        this.props.setDirty(true);
        return this.props.record.update({ manual_consumption: true });
    }
}
MrpConsumed.template = "mrp.Consumed";

registry.category('fields').add('mrp_consumed', MrpConsumed);
