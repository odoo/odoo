import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { FormActionFieldsOption } from "./form_action_fields_option";
import { FormModelRequiredFieldAlert } from "./form_model_required_field_alert";
import { getDependencyEl, getFieldName, getMultipleInputs, isFieldCustom } from "./utils";

export class FormFieldOption extends BaseOptionComponent {
    static template = "website.s_website_form_field_option";
    static props = {
        fetchModels: Function,
        loadFieldOptionData: Function,
        redrawSequence: { type: Number, optional: true },
    };
    static components = { FormActionFieldsOption, FormModelRequiredFieldAlert };

    setup() {
        super.setup();
        this.state = useState({
            availableFields: [],
            conditionInputs: [],
            conditionValueList: [],
            dependencyEl: null,
            valueList: null,
        });
        this.domState = useDomState((el) => {
            const modelName = el.closest("form")?.dataset.model_name;
            const fieldName = getFieldName(el);
            return {
                elDataset: { ...el.dataset },
                elClassList: [...el.classList],
                fieldName,
                modelName,
            };
        });

        this.domStateDependency = useDomState((el) => {
            const dependencyEl = getDependencyEl(el);
            if (!dependencyEl) {
                return {
                    type: "",
                    nodeName: "",
                    isRecordField: false,
                    isFormDate: false,
                    isFormDateTime: false,
                    hasDateTimePicker: false,
                };
            }

            return {
                type: dependencyEl.type,
                nodeName: dependencyEl.nodeName,
                isRecordField:
                    dependencyEl.closest(".s_website_form_field")?.dataset.type === "record",
                isFormDate: !!dependencyEl.closest(".s_website_form_date"),
                isFormDateTime: !!dependencyEl.closest(".s_website_form_datetime"),
                hasDateTimePicker: dependencyEl.classList.contains("datetimepicker-input"),
            };
        });
        onWillStart(async () => {
            const el = this.env.getEditingElement();
            const fieldOptionData = await this.props.loadFieldOptionData(el);
            this.state.availableFields.push(...fieldOptionData.availableFields);
            this.state.conditionInputs.push(...fieldOptionData.conditionInputs);
            this.state.valueList = fieldOptionData.valueList;
            this.state.conditionValueList.push(...fieldOptionData.conditionValueList);
        });
        onWillUpdateProps(async (props) => {
            const el = this.env.getEditingElement();
            const fieldOptionData = await props.loadFieldOptionData(el);
            this.state.availableFields.length = 0;
            this.state.availableFields.push(...fieldOptionData.availableFields);
            this.state.conditionInputs.length = 0;
            this.state.conditionInputs.push(...fieldOptionData.conditionInputs);
            this.state.valueList = fieldOptionData.valueList;
            this.state.conditionValueList.length = 0;
            this.state.conditionValueList.push(...fieldOptionData.conditionValueList);
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
