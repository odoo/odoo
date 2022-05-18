/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { isTruthy } from "@web/core/utils/xml";
import { X2M_TYPES } from "@web/views/helpers/view_utils";

const { Component, xml } = owl;

const viewRegistry = registry.category("views");
const fieldRegistry = registry.category("fields");

class DefaultField extends Component {}
DefaultField.template = xml``;

function getFieldClassFromRegistry(viewType, fieldType, widget, jsClass) {
    if (jsClass && widget) {
        const name = `${jsClass}.${widget}`;
        if (fieldRegistry.contains(name)) {
            return fieldRegistry.get(name);
        }
    }
    if (viewType && widget) {
        const name = `${viewType}.${widget}`;
        if (fieldRegistry.contains(name)) {
            return fieldRegistry.get(name);
        }
    }

    if (widget) {
        if (fieldRegistry.contains(widget)) {
            return fieldRegistry.get(widget);
        }
        console.warn(`Missing widget: ${widget} for field of type ${fieldType}`);
    }

    if (viewType && fieldType) {
        const name = `${viewType}.${fieldType}`;
        if (fieldRegistry.contains(name)) {
            return fieldRegistry.get(name);
        }
    }

    if (fieldRegistry.contains(fieldType)) {
        return fieldRegistry.get(fieldType);
    }

    return DefaultField;
}

export function fieldVisualFeedback(FieldComponent, record, fieldName) {
    const Cls = FieldComponent || record.activeFields[fieldName].FieldComponent;
    const readonly = record.isReadonly(fieldName);
    const inEdit = record.mode !== "readonly";

    let empty = !record.isVirtual;
    if ("isEmpty" in Cls) {
        empty = empty && Cls.isEmpty(record, fieldName);
    } else {
        empty = empty && !record.data[fieldName];
    }
    empty = inEdit ? empty && readonly : empty;
    return {
        readonly,
        required: record.isRequired(fieldName),
        invalid: record.isInvalid(fieldName),
        empty,
    };
}

export class Field extends Component {
    setup() {
        this.FieldComponent = this.props.record.activeFields[this.props.name].FieldComponent;
        if (!this.FieldComponent) {
            this.FieldComponent = getFieldClassFromRegistry(null, this.type, this.props.name, null);
        }
    }

    get classNames() {
        const { readonly, required, invalid, empty } = fieldVisualFeedback(
            this.FieldComponent,
            this.props.record,
            this.props.name
        );
        const classNames = {
            o_field_widget: true,
            o_readonly_modifier: readonly,
            o_required_modifier: required,
            o_field_invalid: invalid,
            o_field_empty: empty,
            [`o_field_${this.type}`]: true,
            [this.props.class]: !!this.props.class,
        };

        // generate field decorations classNames (only if field-specific decorations
        // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
        // only handle the text-decoration.
        const { decorations } = this.props.record.activeFields[this.props.name];
        const evalContext = this.props.record.evalContext;
        for (const decoName in decorations) {
            const value = evaluateExpr(decorations[decoName], evalContext);
            classNames[`text-${decoName}`] = value;
        }

        return classNames;
    }

    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }

    get fieldComponentProps() {
        const record = this.props.record;
        const field = record.fields[this.props.name];
        const activeField = record.activeFields[this.props.name];

        const readonlyFromModifiers = this.props.record.isReadonly(this.props.name);
        const readonlyFromViewMode = !this.props.record.isInEdition;
        const emptyRequiredValue =
            this.props.record.isRequired(this.props.name) && !this.props.value;

        // Decoration props
        const decorationMap = {};
        const { decorations } = this.props.record.activeFields[this.props.name];
        const evalContext = this.props.record.evalContext;
        for (const decoName in decorations) {
            const value = evaluateExpr(decorations[decoName], evalContext);
            decorationMap[decoName] = value;
        }

        const props = { ...this.props };
        delete props.style;
        delete props.class;

        let extractedPropsForStandaloneComponent = {};
        if (this.FieldComponent.extractProps) {
            extractedPropsForStandaloneComponent = this.FieldComponent.extractProps(
                this.props.name,
                record,
                activeField.attrs
            );
        }

        return {
            ...activeField.props,
            required: this.props.record.isRequired(this.props.name), // AAB: does the field really need this?
            update: async (value) => {
                await record.update({ [this.props.name]: value });
                if (record.selected && record.model.multiEdit) {
                    return;
                }
                // We save only if we're on view mode readonly and no readonly field modifier
                if (readonlyFromViewMode && !readonlyFromModifiers && !emptyRequiredValue) {
                    // TODO: maybe move this in the model
                    return record.save();
                }
            },
            value: this.props.record.data[this.props.name],
            decorations: decorationMap,
            readonly: readonlyFromViewMode || readonlyFromModifiers || false,
            ...props,
            type: field.type,
            ...extractedPropsForStandaloneComponent,
        };
    }
}
Field.template = xml/* xml */ `
    <div t-att-name="props.name" t-att-class="classNames" t-att-style="props.style">
        <t t-component="FieldComponent" t-props="fieldComponentProps"/>
    </div>`;

const EXCLUDED_ATTRS = [
    "name",
    "widget",
    "context",
    "domain",
    "options",
    "modifiers",
    "required",
    "readonly",
    "invisible",
    "on_change",
];

Field.parseFieldNode = function (node, models, modelName, viewType, jsClass) {
    const name = node.getAttribute("name");
    const widget = node.getAttribute("widget");
    const fields = models[modelName];
    const field = fields[name];
    const fieldInfo = {
        name,
        viewType,
        context: node.getAttribute("context") || "{}",
        domain: new Domain(node.getAttribute("domain") || []),
        string: node.getAttribute("string") || field.string,
        widget,
        modifiers: JSON.parse(node.getAttribute("modifiers") || "{}"),
        onChange: isTruthy(node.getAttribute("on_change")),
        FieldComponent: getFieldClassFromRegistry(viewType, fields[name].type, widget, jsClass),
        decorations: {}, // populated below
        noLabel: isTruthy(node.getAttribute("nolabel")),
        props: {},
        rawAttrs: {},
        options: evaluateExpr(node.getAttribute("options") || "{}"),
    };
    fieldInfo.attrs = {
        options: fieldInfo.options,
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

        fieldInfo.rawAttrs[attribute.name] = attribute.value;
        if (EXCLUDED_ATTRS.includes(attribute.name)) {
            continue;
        }
        fieldInfo.attrs[attribute.name] = attribute.value;
    }

    if (fieldInfo.modifiers.invisible !== true && X2M_TYPES.includes(field.type)) {
        const views = {};
        for (const child of node.children) {
            const viewType = child.tagName === "tree" ? "list" : child.tagName;
            const { ArchParser } = viewRegistry.get(viewType);
            const xmlSerializer = new XMLSerializer();
            const subArch = xmlSerializer.serializeToString(child);
            const archInfo = new ArchParser().parse(subArch, models, field.relation);

            views[viewType] = {
                ...archInfo,
                fields: models[field.relation],
            };
            fieldInfo.relatedFields = models[field.relation];
        }
        fieldInfo.viewMode =
            (node.getAttribute("mode") === "tree" ? "list" : node.getAttribute("mode")) ||
            Object.keys(views).find((v) => ["list", "kanban"].includes(v));

        const fieldsToFetch = { ...fieldInfo.FieldComponent.fieldsToFetch }; // should become an array?
        // special case for color field
        // GES: this is not nice, we will look for something better.
        const colorField = fieldInfo.attrs.options.color_field;
        if (colorField) {
            fieldsToFetch[colorField] = { name: colorField, type: "integer", active: true };
        }
        fieldInfo.fieldsToFetch = fieldsToFetch;
        fieldInfo.relation = field.relation; // not really necessary
        fieldInfo.views = views;
    }

    return fieldInfo;
};

Field.forbiddenAttributeNames = {
    decorations: `You cannot use the "decorations" attribute name as it is used as generated prop name for the composite decoration-<something> attributes.`,
};
