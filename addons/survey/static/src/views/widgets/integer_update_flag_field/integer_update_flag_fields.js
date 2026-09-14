/** @odoo-module native */
import { useEffect, useRef } from "@odoo/owl";
import { ParseError } from "@web/core/parse_error";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { IntegerField, integerField } from "@web/fields/basic/integer/integer_field";

/**
 * Update a second field when the widget's own field `value` changes.
 *
 * The second field (boolean) will be set to `true` if the new `value` is
 * different from the reference value (passed in widget's `context` attribute)
 * and vice versa.
 * This is used over an onchange/compute to only enable this behavior when a
 * user directly changes the value from the client, and not as a result of
 * another onchange/compute.
 *
 * See also `BooleanUpdateFlagField`.
 */
export class IntegerUpdateFlagField extends IntegerField {
    static props = {
        ...IntegerField.props,
        flagFieldName: { type: String },
        referenceValue: { type: Number },
    };
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        const inputRef = useRef("numpadDecimal");
        const onChange = async (ev) => {
            let value;
            try {
                value = this.parse(ev.target.value);
            } catch (error) {
                if (error instanceof ParseError) {
                    return;
                }
                throw error;
            }
            await this.props.record.update({
                [this.props.flagFieldName]: value !== this.props.referenceValue,
            });
        };
        useEffect(
            (inputEl) => {
                if (inputEl) {
                    inputEl.addEventListener("change", onChange);
                    return () => {
                        inputEl.removeEventListener("change", onChange);
                    };
                }
            },
            () => [inputRef.el],
        );
    }
}

export const integerUpdateFlagField = {
    ...integerField,
    component: IntegerUpdateFlagField,
    displayName: _t("Integer updating comparison flag"),
    extractProps({ attrs, options }, { context: { referenceValue } }) {
        return {
            ...integerField.extractProps(...arguments),
            flagFieldName: options.flagFieldName,
            referenceValue: referenceValue,
        };
    },
};

registry.category("fields").add("integer_update_flag", integerUpdateFlagField);
