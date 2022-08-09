/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { archParseBoolean, evalDomain, X2M_TYPES } from "@web/views/utils";
import { getTooltipInfo } from "./field_tooltip";

const { Component, xml } = owl;

const viewRegistry = registry.category("views");
const fieldRegistry = registry.category("fields");

class DefaultField extends Component {}
DefaultField.template = xml``;

function getFieldClassFromRegistry(fieldType, widget, viewType, jsClass) {
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

export function fieldVisualFeedback(FieldComponent, record, fieldName, fieldInfo) {
    const modifiers = fieldInfo.modifiers || {};
    const readonly = evalDomain(modifiers.readonly, record.evalContext);
    const inEdit = record.mode !== "readonly";

    let empty = !record.isVirtual;
    if ("isEmpty" in FieldComponent) {
        empty = empty && FieldComponent.isEmpty(record, fieldName);
    } else {
        empty = empty && !record.data[fieldName];
    }
    empty = inEdit ? empty && readonly : empty;
    return {
        readonly,
        required: evalDomain(modifiers.required, record.evalContext),
        invalid: record.isInvalid(fieldName),
        empty,
    };
}

export class Field extends Component {
    setup() {
        this.FieldComponent = this.props.fieldInfo.FieldComponent;
        if (!this.FieldComponent) {
            const fieldType = this.props.record.fields[this.props.name].type;
            this.FieldComponent = getFieldClassFromRegistry(fieldType, this.props.type);
        }
    }

    get classNames() {
        const { class: _class, fieldInfo, name, record } = this.props;
        const { readonly, required, invalid, empty } = fieldVisualFeedback(
            this.FieldComponent,
            record,
            name,
            fieldInfo
        );
        const classNames = {
            o_field_widget: true,
            o_readonly_modifier: readonly,
            o_required_modifier: required,
            o_field_invalid: invalid,
            o_field_empty: empty,
            [`o_field_${this.type}`]: true,
            [_class]: Boolean(_class),
        };

        // generate field decorations classNames (only if field-specific decorations
        // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
        // only handle the text-decoration.
        const { decorations } = fieldInfo;
        const evalContext = record.evalContext;
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
        const evalContext = record.evalContext;
        const field = record.fields[this.props.name];
        const fieldInfo = this.props.fieldInfo;

        const modifiers = fieldInfo.modifiers || {};
        const required = evalDomain(modifiers.required, evalContext);
        const readonlyFromModifiers = evalDomain(modifiers.readonly, evalContext);
        const readonlyFromViewMode = !this.props.record.isInEdition;
        const emptyRequiredValue = required && !this.props.value;

        // Decoration props
        const decorationMap = {};
        const { decorations } = fieldInfo;
        for (const decoName in decorations) {
            const value = evaluateExpr(decorations[decoName], evalContext);
            decorationMap[decoName] = value;
        }

        let propsFromAttrs = fieldInfo.propsFromAttrs;
        if (this.props.attrs) {
            const extractProps = this.FieldComponent.extractProps || (() => ({}));
            propsFromAttrs = extractProps({
                field,
                attrs: {
                    ...this.props.attrs,
                    options: evaluateExpr(this.props.attrs.options || "{}"),
                },
            });
        }

        const props = { ...this.props };
        delete props.style;
        delete props.class;
        delete props.showTooltip;
        delete props.fieldInfo;
        delete props.attrs;

        return {
            ...fieldInfo.props,
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
            ...propsFromAttrs,
            ...props,
            type: field.type,
        };
    }

    get tooltip() {
        if (this.props.showTooltip) {
            const tooltip = getTooltipInfo({
                field: this.props.record.fields[this.props.name],
                fieldInfo: this.props.fieldInfo,
            });
            if (Boolean(odoo.debug) || (tooltip && JSON.parse(tooltip).field.help)) {
                return tooltip;
            }
        }
        return false;
    }
}
Field.template = xml/* xml */ `
    <div t-att-name="props.name" t-att-class="classNames" t-att-style="props.style" t-att-data-tooltip-template="tooltip and 'web.FieldTooltip'" t-att-data-tooltip-info="tooltip">
        <t t-component="FieldComponent" t-props="fieldComponentProps"/>
    </div>`;

Field.parseFieldNode = function (node, models, modelName, viewType, jsClass) {
    const name = node.getAttribute("name");
    const widget = node.getAttribute("widget");
    const fields = models[modelName];
    const field = fields[name];
    const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
    const fieldInfo = {
        name,
        viewType,
        context: node.getAttribute("context") || "{}",
        string: node.getAttribute("string") || field.string,
        help: node.getAttribute("help"),
        widget,
        modifiers,
        onChange: archParseBoolean(node.getAttribute("on_change")),
        FieldComponent: getFieldClassFromRegistry(fields[name].type, widget, viewType, jsClass),
        forceSave: archParseBoolean(node.getAttribute("force_save")),
        decorations: {}, // populated below
        noLabel: archParseBoolean(node.getAttribute("nolabel")),
        props: {},
        rawAttrs: {},
        options: evaluateExpr(node.getAttribute("options") || "{}"),
        alwaysInvisible: modifiers.invisible === true || modifiers.column_invisible === true,
    };
    if (node.getAttribute("domain")) {
        fieldInfo.domain = node.getAttribute("domain");
    }
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

        if (!attribute.name.startsWith("t-att")) {
            fieldInfo.rawAttrs[attribute.name] = attribute.value;
        }
    }

    if (viewType !== "kanban") {
        // FIXME WOWL: find a better solution
        const extractProps = fieldInfo.FieldComponent.extractProps || (() => ({}));
        fieldInfo.propsFromAttrs = extractProps({
            field,
            attrs: { ...fieldInfo.rawAttrs, options: fieldInfo.options },
        });
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

        let viewMode = node.getAttribute("mode");
        if (!viewMode) {
            if (views.list && !views.kanban) {
                viewMode = "list";
            } else if (!views.list && views.kanban) {
                viewMode = "kanban";
            } else {
                viewMode = "list,kanban";
            }
        } else {
            viewMode = viewMode.replace("tree", "list");
        }
        fieldInfo.viewMode = viewMode;

        const fieldsToFetch = { ...fieldInfo.FieldComponent.fieldsToFetch }; // should become an array?
        // special case for color field
        // GES: this is not nice, we will look for something better.
        const colorField = fieldInfo.options.color_field;
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
Field.defaultProps = { fieldInfo: {} };
