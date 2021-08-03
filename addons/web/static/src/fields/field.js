/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FieldChar } from "./basic_fields";

const { Component } = owl;

const fieldRegistry = registry.category("fields");

export class Field extends Component {
    static template = owl.tags.xml`
    <div t-attf-id="{{ props.fieldId }}">
        <t t-component="FieldComponent" t-props="props" class="o-field" t-key="props.record.id"/>
    </div>`;

    static getTangibleField(record, type, fieldName) {
        console.log(arguments);
        console.trace();
        if (!fieldRegistry.contains(type)) {
            let fields = record.fields;
            type = fields[fieldName].type;
        }
        // todo: remove fallback?
        return fieldRegistry.get(type, FieldChar);
    }

    setup() {
        const { record, type, name } = this.props;
        this.FieldComponent = Field.getTangibleField(record, type, name);
    }
}
