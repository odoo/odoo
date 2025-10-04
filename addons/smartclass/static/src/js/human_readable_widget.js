import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useInputField } from "@web/views/fields/input_field_hook";
import { formatHumanReadable } from "./formatters";

export class HumanReadableWidget extends Component {
    static props = { ...standardFieldProps };
    static template = xml`<span t-esc="formattedValue" />`;

    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            refName: "human_readable",
        });
    }

    async updateValue() {
        if (!this.isDirty) {
            return;
        }
        const value = this.input.el.value;
        await this.props.record.update({ [this.props.name]: value });
    }

    get formattedValue() {
        return formatHumanReadable(this.value);
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
}
registry.category("fields").add("human_readable_widget", {
    component: HumanReadableWidget,
    supportedTypes: ["float"],
});
