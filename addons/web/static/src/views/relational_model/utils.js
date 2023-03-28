/* @odoo-module */

import { makeContext } from "@web/core/context";
import { omit } from "@web/core/utils/objects";

export const addFieldDependencies = (activeFields, fields, fieldDependencies = []) => {
    for (const field of fieldDependencies) {
        if (!activeFields[field.name]) {
            activeFields[field.name] = {
                context: field.context || "{}",
                invisible: field.invisible || false,
                readonly: field.readonly || false,
                required: field.required || false,
                onChange: field.onChange || false,
            };
        }
        if (!fields[field.name]) {
            fields[field.name] = omit(field, [
                "context",
                "invisible",
                "required",
                "readonly",
                "onChange",
            ]);
        }
    }
};

export const extractFieldsFromArchInfo = ({ fieldNodes, widgetNodes }, fields) => {
    const activeFields = {};
    fields = { ...fields };
    for (const fieldNode of Object.values(fieldNodes)) {
        const fieldName = fieldNode.name;
        const modifiers = fieldNode.modifiers || {};
        if (!(fieldName in activeFields)) {
            activeFields[fieldName] = {
                context: fieldNode.context || "{}",
                invisible: modifiers.invisible || modifiers.column_invisible || false,
                readonly: modifiers.readonly || false,
                required: modifiers.required || false,
                onChange: fieldNode.onChange || false,
            };
            if (modifiers.invisible === true || modifiers.column_invisible === true) {
                continue; // always invisible
            }
            if (fieldNode.views) {
                const viewDescr = fieldNode.views[fieldNode.viewMode];
                activeFields[fieldName].related = extractFieldsFromArchInfo(
                    viewDescr,
                    viewDescr.fields
                );
                activeFields[fieldName].limit = viewDescr.limit;
            }
        } else {
            // TODO (see task description for multiple occurrences of fields)
        }
        if (fieldNode.field) {
            addFieldDependencies(activeFields, fields, fieldNode.field.fieldDependencies);
        }
    }
    for (const widgetInfo of Object.values(widgetNodes || {})) {
        addFieldDependencies(activeFields, fields, widgetInfo.widget.fieldDependencies);
    }
    return { activeFields, fields };
};

const SENTINEL = Symbol("sentinel");
function getFieldContext(fieldName, activeFields, evalContext, parentActiveFields = null) {
    const rawContext = activeFields[fieldName].context;
    if (!rawContext || rawContext === "{}") {
        return;
    }

    evalContext = { ...evalContext };
    for (const fieldName in activeFields) {
        evalContext[fieldName] = SENTINEL;
    }
    if (parentActiveFields) {
        evalContext.parent = {};
        for (const fieldName in parentActiveFields) {
            evalContext.parent[fieldName] = SENTINEL;
        }
    }
    const evaluatedContext = makeContext([rawContext], evalContext);
    for (const key in evaluatedContext) {
        if (evaluatedContext[key] === SENTINEL || key.startsWith("default_")) {
            // FIXME: this isn't perfect, a value might be evaluted to something else
            // than the symbol because of the symbol
            delete evaluatedContext[key];
        }
    }
    if (Object.keys(evaluatedContext).length > 0) {
        return evaluatedContext;
    }
}

export const getFieldsSpec = (activeFields, fields, evalContext, parentActiveFields = null) => {
    console.log("getFieldsSpec");
    const fieldsSpec = {};
    for (const fieldName in activeFields) {
        const fieldDescr = activeFields[fieldName];
        fieldsSpec[fieldName] = {};
        // X2M
        if (fieldDescr.related) {
            fieldsSpec[fieldName].fields = getFieldsSpec(
                fieldDescr.related.activeFields,
                fieldDescr.related.fields,
                evalContext,
                activeFields
            );
            fieldsSpec[fieldName].limit = fieldDescr.limit || 40;
        }
        // M2O
        if (fields[fieldName].type === "many2one" && fieldDescr.invisible !== true) {
            fieldsSpec[fieldName].fields = { display_name: {} };
        }
        if (["many2one", "one2many", "many2many"].includes(fields[fieldName].type)) {
            const context = getFieldContext(
                fieldName,
                activeFields,
                evalContext,
                parentActiveFields
            );
            if (context) {
                fieldsSpec[fieldName].context = context;
            }
        }
    }
    return fieldsSpec;
};

function _populateOnChangeSpec(activeFields, spec, path = false) {
    const prefix = path ? `${path}.` : "";
    for (const [fieldName, field] of Object.entries(activeFields)) {
        const key = `${prefix}${fieldName}`;
        spec[key] = field.onChange ? "1" : "";
        if (field.related) {
            _populateOnChangeSpec(field.related.activeFields, spec, key);
        }
    }
}
export const getOnChangeSpec = (activeFields) => {
    const spec = {};
    _populateOnChangeSpec(activeFields, spec);
    return spec;
};
