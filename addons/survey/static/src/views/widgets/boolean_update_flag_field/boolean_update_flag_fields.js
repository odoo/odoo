import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { booleanField, BooleanField } from "@web/views/fields/boolean/boolean_field";


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
 * See also `IntegerUpdateFlagField`.
 */
export class BooleanUpdateFlagField extends BooleanField {
    static props= {
        ...BooleanField.props,
        flagFieldName: { type: String },
        referenceValue: { type: Boolean },
    }
    /**
     * @override
     */
    async onChange(newValue) {
        super.onChange(...arguments);
        await this.props.record._update({
            [this.props.flagFieldName]: newValue !== this.props.referenceValue}
        );
    }
}

export const booleanUpdateFlagField = {
    ...booleanField,
    component: BooleanUpdateFlagField,
    displayName: _t("Checkbox updating comparison flag"),
    extractProps ({ options }, { context: { referenceValue } }) {
        return {
            flagFieldName: options.flagFieldName,
            referenceValue: referenceValue,
        }
    }
};

registry.category("fields").add("boolean_update_flag", booleanUpdateFlagField);
