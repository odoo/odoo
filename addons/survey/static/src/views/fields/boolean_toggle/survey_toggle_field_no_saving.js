/** @odoo-module **/
import { registry } from "@web/core/registry"
import { BooleanToggleField } from '@web/views/fields/boolean_toggle/boolean_toggle_field';

export class SurveyToggleFieldNoSaving extends BooleanToggleField {
    /**
    *override
    *In class BooleanToggleField , onChange {save : true} was set but we didn't want to save.
    *Hence, we changed save to false.
    */
    onChange(newValue) {
        this.props.record.update({ [this.props.name]: newValue });
    }
}

registry.category("fields").add("survey_toggle_no_saving", SurveyToggleFieldNoSaving);
