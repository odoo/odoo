import { useState } from "@odoo/owl";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { BooleanField, booleanField } from "@web/views/fields/boolean/boolean_field";

/**
 * Set if a choice based question accepts multiple answers or not
 */
class BooleanFieldMultipleChoice extends BooleanField {
    /**
     * override
     */
    setup() {
        this.state = useState({});
        useRecordObserver((record) => {
            this.state.value = record.data[this.props.name] === "multiple_choice" ? true : false;
        });
    }
    /**
     * override
     * @param {boolean} newValue
     */
    onChange(newValue) {
        this.state.value = newValue;
        this.props.record.update({
            [this.props.name]: newValue ? "multiple_choice" : "simple_choice",
        });
    }
}

const booleanFieldMultipleChoice = {
    ...booleanField,
    component: BooleanFieldMultipleChoice,
    displayName: _t("Simple or Multiple Choice Question"),
    supportedTypes: ["selection"], // as question_type is a selection field
};

registry.category("fields").add("multiple_choice_boolean", booleanFieldMultipleChoice);
