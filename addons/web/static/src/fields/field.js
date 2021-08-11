/** @odoo-module **/
import { registry } from "@web/core/registry";
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
        // todo: remove fallback?
        return fieldRegistry.get(type, FieldChar);
    }

    setup() {
        const { record, type, name } = this.props;
        this.FieldComponent = Field.getTangibleField(record, type, name);
    }
}

Field.template = tags.xml/* xml */ `
    <div t-attf-id="{{ props.fieldId }}">
        <t t-component="FieldComponent" t-props="props" class="o-field" t-key="props.record.id"/>
    </div>`;
