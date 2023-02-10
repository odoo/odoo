/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import {
    archParseBoolean,
    evalDomain,
    getClassNameFromDecoration,
    X2M_TYPES,
} from "@web/views/utils";
import { getTooltipInfo } from "./field_tooltip";

import { Component, xml } from "@odoo/owl";

const viewRegistry = registry.category("views");
const fieldRegistry = registry.category("fields");

class DefaultField extends Component {}
DefaultField.template = xml``;

export function getFieldFromRegistry(fieldType, widget, viewType, jsClass) {
    const prefixes = jsClass ? [jsClass, viewType, ""] : [viewType, ""];
    const findInRegistry = (key) => {
        for (const prefix of prefixes) {
            const _key = prefix ? `${prefix}.${key}` : key;
            if (fieldRegistry.contains(_key)) {
                return fieldRegistry.get(_key);
            }
        }
    };
    if (widget) {
        const field = findInRegistry(widget);
        if (field) {
            return field;
        }
        console.warn(`Missing widget: ${widget} for field of type ${fieldType}`);
    }
    return findInRegistry(fieldType) || { component: DefaultField };
}

export function fieldVisualFeedback(field, record, fieldName, fieldInfo) {
    const modifiers = fieldInfo.modifiers || {};
    const readonly = evalDomain(modifiers.readonly, record.evalContext);
    const inEdit = record.isInEdition;

    let empty = !record.isNew;
    if ("isEmpty" in field) {
        empty = empty && field.isEmpty(record, fieldName);
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
        if (this.props.fieldInfo) {
            this.field = this.props.fieldInfo.field;
        } else {
            const fieldType = this.props.record.fields[this.props.name].type;
            this.field = getFieldFromRegistry(fieldType, this.props.type);
        }

        owl.onWillRender(() => {
            console.log("render Field");
        });
    }

    get classNames() {
        const { class: _class, fieldInfo, name, record } = this.props;
        const { readonly, required, invalid, empty } = fieldVisualFeedback(
            this.field,
            record,
            name,
            fieldInfo || {}
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
        if (this.field.additionalClasses) {
            for (const cls of this.field.additionalClasses) {
                classNames[cls] = true;
            }
        }

        // generate field decorations classNames (only if field-specific decorations
        // have been defined in an attribute, e.g. decoration-danger="other_field = 5")
        // only handle the text-decoration.
        if (fieldInfo && fieldInfo.decorations) {
            const { decorations } = fieldInfo;
            const evalContext = record.evalContext;
            for (const decoName in decorations) {
                const value = evaluateExpr(decorations[decoName], evalContext);
                classNames[getClassNameFromDecoration(decoName)] = value;
            }
        }

        return classNames;
    }

    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }

    get fieldComponentProps() {
        const record = this.props.record;
        const evalContext = record.evalContext;

        let readonlyFromModifiers = false;
        let propsFromNode = {};
        if (this.props.fieldInfo) {
            let fieldInfo = this.props.fieldInfo;

            const modifiers = fieldInfo.modifiers || {};
            readonlyFromModifiers = evalDomain(modifiers.readonly, evalContext);

            if (this.props.attrs) {
                fieldInfo = {
                    ...fieldInfo,
                    attrs: { ...fieldInfo.attrs, ...this.props.attrs },
                };
            }
            propsFromNode = this.field.extractProps ? this.field.extractProps(fieldInfo) : {};
        }

        const props = { ...this.props };
        delete props.style;
        delete props.class;
        delete props.showTooltip;
        delete props.fieldInfo;
        delete props.attrs;
        delete props.type;

        return {
            readonly: !record.isInEdition || readonlyFromModifiers || false,
            ...propsFromNode,
            ...props,
        };
    }

    get tooltip() {
        if (this.props.showTooltip) {
            const tooltip = getTooltipInfo({
                field: this.props.record.fields[this.props.name],
                fieldInfo: this.props.fieldInfo || {},
            });
            if (Boolean(odoo.debug) || (tooltip && JSON.parse(tooltip).field.help)) {
                return tooltip;
            }
        }
        return false;
    }
}
Field.template = "web.Field";

Field.parseFieldNode = function (node, models, modelName, viewType, jsClass) {
    const name = node.getAttribute("name");
    const widget = node.getAttribute("widget");
    const fields = models[modelName];
    const field = getFieldFromRegistry(fields[name].type, widget, viewType, jsClass);
    const fieldInfo = {
        name,
        viewType,
        widget,
        modifiers: {},
        field,
        context: "{}",
        string: fields[name].string,
        help: undefined,
        onChange: false,
        forceSave: false,
        options: {},
        alwaysInvisible: false,
        decorations: {},
        attrs: {},
        domain: undefined,
    };

    for (const { name, value } of node.attributes) {
        if (["name", "widget"].includes(name)) {
            // avoid adding name and widget to attrs
            continue;
        }
        if (["context", "string", "help", "domain"].includes(name)) {
            fieldInfo[name] = value;
        } else if (name === "modifiers") {
            fieldInfo.modifiers = JSON.parse(value);
            fieldInfo.alwaysInvisible =
                fieldInfo.modifiers.invisible === true ||
                fieldInfo.modifiers.column_invisible === true;
        } else if (name === "on_change") {
            fieldInfo.onChange = archParseBoolean(value);
        } else if (name === "options") {
            fieldInfo.options = evaluateExpr(value);
        } else if (name === "force_save") {
            fieldInfo.forceSave = archParseBoolean(value);
        } else if (name.startsWith("decoration-")) {
            // prepare field decorations
            fieldInfo.decorations[name.replace("decoration-", "")] = value;
        } else if (!name.startsWith("t-att")) {
            // all other (non dynamic) attributes
            fieldInfo.attrs[name] = value;
        }
    }

    if (X2M_TYPES.includes(fields[name].type)) {
        const views = {};
        let fieldsToFetch = fieldInfo.field.fieldsToFetch;
        if (fieldsToFetch) {
            if (fieldsToFetch instanceof Function) {
                fieldsToFetch = fieldsToFetch(fieldInfo);
            }
            fieldsToFetch = Object.fromEntries(fieldsToFetch.map((f) => [f.name, f]));
            views.default = { fieldNodes: fieldsToFetch, fields: fieldsToFetch };
            fieldInfo.viewMode = "default";
        } else {
            for (const child of node.children) {
                const viewType = child.tagName === "tree" ? "list" : child.tagName;
                const { ArchParser } = viewRegistry.get(viewType);
                const xmlSerializer = new XMLSerializer();
                const subArch = xmlSerializer.serializeToString(child);
                const archInfo = new ArchParser().parse(subArch, models, fields[name].relation);
                views[viewType] = {
                    ...archInfo,
                    fields: models[fields[name].relation],
                };
            }

            let viewMode = node.getAttribute("mode");
            if (!viewMode) {
                if (views.list && !views.kanban) {
                    viewMode = "list";
                } else if (!views.list && views.kanban) {
                    viewMode = "kanban";
                } else if (views.list && views.kanban) {
                    viewMode = "list,kanban";
                }
            } else {
                viewMode = viewMode.replace("tree", "list");
            }
            fieldInfo.viewMode = viewMode;
        }
        if (Object.keys(views).length) {
            fieldInfo.relatedFields = models[field.relation];
            fieldInfo.views = views;
        }
    }

    return fieldInfo;
};

Field.props = ["fieldInfo?", "*"];
