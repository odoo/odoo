import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { getDependencyEl, getMultipleInputs, isFieldCustom } from "./utils";

export class FormFieldOption extends BaseOptionComponent {
    static template = "html_builder.website.s_website_form_field_option";
    static props = {
        loadFieldOptionData: Function,
        redrawSequence: { type: Number, optional: true },
    };
    static components = { FormActionFieldsOption };

    setup() {
        super.setup();
        this.state = useState({
            availableFields: [],
            conditionInputs: [],
            conditionValueList: [],
            dependencyEl: null,
        });
        this.domState = useDomState((el) => ({ el }));
        onWillStart(async () => {
            const el = this.env.getEditingElement();
            const fieldOptionData = await this.props.loadFieldOptionData(el);
            this.state.availableFields.push(...fieldOptionData.availableFields);
            this.state.conditionInputs.push(...fieldOptionData.conditionInputs);
            this.state.conditionValueList.push(...fieldOptionData.conditionValueList);
            this.state.dependencyEl = getDependencyEl(el);
        });
        onWillUpdateProps(async (props) => {
            const el = this.env.getEditingElement();
            const fieldOptionData = await props.loadFieldOptionData(el);
            this.state.availableFields.length = 0;
            this.state.availableFields.push(...fieldOptionData.availableFields);
            this.state.conditionInputs.length = 0;
            this.state.conditionInputs.push(...fieldOptionData.conditionInputs);
            this.state.conditionValueList.length = 0;
            this.state.conditionValueList.push(...fieldOptionData.conditionValueList);
            this.state.dependencyEl = getDependencyEl(el);
        });
        // TODO select field's hack ?
    }
    get isTextConditionValueVisible() {
        const el = this.env.getEditingElement();
        const dependencyEl = getDependencyEl(el);
        if (
            !el.classList.contains("s_website_form_field_hidden_if") ||
            (dependencyEl &&
                (["checkbox", "radio"].includes(dependencyEl.type) ||
                    dependencyEl.nodeName === "SELECT"))
        ) {
            return false;
        }
        if (!dependencyEl) {
            return true;
        }
        if (dependencyEl?.classList.contains("datetimepicker-input")) {
            return false;
        }
        return (
            (["text", "email", "tel", "url", "search", "password", "number"].includes(
                dependencyEl.type
            ) ||
                dependencyEl.nodeName === "TEXTAREA") &&
            !["set", "!set"].includes(el.dataset.visibilityComparator)
        );
    }
    get isTextConditionOperatorVisible() {
        const el = this.env.getEditingElement();
        const dependencyEl = getDependencyEl(el);
        if (
            !el.classList.contains("s_website_form_field_hidden_if") ||
            dependencyEl?.classList.contains("datetimepicker-input")
        ) {
            return false;
        }
        return (
            !dependencyEl ||
            ["text", "email", "tel", "url", "search", "password"].includes(dependencyEl.type) ||
            dependencyEl.nodeName === "TEXTAREA"
        );
    }
    get isExisingFieldSelectType() {
        const el = this.env.getEditingElement();
        return !isFieldCustom(el) && ["selection", "many2one"].includes(el.dataset.type);
    }
    get isMultipleInputs() {
        const el = this.env.getEditingElement();
        return !!getMultipleInputs(el);
    }
    get isMaxFilesVisible() {
        // Do not display the option if only one file is supposed to be
        // uploaded in the field.
        const el = this.env.getEditingElement();
        const fieldEl = el.closest(".s_website_form_field");
        return (
            fieldEl.classList.contains("s_website_form_custom") ||
            ["one2many", "many2many"].includes(fieldEl.dataset.type)
        );
    }
}
