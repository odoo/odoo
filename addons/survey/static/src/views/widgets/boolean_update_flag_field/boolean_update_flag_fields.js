import { onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
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
        referenceValue: { type: Boolean, optional: true },
    }
    /**
     * @override
     */
    setup() {
        super.setup();
        this.referenceValue = this.props.referenceValue;
        this.orm = useService("orm");
        if (["survey.question", "survey_question"].includes(this.props.record.resModel)) {
            this.referenceValue = this.props.record?.evalContext?.parent?.session_speed_rating;
            if (this.referenceValue === undefined) {
                onWillStart(async () => {
                    const result = await this.orm.searchRead(
                        "survey.survey",
                        [["id", "=", this.props.record.data.survey_id[0]]],
                        ["session_speed_rating"]
                    );
                    this.referenceValue = result[0]["session_speed_rating"];
                });
            }
        }
    }
    /**
     * @override
     */
    async onChange(newValue) {
        super.onChange(...arguments);
        await this.props.record._update({
            [this.props.flagFieldName]: newValue !== this.referenceValue}
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
