import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";
import { onMounted } from "@odoo/owl";

export class BooleanRadio extends RadioField {
    static props = {
        ...RadioField.props,
        yes_label_element_id: { type: String },
        no_label_element_id: { type: String },
        first_element: { optional: true, type: Boolean },
    };

    static defaultProps = {
        ...RadioField.defaultProps,
        first_element: true,
    };

    setup() {
        super.setup(...arguments);
        onMounted(() => {
            this.updateLabels();
        });
    }

    updateLabels() {
        const trueLabel = document.getElementById(
            this.props.yes_label_element_id
        ).innerText;
        const falseLabel = document.getElementById(
            this.props.no_label_element_id
        ).innerText;
        document.getElementById(`${this.id}_true`).labels[0].textContent =
            trueLabel;
        document.getElementById(`${this.id}_false`).labels[0].textContent =
            falseLabel;
    }

    get items() {
        if (this.type === "boolean") {
            const items = [["true", ""], ["false", ""]];
            return this.props.first_element ? items : items.reverse();
        }
        return super.items;
    }

    get value() {
        if (this.type === "boolean")
            return this.props.record.data[this.props.name].toString();
        return super.items;
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        if (this.type === "boolean")
            this.props.record.update({
                [this.props.name]: value[0] === "true",
            });
        super.onChange();
    }
}

export const booleanRadio = {
    ...radioField,
    component: BooleanRadio,
    displayName: _t("Boolean display as radio field with translatable labels"),
    supportedOptions: [
        ...radioField.supportedOptions,
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
        {
            label: _t("First Element"),
            name: "first_element",
            type: "Boolean",
            help: _t("Defines which values comes first."),
        },
    ],
    supportedTypes: ["boolean"],
    extractProps({ options }, dynamicInfo) {
        return {
            ...radioField.extractProps(...arguments),
            readonly: dynamicInfo.readonly,
            yes_label_element_id: options.yes_label_element_id,
            no_label_element_id: options.no_label_element_id,
            first_element: options.first_element,
        };
    },
};

registry.category("fields").add("boolean_radio", booleanRadio);
