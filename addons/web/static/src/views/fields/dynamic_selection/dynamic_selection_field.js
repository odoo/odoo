import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DynamicSelectionField extends Component {
    static template = "web.DynamicSelectionField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ options: [] });

        onWillStart(async () => {
            await this.loadOptions();
        });
    }

    async loadOptions() {
        const modelName = this.props.record.data.crud_model_name;
        const fieldName = this.props.record.data.update_field_name;
        if (modelName && fieldName) {
            const fieldsInfo = await this.orm.call(modelName, "fields_get", [[fieldName]]);           
            if (fieldsInfo[fieldName] && fieldsInfo[fieldName].selection) {
                this.state.options = fieldsInfo[fieldName].selection;
            }
        }
    }

    get selectedLabel() {
        const currentValue = this.props.record.data[this.props.name];
        const option = this.state.options.find((opt) => opt[0] === currentValue);
        return option ? option[1] : currentValue || "";
    }

    onChange(ev) {
        const newValue = ev.target.value;
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export const dynamicSelectionField = {
    component: DynamicSelectionField,
    displayName: "Dynamic Selection Field",
    supportedTypes: ["char", "text"],
};

registry.category("fields").add("dynamic_selection_field", dynamicSelectionField);
