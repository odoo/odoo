import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";
import { exprToBoolean } from "@web/core/utils/strings";

const DATETIME_FORMAT = "yyyy-MM-dd HH:mm:ss";
const TIME_FORMAT = "HH:mm";

export class SurveyTimeField extends Component {
    static props = standardFieldProps;
    static template = "survey.SurveyTimeField";

    setup() {
        useInputField({
            getValue: () => this.value,
        });
    }

    get value() {
        const value = this.props.record.data[this.props.name];

        if (luxon.DateTime.fromFormat(value, DATETIME_FORMAT).isValid) {
            return luxon.DateTime.fromFormat(value, DATETIME_FORMAT).toFormat(TIME_FORMAT);
        }
        return value || "";
    }
}

export const surveyTimeField = {
    component: SurveyTimeField,
    displayName: _t("Survey Time Field"),
    supportedTypes: ["char"],
};

registry.category("fields").add("survey_time", surveyTimeField);
