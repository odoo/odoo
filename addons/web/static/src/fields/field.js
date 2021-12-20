/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { isBroadlyFalsy } from "@web/core/utils/misc";
import { snakeToCamel } from "@web/core/utils/strings";
import { isAttr } from "@web/core/utils/xml";
import { getX2MViewModes, X2M_TYPES } from "@web/views/helpers/view_utils";

const { Component, tags } = owl;

const fieldRegistry = registry.category("fields");
const viewRegistry = registry.category("views");

export class Field extends Component {
    // AAB: no need to pre-optimize anything, but as it stands, this method is called
    // twice at each patch for "required" and twice for "readonly"
    evalModifier(modifier) {
        const activeField = this.props.record.activeFields[this.props.name];
        let modifierValue = activeField.modifiers[modifier];
        if (Array.isArray(modifierValue)) {
            modifierValue = new Domain(modifierValue).contains(this.props.record.evalContext);
        }
        return !!modifierValue;
    }

    get classNames() {
        const classNames = {
            o_field_widget: true,
            o_readonly_modifier: this.evalModifier("readonly"),
            o_required_modifier: this.evalModifier("required"),
            [`o_field_${this.type}`]: true,
        };

        // generate field decorations classNames (only if field-specific decorations
        // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
        const { decorations } = this.props.record.activeFields[this.props.name];
        const getClassFromDecoration =
            this.effectiveFieldComponent.getClassFromDecoration || ((d) => `text-${d}`);
        const evalContext = this.props.record.evalContext;
        for (const decoName in decorations) {
            const value = evaluateExpr(decorations[decoName], evalContext);
            classNames[getClassFromDecoration(decoName)] = value;
        }

        return classNames;
    }

    get effectiveFieldComponent() {
        return Field.getEffectiveFieldComponent(this.props.record, this.type, this.props.name);
    }

    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }

    get effectiveFieldComponentProps() {
        const record = this.props.record;
        const field = record.fields[this.props.name];
        const activeField = record.activeFields[this.props.name];

        const readonlyFromModifiers = this.evalModifier("readonly");
        const readonlyFromViewMode = this.props.readonly;

        return {
            attrs: activeField.attrs || {},
            options: activeField.options || {},
            required: this.evalModifier("required"), // AAB: does the field really need this?
            update: async (value, options = { name: null }) => {
                await record.update(options.name || this.props.name, value);
                // We save only if we're on view mode readonly and no readonly field modifier
                if (readonlyFromViewMode && !readonlyFromModifiers) {
                    return record.save();
                }
            },
            value: this.props.record.data[this.props.name],
            formatValue: this.formatValue.bind(this),
            parseValue: this.parseValue.bind(this),
            ...this.props,
            type: field.type,
            readonly: readonlyFromViewMode || readonlyFromModifiers || false,
        };
    }

    formatValue(value) {
        const record = this.props.record;
        const field = record.fields[this.props.name];
        const activeField = record.activeFields[this.props.name];

        // GES
        // Is this the right place ? Or should we delegate that to the fields anyway.
        // The option exists at least on integer field. To see if it use at many places.
        if ("format" in activeField.options && isBroadlyFalsy(activeField.options.format)) {
            return value;
        }

        const formatterRegistry = registry.category("formatters");
        if (formatterRegistry.contains(activeField.widget)) {
            return formatterRegistry.get(activeField.widget)(value, { field });
        } else if (formatterRegistry.contains(field.type)) {
            return formatterRegistry.get(field.type)(value, { field });
        } else {
            console.warn(`No formatter found for ${field.type} field. It should be implemented.`);
            return String(value);
        }
    }

    parseValue(value) {
        const record = this.props.record;
        const field = record.fields[this.props.name];
        const activeField = record.activeFields[this.props.name];

        const parserRegistry = registry.category("parsers");
        if (parserRegistry.contains(activeField.widget)) {
            return parserRegistry.get(activeField.widget)(value);
        } else if (parserRegistry.contains(field.type)) {
            return parserRegistry.get(field.type)(value);
        } else {
            console.warn(`No parser found for ${field.type} field. It should be implemented.`);
            return value;
        }
    }
}
Field.template = tags.xml/* xml */ `
    <div t-att-name="props.name" t-att-class="classNames">
        <t t-component="effectiveFieldComponent" t-props="effectiveFieldComponentProps" t-key="props.record.id"/>
    </div>`;

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

Field.parseFieldNode = function (node, fields, viewType) {
    const name = node.getAttribute("name");
    const widget = node.getAttribute("widget");
    const field = fields[name];
    const fieldInfo = {
        name,
        string: node.getAttribute("string") || field.string,
        widget,
        options: evaluateExpr(node.getAttribute("options") || "{}"),
        modifiers: JSON.parse(node.getAttribute("modifiers") || "{}"),
        onChange: isAttr(node, "on_change").truthy(),
        FieldComponent: Field.getEffectiveFieldComponent({ fields, viewType }, widget, name),
        decorations: {}, // populated below
        attrs: {},
    };
    for (const attribute of node.attributes) {
        if (attribute.name in Field.forbiddenAttributeNames) {
            throw new Error(Field.forbiddenAttributeNames[attribute.name]);
        }

        // prepare field decorations
        if (attribute.name.startsWith("decoration-")) {
            const decorationName = attribute.name.replace("decoration-", "");
            fieldInfo.decorations[decorationName] = attribute.value;
            continue;
        }

        // FIXME: black list special attributes like on_change, name... ?
        fieldInfo.attrs[snakeToCamel(attribute.name)] = attribute.value;
    }
    if (X2M_TYPES.includes(field.type)) {
        fieldInfo.viewMode = getX2MViewModes(node.getAttribute("mode"))[0];
    }

    if (field.views) {
        fieldInfo.views = {};
        for (let viewType in field.views) {
            const subView = field.views[viewType];
            viewType = viewType === "tree" ? "list" : viewType; // FIXME: get rid of this
            const { ArchParser } = viewRegistry.get(viewType);
            const archInfo = new ArchParser().parse(subView.arch, subView.fields);
            fieldInfo.views[viewType] = {
                ...archInfo,
                activeFields: archInfo.fields,
                fields: subView.fields,
            };
        }
    }

    if (!fieldInfo.invisible && X2M_TYPES.includes(field.type)) {
        fieldInfo.relation = field.relation;
        const relatedFields = {};
        if (fieldInfo.FieldComponent.useSubView) {
            const firstView = fieldInfo.views && fieldInfo.views[fieldInfo.viewMode];
            if (firstView) {
                Object.assign(relatedFields, firstView.fields);
            }
        }
        // add fields required by specific FieldComponents
        Object.assign(relatedFields, fieldInfo.FieldComponent.fieldsToFetch);
        // special case for color field
        const colorField = fieldInfo.options.color_field;
        if (colorField) {
            relatedFields[colorField] = { name: colorField, type: "integer", active: true };
        }
        fieldInfo.relatedFields = relatedFields;
    }

    return fieldInfo;
};

Field.forbiddenAttributeNames = {
    decorations: `You cannot use the "decorations" attribute name as it is used as generated prop name for the composite decoration-<something> attributes.`,
};
