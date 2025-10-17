import { Component, useEffect, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { getValueEditorInfo } from "@web/core/tree_editor/tree_editor_value_editors";
import { getOperatorEditorInfo } from "@web/core/tree_editor/tree_editor_operator_editor";
import { Select } from "@web/core/tree_editor/tree_editor_components";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MailSelect extends Select {
    static template = "mail.MailSelect";
}

function parseValue(fieldType, value) {
    if (fieldType !== "boolean" && !value) {
        return value;
    }
    switch (fieldType) {
        case "many2one":
        case "integer":
            return parseInt(value, 10);
        case "float":
        case "monetary":
            return parseFloat(value);
        case "boolean":
            if (value === "True") {
                return "set";
            }
            return "not set";
        default:
            return value;
    }
}

export class MailFieldSelectorValueField extends Component {
    static props = {
        ...standardFieldProps,
        resModel: { type: String, required: true },
        valueField: { type: String, required: true },
        acceptedTypes: { type: Array, of: String, optional: true },
    };
    static template = "mail.MailFieldSelectorValueField";
    setup() {
        this.fieldService = useService("field");
        this.state = useState({
            field: undefined,
            value: false,
            previousValueField: this.valueField,
        });
        this.loadField().then(() => {
            this.state.value =
                this.value !== undefined && this.state.field
                    ? parseValue(this.state.field.type, this.value)
                    : false;
        });
        useEffect(
            () => {
                if (this.state.previousValueField === this.valueField) {
                    return;
                }
                this.state.previousValueField = this.valueField;
                this.state.value = false;
                this.loadField().then(() => {
                    this.state.value = parseValue(this.state.field?.type, this.state.value);
                });
            },
            () => [this.valueField]
        );
    }

    async loadField() {
        if (!this.valueField) {
            return;
        }
        const fieldsInfo = await this.fieldService.loadFields(this.resModel, {
            fieldNames: [this.valueField],
        });
        this.state.field = fieldsInfo[this.valueField];
    }

    updateValue(value) {
        let valueRecord = value;
        if (this.state.field?.type === "boolean") {
            valueRecord = "set" === value ? true : false;
        }
        this.props.record.update({ [this.props.name]: valueRecord });
        this.state.value = value;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get unsupportedTypesMessage() {
        return _t("The field type is not supported for %s.", this.props.name);
    }

    get field() {
        if (!this.state.field) {
            return undefined;
        }
        let field;
        if (this.state.field.type === "boolean") {
            field = getOperatorEditorInfo(["set", "not set"], this.state.field);
        } else {
            field = getValueEditorInfo(this.state.field, "=");
        }
        if (field.component === Select) {
            field.component = MailSelect;
        }
        return field;
    }

    get fieldComponentProps() {
        const tmp = {
            ...this.field?.extractProps({
                value: this.state.field?.type === "boolean" ? [this.state.value] : this.state.value,
                update: this.updateValue.bind(this),
            }),
            ...(this.state.field?.type !== "many2one" ? { addBlankOption: true } : {}),
        };
        return tmp;
    }

    get acceptedType() {
        return (
            this.state.field &&
            (this.props.acceptedTypes.length === 0 ||
                this.props.acceptedTypes.includes(this.state.field.type))
        );
    }

    get resModel() {
        return this.props.record.data[this.props.resModel];
    }

    get valueField() {
        return this.props.record.data[this.props.valueField];
    }
}

export const mailFieldSelectorValueField = {
    component: MailFieldSelectorValueField,
    displayName: _t("Mail Field Selector Value"),
    supportedTypes: ["char"],
    supportedOptions: [
        {
            label: _t("Model"),
            name: "model",
            type: "string",
            required: true,
        },
        {
            label: _t("Value field"),
            name: "value",
            type: "string",
            required: true,
        },
        {
            label: _t("Accepted field types"),
            name: "accepted_types",
            type: "string[]",
        },
    ],
    extractProps({ options }) {
        return {
            resModel: options.model,
            valueField: options.value,
            acceptedTypes: options.accepted_types || [],
        };
    },
};

registry.category("fields").add("mail_field_selector_value", mailFieldSelectorValueField);
