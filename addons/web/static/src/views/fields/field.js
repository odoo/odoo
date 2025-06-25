import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { utils } from "@web/core/ui/ui_service";
import { exprToBoolean } from "@web/core/utils/strings";
import { getFieldContext } from "@web/model/relational_model/utils";
import { X2M_TYPES, getClassNameFromDecoration } from "@web/views/utils";
import { getTooltipInfo } from "./field_tooltip";

import { Component, xml } from "@odoo/owl";

const isSmall = utils.isSmall;

const viewRegistry = registry.category("views");
const fieldRegistry = registry.category("fields");

const supportedInfoValidation = {
    type: Array,
    element: Object,
    shape: {
        label: String,
        name: String,
        type: String,
        availableTypes: { type: Array, element: String, optional: true },
        default: { type: String, optional: true },
        help: { type: String, optional: true },
        choices: /* choices if type == selection */ {
            type: Array,
            element: Object,
            shape: { label: String, value: String },
            optional: true,
        },
    },
    optional: true,
};

fieldRegistry.addValidation({
    component: { validate: (c) => c.prototype instanceof Component },
    displayName: { type: String, optional: true },
    supportedAttributes: supportedInfoValidation,
    supportedOptions: supportedInfoValidation,
    supportedTypes: { type: Array, element: String, optional: true },
    extractProps: { type: Function, optional: true },
    isEmpty: { type: Function, optional: true },
    isValid: { type: Function, optional: true }, // Override the validation for the validation visual feedbacks
    additionalClasses: { type: Array, element: String, optional: true },
    fieldDependencies: {
        type: [Function, { type: Array, element: Object, shape: { name: String, type: String } }],
        optional: true,
    },
    relatedFields: {
        type: [
            Function,
            {
                type: Array,
                element: Object,
                shape: {
                    name: String,
                    type: String,
                    readonly: { type: Boolean, optional: true },
                    selection: { type: Array, element: { type: Array, element: String } },
                    optional: true,
                },
            },
        ],
        optional: true,
    },
    useSubView: { type: Boolean, optional: true },
    label: { type: [String, { value: false }], optional: true },
    listViewWidth: {
        type: [
            Number,
            {
                type: Array,
                element: Number,
                validate: (array) => array.length === 1 || array.length === 2,
            },
            Function,
        ],
        optional: true,
    },
});

class DefaultField extends Component {
    static template = xml``;
    static props = ["*"];
}

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
    const readonly = evaluateBooleanExpr(fieldInfo.readonly, record.evalContextWithVirtualIds);
    const required = evaluateBooleanExpr(fieldInfo.required, record.evalContextWithVirtualIds);
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
        required,
        invalid: field.isValid
            ? !field.isValid(record, fieldName, fieldInfo)
            : record.isFieldInvalid(fieldName),
        empty,
    };
}

export function getPropertyFieldInfo(propertyField) {
    const { name, relatedPropertyField, string, type } = propertyField;

    const fieldInfo = {
        name,
        string,
        type,
        widget: type,
        options: {},
        column_invisible: "False",
        invisible: "False",
        readonly: "False",
        required: "False",
        attrs: {},
        relatedPropertyField,

        // ??? We don t use it ? But it s in the fieldInfo of the field
        context: "{}",
        help: undefined,
        onChange: false,
        forceSave: false,
        decorations: {},
        // ???
    };

    if (type === "many2one" || type === "many2many") {
        const { domain, relation } = propertyField;
        fieldInfo.relation = relation;
        fieldInfo.domain = domain;

        if (relation === "res.users" || relation === "res.partner") {
            fieldInfo.widget =
                propertyField.type === "many2one" ? "many2one_avatar" : "many2many_tags_avatar";
        } else {
            fieldInfo.widget = propertyField.type === "many2one" ? type : "many2many_tags";
        }
    } else if (type === "tags") {
        fieldInfo.tags = propertyField.tags;
        fieldInfo.widget = `property_tags`;
    } else if (type === "selection") {
        fieldInfo.selection = propertyField.selection;
    }

    fieldInfo.field = getFieldFromRegistry(propertyField.type, fieldInfo.widget);
    let { relatedFields } = fieldInfo.field;
    if (relatedFields) {
        if (relatedFields instanceof Function) {
            relatedFields = relatedFields({ options: {}, attrs: {} });
        }
        fieldInfo.relatedFields = Object.fromEntries(relatedFields.map((f) => [f.name, f]));
    }

    return fieldInfo;
}
export class Field extends Component {
    static template = "web.Field";
    static props = ["fieldInfo?", "*"];
    static parseFieldNode = function (node, models, modelName, viewType, jsClass) {
        const name = node.getAttribute("name");
        const widget = node.getAttribute("widget");
        const fields = models[modelName].fields;
        if (!fields[name]) {
            throw new Error(`"${modelName}"."${name}" field is undefined.`);
        }
        const field = getFieldFromRegistry(fields[name].type, widget, viewType, jsClass);
        const fieldInfo = {
            name,
            type: fields[name].type,
            viewType,
            widget,
            field,
            context: "{}",
            string: fields[name].string,
            help: undefined,
            onChange: false,
            forceSave: false,
            options: {},
            decorations: {},
            attrs: {},
            domain: undefined,
        };

        for (const attr of ["invisible", "column_invisible", "readonly", "required"]) {
            fieldInfo[attr] = node.getAttribute(attr);
            if (fieldInfo[attr] === "True") {
                if (attr === "column_invisible") {
                    fieldInfo.invisible = "True";
                }
            } else if (fieldInfo[attr] === null && fields[name][attr]) {
                fieldInfo[attr] = "True";
            }
        }

        for (const { name, value } of node.attributes) {
            if (["name", "widget"].includes(name)) {
                // avoid adding name and widget to attrs
                continue;
            }
            if (["context", "string", "help", "domain"].includes(name)) {
                fieldInfo[name] = value;
            } else if (name === "on_change") {
                fieldInfo.onChange = exprToBoolean(value);
            } else if (name === "options") {
                fieldInfo.options = evaluateExpr(value);
            } else if (name === "force_save") {
                fieldInfo.forceSave = exprToBoolean(value);
            } else if (name.startsWith("decoration-")) {
                // prepare field decorations
                fieldInfo.decorations[name.replace("decoration-", "")] = value;
            } else if (!name.startsWith("t-att")) {
                // all other (non dynamic) attributes
                fieldInfo.attrs[name] = value;
            }
        }
        if (name === "id") {
            fieldInfo.readonly = "True";
        }

        if (widget === "handle") {
            fieldInfo.isHandle = true;
        }

        if (X2M_TYPES.includes(fields[name].type)) {
            const views = {};
            let relatedFields = fieldInfo.field.relatedFields;
            if (relatedFields) {
                if (relatedFields instanceof Function) {
                    relatedFields = relatedFields(fieldInfo);
                }
                for (const relatedField of relatedFields) {
                    if (!("readonly" in relatedField)) {
                        relatedField.readonly = true;
                    }
                }
                relatedFields = Object.fromEntries(relatedFields.map((f) => [f.name, f]));
                views.default = { fieldNodes: relatedFields, fields: relatedFields };
                if (!fieldInfo.field.useSubView) {
                    fieldInfo.viewMode = "default";
                }
            }
            for (const child of node.children) {
                const viewType = child.tagName;
                const { ArchParser } = viewRegistry.get(viewType);
                // We copy and hence isolate the subview from the main view's tree
                // This way, the subview's tree is autonomous and CSS selectors will work normally
                const childCopy = child.cloneNode(true);
                const archInfo = new ArchParser().parse(childCopy, models, fields[name].relation);
                views[viewType] = {
                    ...archInfo,
                    limit: archInfo.limit || 40,
                    fields: models[fields[name].relation].fields,
                };
            }

            let viewMode = node.getAttribute("mode");
            if (viewMode) {
                if (viewMode.split(",").length !== 1) {
                    viewMode = isSmall() ? "kanban" : "list";
                }
            } else {
                if (views.list && !views.kanban) {
                    viewMode = "list";
                } else if (!views.list && views.kanban) {
                    viewMode = "kanban";
                } else if (views.list && views.kanban) {
                    viewMode = isSmall() ? "kanban" : "list";
                }
            }
            if (viewMode) {
                fieldInfo.viewMode = viewMode;
            }
            if (Object.keys(views).length) {
                fieldInfo.relatedFields = models[fields[name].relation]?.fields;
                fieldInfo.views = views;
            }
        }
        if (fields[name].type === "many2one_reference") {
            let relatedFields = fieldInfo.field.relatedFields;
            if (relatedFields) {
                relatedFields = Object.fromEntries(relatedFields.map((f) => [f.name, f]));
                fieldInfo.viewMode = "default";
                fieldInfo.views = {
                    default: { fieldNodes: relatedFields, fields: relatedFields },
                };
            }
        }

        return fieldInfo;
    };

    setup() {
        if (this.props.fieldInfo) {
            this.field = this.props.fieldInfo.field;
        } else {
            const fieldType = this.props.record.fields[this.props.name].type;
            this.field = getFieldFromRegistry(fieldType, this.props.type);
        }
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
            for (const decoName in decorations) {
                const value = evaluateBooleanExpr(
                    decorations[decoName],
                    record.evalContextWithVirtualIds
                );
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
        let readonly = this.props.readonly || false;

        let propsFromNode = {};
        if (this.props.fieldInfo) {
            let fieldInfo = this.props.fieldInfo;
            readonly =
                readonly ||
                evaluateBooleanExpr(fieldInfo.readonly, record.evalContextWithVirtualIds);

            if (this.field.extractProps) {
                if (this.props.attrs) {
                    fieldInfo = {
                        ...fieldInfo,
                        attrs: { ...fieldInfo.attrs, ...this.props.attrs },
                    };
                }

                const dynamicInfo = {
                    get context() {
                        return getFieldContext(record, fieldInfo.name, fieldInfo.context);
                    },
                    domain() {
                        const evalContext = record.evalContext;
                        if (fieldInfo.domain) {
                            return new Domain(evaluateExpr(fieldInfo.domain, evalContext)).toList();
                        }
                    },
                    required: evaluateBooleanExpr(
                        fieldInfo.required,
                        record.evalContextWithVirtualIds
                    ),
                    readonly: readonly,
                };
                propsFromNode = this.field.extractProps(fieldInfo, dynamicInfo);
            }
        }

        const props = { ...this.props };
        delete props.style;
        delete props.class;
        delete props.showTooltip;
        delete props.fieldInfo;
        delete props.attrs;
        delete props.type;
        delete props.readonly;

        return {
            readonly: readonly || !record.isInEdition || false,
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
