// @ts-check
/** @odoo-module native */

import { Component, onWillRender, xml } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { Domain } from "@web/core/domain";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { fieldLog } from "@web/core/utils/asset_log";
import { omit } from "@web/core/utils/collections/objects";
import { getClassNameFromDecoration } from "@web/core/utils/decorations";
import { useRenderCounter } from "@web/core/utils/render_instrumentation";
import { getFieldContext } from "@web/model/relational_model";
import {
    FIELD_DEPENDENCIES_VALIDATION,
    RELATED_FIELDS_VALIDATION,
} from "@web/model/relational_model/field_metadata";

import { getTooltipInfo } from "./field_tooltip.js";
import { standardFieldProps } from "./standard_field_props.js";

const fieldRegistry = registry.category("fields");

const validFieldTypes = [
    "binary",
    "boolean",
    "json",
    "integer",
    "float",
    "monetary",
    "properties",
    "properties_definition",
    "reference",
    "many2one_reference",
    "many2one",
    "one2many",
    "many2many",
    "selection",
    "date",
    "datetime",
    "char",
    "text",
    "html",
];

const supportedInfoEntryShape = {
    name: String,
    label: { type: String, optional: true },
    type: { type: String, optional: true },
    availableTypes: { type: Array, element: String, optional: true },
    default: { optional: true },
    help: { type: String, optional: true },
    choices: {
        type: Array,
        element: {
            type: Object,
            shape: {
                label: { type: String, optional: true },
                value: { optional: true },
                "*": true,
            },
        },
        optional: true,
    },
    isRelationalField: { type: Boolean, optional: true },
    placeholder: { type: String, optional: true },
    "*": true,
};

const supportedInfoValidation = {
    type: Array,
    optional: true,
    element: [
        { type: Object, shape: supportedInfoEntryShape },
        {
            type: Array,
            element: { type: Object, shape: supportedInfoEntryShape },
        },
    ],
};

fieldRegistry.addValidation({
    component: { validate: (/** @type {any} */ c) => c.prototype instanceof Component },
    displayName: { type: String, optional: true },
    supportedAttributes: supportedInfoValidation,
    supportedOptions: supportedInfoValidation,
    supportedTypes: {
        type: Array,
        element: String,
        optional: true,
        validate: (/** @type {any} */ array) =>
            array.every((/** @type {any} */ x) => validFieldTypes.includes(x)),
    },
    extractProps: { type: Function, optional: true },
    isEmpty: { type: Function, optional: true },
    isValid: { type: Function, optional: true },
    additionalClasses: { type: Array, element: String, optional: true },
    fieldDependencies: FIELD_DEPENDENCIES_VALIDATION,
    relatedFields: RELATED_FIELDS_VALIDATION,
    useSubView: { type: Boolean, optional: true },
    interactiveOutsideEdition: { type: [Boolean, Function], optional: true },
    label: { type: [String, { value: false }], optional: true },
    listViewWidth: {
        type: [
            Number,
            { value: "content" },
            {
                type: Array,
                element: Number,
                validate: (/** @type {any} */ array) =>
                    array.length === 1 || array.length === 2,
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

/** @type {WeakMap<Function, Function>} */
const COUNTED_COMPONENTS = new WeakMap();

/**
 * @param {any} C
 * @returns {any}
 */
function countedComponent(C) {
    let counted = COUNTED_COMPONENTS.get(C);
    if (!counted) {
        counted = class extends C {
            setup() {
                useRenderCounter(`fields.${C.template}`);
                super.setup?.();
            }
        };
        Object.defineProperty(counted, "name", { value: C.name });
        COUNTED_COMPONENTS.set(C, counted);
    }
    return counted;
}

/** @type {readonly string[]} */
const FIELD_OWN_PROPS = Object.freeze([
    "attrs",
    "class",
    "fieldInfo",
    "readonly",
    "showTooltip",
    "style",
    "type",
]);

/** @type {Set<string>} */
const warnedWidgetMisses = new Set();

const log = makeLogger("web.field");

export function resetWidgetMissWarnings() {
    warnedWidgetMisses.clear();
}

/**
 * @param {{ supportedOptions?: any[], [key: string]: any }} field
 * @returns {Set<string> | null}
 */
export function getSupportedOptionNames(field) {
    if (!field?.supportedOptions) {
        return null;
    }
    const names = new Set();
    for (const entry of field.supportedOptions) {
        for (const descriptor of Array.isArray(entry) ? entry : [entry]) {
            if (descriptor?.name) {
                names.add(descriptor.name);
            }
        }
    }
    return names;
}

/**
 * @param {string} fieldType
 * @param {string} [widget]
 * @param {string} [viewType]
 * @param {string} [jsClass]
 * @returns {{ component: import("@odoo/owl").ComponentConstructor, extractProps?: Function, supportedTypes?: string[], isEmpty?: Function, isValid?: Function, additionalClasses?: string[], relatedFields?: Array | Function, useSubView?: boolean, [key: string]: any }}
 */
export function getFieldFromRegistry(fieldType, widget, viewType, jsClass) {
    fieldLog("resolve", widget || fieldType, viewType || "", jsClass || "");
    const prefixes = jsClass ? [jsClass, viewType, ""] : [viewType, ""];
    /** @param {string} key */
    const findInRegistry = (key) => {
        for (const prefix of prefixes) {
            const field = fieldRegistry.get(
                prefix ? `${prefix}.${key}` : key,
                undefined,
            );
            if (field) {
                return field;
            }
        }
    };
    if (widget) {
        const field = findInRegistry(widget);
        const warningKey = `${widget}|${fieldType}`;
        if (field) {
            if (
                field.supportedTypes &&
                !field.supportedTypes.includes(fieldType) &&
                !warnedWidgetMisses.has(warningKey)
            ) {
                warnedWidgetMisses.add(warningKey);
                console.warn(
                    `The widget: ${widget} don't support the type ${fieldType}`,
                );
            }
            return field;
        }
        if (!warnedWidgetMisses.has(warningKey)) {
            warnedWidgetMisses.add(warningKey);
            console.warn(`Missing widget: ${widget} for field of type ${fieldType}`);
        }
    }
    return /** @type {any} */ (
        findInRegistry(fieldType) || { component: DefaultField }
    );
}

/**
 * @param {{ isEmpty?: (record: any, fieldName: string) => boolean, isValid?: (record: any, fieldName: string, fieldInfo: any) => boolean }} field
 * @param {import("@web/model/relational_model/record").RelationalRecord} record
 * @param {string} fieldName
 * @param {{ readonly?: string, required?: string }} fieldInfo
 * @returns {{ readonly: boolean, required: boolean, invalid: boolean, empty: boolean }}
 */
export function fieldVisualFeedback(field, record, fieldName, fieldInfo) {
    const readonly = evaluateBooleanExpr(
        fieldInfo.readonly,
        record.evalContextWithVirtualIds,
    );
    const inEdit = record.isInEdition;

    let empty = !record.isNew;
    empty =
        empty &&
        (field.isEmpty ? field.isEmpty(record, fieldName) : !record.data[fieldName]);
    empty = inEdit ? empty && readonly : empty;
    let required;
    return {
        readonly,
        get required() {
            required ??= evaluateBooleanExpr(
                fieldInfo.required,
                record.evalContextWithVirtualIds,
            );
            return required;
        },
        invalid: field.isValid
            ? !field.isValid(record, fieldName, fieldInfo)
            : record.isFieldInvalid(fieldName),
        empty,
    };
}

/**
 * @param {{ name: string, type: string, widget?: string, string?: string, relation?: string, domain?: string, selection?: Array, tags?: Array, relatedPropertyField?: any }} propertyField
 * @param {string} [viewType]
 * @returns {{ name: string, type: string, viewType?: string, widget: string, string?: string, field: ReturnType<typeof getFieldFromRegistry>, options: Object, readonly: string, required: string, invisible: string, column_invisible: string, context: string, attrs: Object, decorations: Object, [key: string]: any }}
 */
export function getPropertyFieldInfo(propertyField, viewType) {
    const { name, relatedPropertyField, string, type, widget } = propertyField;

    /** @type {any} */
    const fieldInfo = {
        name,
        string,
        type,
        viewType,
        widget: widget || type,
        options: {},
        column_invisible: "False",
        invisible: "False",
        readonly: "False",
        required: "False",
        attrs: {},
        relatedPropertyField,

        context: "{}",
        help: undefined,
        onChange: false,
        forceSave: false,
        decorations: {},
        domain: undefined,
    };

    if (type === "many2one" || type === "many2many") {
        const { domain, relation } = propertyField;
        fieldInfo.relation = relation;
        fieldInfo.domain = domain;

        if (relation === "res.users" || relation === "res.partner") {
            fieldInfo.widget =
                propertyField.type === "many2one"
                    ? "many2one_avatar"
                    : "many2many_tags_avatar";
        } else {
            fieldInfo.widget =
                propertyField.type === "many2one" ? type : "many2many_tags";
        }
    } else if (type === "tags") {
        fieldInfo.tags = propertyField.tags;
        fieldInfo.widget = `property_tags`;
    } else if (type === "selection") {
        fieldInfo.selection = propertyField.selection;
    }

    fieldInfo.field = getFieldFromRegistry(
        propertyField.type,
        fieldInfo.widget,
        viewType,
    );
    let { relatedFields } = fieldInfo.field;
    if (relatedFields) {
        if (relatedFields instanceof Function) {
            relatedFields = relatedFields({ options: {}, attrs: {} });
        }
        fieldInfo.relatedFields = Object.fromEntries(
            relatedFields.map((/** @type {any} */ f) => [f.name, f]),
        );
    }

    return fieldInfo;
}
const archString = { type: [String, { value: null }], optional: true };

export const fieldProps = {
    ...standardFieldProps,
    attrs: { type: Object, optional: true },
    class: archString,
    fieldInfo: { type: Object, optional: true },
    showTooltip: { type: Boolean, optional: true },
    style: archString,
    type: archString,
    "*": true,
};

export class Field extends Component {
    static template = "web.Field";
    static props = fieldProps;

    /** @type {{ readonly: boolean, required: boolean, invalid: boolean, empty: boolean }} */
    _visualFeedback;

    /** @type {(record?: any) => any[] | undefined} */
    dynamicDomain;

    setup() {
        if (this.props.fieldInfo) {
            this.field = this.props.fieldInfo.field;
        } else {
            const fieldType = this.props.record.fields[this.props.name].type;
            this.field = getFieldFromRegistry(fieldType, this.props.type);
        }
        log.lifecycle("setup", () => ({
            name: this.props.name,
            widget: this.props.type,
            component: this.field?.component?.name,
            resModel: this.props.record.resModel,
        }));
        this.dynamicDomain = (record = this.props.record) => {
            const { fieldInfo } = this.props;
            if (fieldInfo?.domain) {
                return new Domain(
                    evaluateExpr(fieldInfo.domain, record.evalContext),
                ).toList();
            }
        };
        onWillRender(() => {
            this._visualFeedback = fieldVisualFeedback(
                this.field,
                this.props.record,
                this.props.name,
                this.props.fieldInfo || {},
            );
            this._tooltip = this.computeTooltip();
        });
    }

    /** @returns {Record<string, boolean>} */
    get classNames() {
        const { class: _class, fieldInfo, record } = this.props;
        const { readonly, required, invalid, empty } = this._visualFeedback;
        const classNames = {
            o_field_widget: true,
            o_readonly_modifier: readonly,
            o_required_modifier: required,
            o_field_invalid: invalid,
            o_field_empty: empty,
            [`o_field_${this.type}`]: true,
            ...(_class ? { [_class]: true } : {}),
        };
        if (this.field.additionalClasses) {
            for (const cls of this.field.additionalClasses) {
                classNames[cls] = true;
            }
        }

        if (fieldInfo?.decorations) {
            const { decorations } = fieldInfo;
            for (const decoName of Object.keys(decorations)) {
                const value = evaluateBooleanExpr(
                    decorations[decoName],
                    record.evalContextWithVirtualIds,
                );
                classNames[getClassNameFromDecoration(decoName)] = value;
            }
        }

        return classNames;
    }

    /** @returns {string} */
    get type() {
        return this.props.type || this.props.record.fields[this.props.name].type;
    }

    /** @returns {import("@odoo/owl").ComponentConstructor} */
    get fieldComponent() {
        return countedComponent(this.field.component);
    }

    /** @returns {Object} */
    get fieldComponentProps() {
        const record = this.props.record;
        let readonly = this.props.readonly || false;

        let propsFromNode = {};
        if (this.props.fieldInfo) {
            let fieldInfo = this.props.fieldInfo;
            readonly = readonly || this._visualFeedback.readonly;

            if (this.field.extractProps) {
                if (this.props.attrs) {
                    fieldInfo = {
                        ...fieldInfo,
                        attrs: { ...fieldInfo.attrs, ...this.props.attrs },
                    };
                }
                if (
                    fieldInfo.attrs.placeholder ||
                    fieldInfo.options.placeholder_field
                ) {
                    fieldInfo = {
                        ...fieldInfo,
                        placeholder:
                            record.data[fieldInfo.options.placeholder_field] ||
                            fieldInfo.attrs.placeholder,
                    };
                }

                const contextOwner = this;
                const dynamicInfo = {
                    get context() {
                        return getFieldContext(
                            record,
                            fieldInfo.name,
                            fieldInfo.context,
                            contextOwner,
                        );
                    },
                    domain: this.dynamicDomain,
                    required: this._visualFeedback.required,
                    readonly: readonly,
                };
                propsFromNode = this.field.extractProps(fieldInfo, dynamicInfo);
            }
        }

        const props = omit(this.props, ...FIELD_OWN_PROPS);

        const { interactiveOutsideEdition } = this.field;
        const inEditionOnly = !(typeof interactiveOutsideEdition === "function"
            ? interactiveOutsideEdition(this.props.fieldInfo || {})
            : interactiveOutsideEdition);

        return {
            readonly: (inEditionOnly && !record.isInEdition) || readonly,
            ...propsFromNode,
            ...props,
        };
    }

    /** @returns {string | false} */
    computeTooltip() {
        if (!this.props.showTooltip) {
            return false;
        }
        const field = this.props.record.fields[this.props.name];
        const fieldInfo = this.props.fieldInfo || {};
        if (!odoo.debug && !(fieldInfo.help ?? field.help)) {
            return false;
        }
        return getTooltipInfo({ field, fieldInfo });
    }

    /** @returns {string | false} */
    get tooltip() {
        return /** @type {string | false} */ (this._tooltip);
    }
}
