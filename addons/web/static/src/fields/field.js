/** @odoo-module **/
import { evaluateExpr } from "@web/core/py_js/py";
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

    get effectiveFieldComponent() {
        return Field.getEffectiveFieldComponent(this.props.record, this.type, this.props.name);
    }

    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }

    evaluateExpressions(activeField, context) {
        activeField.modifiers = evaluateExpr(activeField.modifiersAttribute, context);
        activeField.options = evaluateExpr(activeField.optionsAttribute, context);
        if (activeField.decorationAttributes) {
            activeField.decorations = {};
            for (const decorationName in activeField.decorationAttributes) {
                activeField.decorations[decorationName] = evaluateExpr(
                    activeField.decorationAttributes[decorationName],
                    context
                );
            }
        }
    }

    get effectiveFieldComponentProps() {
        const record = this.props.record;
        const field = record.fields[this.props.name];
        const activeField = record.activeFields[this.props.name];

        // At this stage, plenty of data have been extracted from the field node,
        // but some need to be evaluated with the record.data context.
        this.evaluateExpressions(activeField, record.data);

        const readonyFromModifiers = activeField.modifiers.readonly == true;
        const readonlyFromViewMode = this.props.readonly;

        // currently unused
        //const invisible = activeField.modifiers.invisible === true;

        let value = this.props.record.data[this.props.name];
        if (value === undefined) {
            // FIXME: this is certainly wrong, should we set the default in the datapoint?
            value = field.default !== undefined ? field.default : null;
        }

        if (activeField.decorations) {
            this.props.decorations = activeField.decorations;
        }

        return {
            attrs: activeField.attrs || {},
            options: activeField.options || {},
            required: this.props.required || field.required || false,
            update: async (value) => {
                await record.update(this.props.name, value);
                // We save only if we're on view mode readonly and no readonly field modifier
                if (readonlyFromViewMode && !readonyFromModifiers) {
                    return record.save();
                }
            },
            value,
            ...this.props,
            type: field.type,
            readonly: readonlyFromViewMode || readonyFromModifiers || false,
        };
    }
}
Field.template = tags.xml/* xml */ `
    <t t-component="effectiveFieldComponent" t-props="effectiveFieldComponentProps" t-key="props.record.id"/>
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

Field.getEffectiveFieldComponent = function (record, type, fieldName) {
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

Field.forbiddenAttributeNames = {
    decorations: `You cannot use the "decorations" attribute name as it is used as generated prop name for the composite decoration-<something> attributes.`,
};
