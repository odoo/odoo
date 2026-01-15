import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { onMounted } from "@odoo/owl";

export class BooleanRadio extends RadioField {
    static props = {
        ...RadioField.props,
        yes_label_element_id: { type: String },
        no_label_element_id: { type: String },
    };
    setup() {
        super.setup(...arguments);
        onMounted(this.moveElement);
    }

    moveElement() {
        document.querySelectorAll("[data-value='true']")[0]
            .labels[0].textContent = document.getElementById(this.props.yes_label_element_id).innerText;
        document.querySelectorAll("[data-value='false']")[0]
            .labels[0].textContent = document.getElementById(this.props.no_label_element_id).innerText;
    }

    get items() {
        if (this.type === "boolean") return [["true", ""], ["false", ""]];
        return super.items;
    }

    get value() {
        if (this.type === "boolean") return this.props.record.data[this.props.name].toString();
        return super.items;
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        if (this.type === "boolean") this.props.record.update({ [this.props.name]: value[0] === "true" });
        super.onChange();
    }

}

export const booleanRadio = {
    ...radioField,
    component: BooleanRadio,
    displayName: _t("Boolean display as radio field with translatable labels"),
    supportedOptions: [
        {
            label: _t("True association"),
            name: "yes_label_element_id",
            type: "string",
            help: _t("Link an element with the boolean True value."),
        },
        {
            label: _t("False association"),
            name: "no_label_element_id",
            type: "string",
            help: _t("Link an element with the boolean False value."),
        },
    ],
    supportedTypes: ["boolean"],
    extractProps({ options }, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
            yes_label_element_id: options.yes_label_element_id,
            no_label_element_id: options.no_label_element_id,
        };
    },
};

registry.category("fields").add("boolean_radio", booleanRadio);
