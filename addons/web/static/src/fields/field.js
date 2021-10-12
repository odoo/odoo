/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useEffect } from "@web/core/utils/hooks";
import { FieldChar } from "./basic_fields";

const { Component, tags } = owl;

const fieldRegistry = registry.category("fields");

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
        return fieldRegistry.get(type, FieldChar);
    }

    get concreteFieldProps() {
        return {
            value: this.props.record.data[this.name],
            readonly: this.fields[this.name].readonly,
            name: this.name,
            record: this.props.record,
        };
    }

    setup() {
        const { record, type, name } = this.props;
        this.fields = record.fields;
        this.name = name;
        // this.type = this.fields[name].type; // FIXME (why give it in props?)
        this.type = type;
        this.FieldComponent = Field.getTangibleField(record, type, name);

        useEffect(() => {
            this.el.classList.add("o_field_widget");
            this.el.classList.add(`o_field_${this.type}`);
            this.el.setAttribute("name", this.name);
        });
    }
}

Field.template = tags.xml/* xml */ `
    <div t-attf-id="{{ props.fieldId }}">
        <t t-component="FieldComponent" t-props="concreteFieldProps" t-key="props.record.id"/>
    </div>`;
