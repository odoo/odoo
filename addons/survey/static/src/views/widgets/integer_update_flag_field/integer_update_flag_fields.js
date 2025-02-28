import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { integerField, IntegerField } from "@web/views/fields/integer/integer_field";

import { onWillStart, useEffect, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


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
    static props= {
        ...IntegerField.props,
        flagFieldName: { type: String },
        surveyId: { type: Number },
    }
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        const inputRef = useRef("numpadDecimal");
        const onChange = async () => {
            await this.props.record._update({
                [this.props.flagFieldName]: parseInt(this.formattedValue) !== this.referenceValue}
            );
        }
        useEffect(
            (inputEl) => {
                if (inputEl) {
                    inputEl.addEventListener("change", onChange);
                    return () => {
                        inputEl.removeEventListener("change", onChange);
                    };
                }
            },
            () => [inputRef.el]
        );
        this.orm = useService("orm");
        onWillStart(async () => {
            this.orm.searchRead(
                "survey.survey",
                [["id", "=", this.props.surveyId]],
                ["session_speed_rating_time_limit"]
            );
        });
    }
}

export const integerUpdateFlagField = {
    ...integerField,
    component: IntegerUpdateFlagField,
    displayName: _t("Integer updating comparison flag"),
    extractProps ({ attrs, options }, { context: { surveyId } }) {
        return {
            ...integerField.extractProps(...arguments),
            flagFieldName: options.flagFieldName,
            surveyId: surveyId,
        }
    }
};


registry.category("fields").add("integer_update_flag", integerUpdateFlagField)
