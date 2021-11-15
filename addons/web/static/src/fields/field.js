/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useEffect } from "@web/core/utils/hooks";

const { Component, tags } = owl;

const fieldRegistry = registry.category("fields");

class DefaultField extends Component {
    onChange(ev) {
        this.props.record.update(this.props.name, ev.target.value);
    }
}
DefaultField.template = tags.xml`
    <t>
        <span t-if="props.readonly" t-esc="props.value" />
        <input t-else="" class="o_input" t-on-change="onChange" t-att-value="props.value" />
    </t>
`;

export class Field extends Component {
    static getTangibleField(record, type, fieldName) {
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
    }

    get concreteFieldProps() {
        return {
            ...this.props,
            meta: this.fields[this.name],
            name: this.name,
            readonly: this.props.readonly || this.fields[this.name].readonly || false,
            required: this.fields[this.name].required || false,
            type: this.type,
            update: (value) => {
                return this.props.record.update(this.name, value);
            },
            value: this.props.record.data[this.name] || null,
        };
    }

    setup() {
        const { record, type, name } = this.props;
        this.fields = record.fields;
        this.name = name;
        // this.type = this.fields[name].type; // FIXME (why give it in props?)
        this.type = type || this.fields[name].type;
        this.FieldComponent = Field.getTangibleField(record, type, name);

        useEffect(() => {
            this.el.classList.add("o_field_widget");
            this.el.classList.add(`o_field_${this.type}`);
            this.el.setAttribute("name", this.name);
            this.el.setAttribute("id", this.props.fieldId);
        });
    }
}

Field.template = tags.xml/* xml */ `
    <t t-component="FieldComponent" t-props="concreteFieldProps" t-key="props.record.id"/>
`;
