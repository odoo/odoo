/* @odoo-module */

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

export const getActiveFieldsFromArchInfo = (
    { fieldNodes, widgetNodes },
    fields,
    { isSmall } = {}
) => {
    const activeFields = {};
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
                let viewMode = fieldNode.viewMode;
                if (viewMode.split(",").length !== 1) {
                    viewMode = isSmall ? "kanban" : "list";
                }
                const viewDescr = fieldNode.views[viewMode];
                activeFields[fieldName].related = {
                    activeFields: getActiveFieldsFromArchInfo(viewDescr, viewDescr.fields, {
                        isSmall,
                    }),
                    fields: viewDescr.fields,
                };
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
    return activeFields;
};

export const getFieldsSpec = (activeFields, fields) => {
    console.log("getFieldsSpec");
    const fieldsSpec = {};
    for (const fieldName in activeFields) {
        const fieldDescr = activeFields[fieldName];
        fieldsSpec[fieldName] = {};
        // X2M
        if (fieldDescr.related) {
            fieldsSpec[fieldName].fields = getFieldsSpec(
                fieldDescr.related.activeFields,
                fieldDescr.related.fields
            );
            // fieldsSpec[fieldName].context = fieldDescr.context; // TODO: evaluate (without record)
        }
        // M2O
        if (fields[fieldName].type === "many2one") {
            fieldsSpec[fieldName].fields = { display_name: {} }; // TODO: not necessary if always invisible
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
