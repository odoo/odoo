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
        surveyId: { type: Number },
    }

    setup() {
        super.setup();
        this.orm = useService("orm");

        onWillStart(async () => {
            this.referenceValue = await this.orm.searchRead(
                "survey.survey",
                [["id", "=", this.props.surveyId]],
                ["session_speed_rating"]
            );
        });
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
    extractProps ({ options }, { context: { surveyId } }) {
        return {
            flagFieldName: options.flagFieldName,
            surveyId: surveyId,
        }
    }
};

registry.category("fields").add("boolean_update_flag", booleanUpdateFlagField);
