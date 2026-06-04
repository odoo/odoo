import { Component, signal, props } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class PropertySelectionField extends Component {
    static template = "web.PropertySelectionField";
    props = props({
        ...standardFieldProps,
        propertyName: String,
        propertyFieldName: String,
        propertyModelName: String,
    });

    selectionItems = signal([]);
    selectedValue = signal("");

    setup() {
        this.fieldService = useService("field");
        this.loadFieldInfo();
    }

    async loadFieldInfo() {
        const propertiesDef = await this.fieldService.loadPropertyDefinitions(
            this.propertyModelName,
            this.propertyFieldName
        );
        const propertyDef = propertiesDef[this.propertyName];
        if (propertyDef) {
            this.selectionItems.set(propertyDef.selection || []);
            this.selectedValue.set(this.props.record.data[this.props.name]);
        }
    }

    onValueChange(value) {
        this.selectedValue.set(value);
        this.props.record.update({ [this.props.name]: this.selectedValue() });
    }

    get propertyName() {
        return this.props.record.data[this.props.propertyName];
    }

    get propertyFieldName() {
        return this.props.record.data[this.props.propertyFieldName];
    }

    get propertyModelName() {
        return this.props.record.data[this.props.propertyModelName];
    }
}

export const propertyFieldField = {
    component: PropertySelectionField,
    supportedOptions: [
        {
            label: _t("Property Model Name"),
            name: "property_model_name",
            type: "string",
        },
        {
            label: _t("Property Field Name"),
            name: "property_field_name",
            type: "string",
        },
        {
            label: _t("Property Name"),
            name: "property_name",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ options }) => ({
        propertyFieldName: options.property_field_name,
        propertyName: options.property_name,
        propertyModelName: options.property_model_name,
    }),
};

registry.category("fields").add("property_selection", propertyFieldField);
