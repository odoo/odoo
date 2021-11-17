/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useEffect } from "@web/core/utils/hooks";

const { Component, tags } = owl;

const fieldRegistry = registry.category("fields");

export class Field extends Component {
    setup() {
        useEffect(() => {
            this.el.classList.add("o_field_widget");
            this.el.classList.add(`o_field_${this.type}`);
            this.el.setAttribute("name", this.props.name);
        });
    }

    get concreteFieldComponent() {
        return Field.getTangibleField(this.props.record, this.type, this.props.name);
    }
    get concreteFieldProps() {
        const field = this.props.record.fields[this.props.name];
        return {
            ...this.props,
            attrs: this.props.record.activeFields[this.props.name].attrs || {},
            options: this.props.record.activeFields[this.props.name].options || {},
            readonly: this.props.readonly || field.readonly || false,
            required: this.props.required || field.required || false,
            type: field.type,
            update: (value) => {
                return this.props.record.update(this.props.name, value);
            },
            value: this.props.record.data[this.props.name] || null,
        };
    }
    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }
}
Field.template = tags.xml/* xml */ `
    <t t-component="concreteFieldComponent" t-props="concreteFieldProps" t-key="props.record.id"/>
`;

class DefaultField extends Component {
    onChange(ev) {
        this.props.update(ev.target.value);
    }
}
DefaultField.template = tags.xml`
    <t>
        <span t-if="props.readonly" t-esc="props.value" />
        <input t-else="" class="o_input" t-att-value="props.value" t-att-id="props.id" t-on-change="onChange" />
    </t>
`;

Field.getTangibleField = function (record, type, fieldName) {
    if (record.viewMode) {
        const specificType = `${record.viewMode}.${type}`;
        if (fieldRegistry.contains(specificType)) {
            return fieldRegistry.get(specificType);
        }
    }
    if (!fieldRegistry.contains(type)) {
        const fields = record.fields;
        type = fields[fieldName].type;
    }
    // todo: remove fallback? yep
    return fieldRegistry.get(type, DefaultField);
};
