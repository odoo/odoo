/* @odoo-module */

export const addFieldDependencies = (activeFields, fieldDependencies = []) => {
    for (const field of fieldDependencies) {
        if (!activeFields[field.name]) {
            activeFields[field.name] = {
                context: "{}",
                readonly: false,
                required: false,
                onChange: false,
            };
        }
    }
};

export const getActiveFieldsFromArchInfo = ({ fieldNodes, widgetNodes }, { isSmall } = {}) => {
    const activeFields = {};
    for (const fieldNode of Object.values(fieldNodes)) {
        const fieldName = fieldNode.name;
        const modifiers = fieldNode.modifiers || {};
        if (!(fieldName in activeFields)) {
            activeFields[fieldName] = {
                context: fieldNode.context || "{}",
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
                    activeFields: getActiveFieldsFromArchInfo(viewDescr, {
                        isSmall,
                    }),
                    fields: viewDescr.fields,
                };
            }
        } else {
            // TODO (see task description for multiple occurrences of fields)
        }
        if (fieldNode.FieldComponent) {
            addFieldDependencies(activeFields, fieldNode.field.fieldDependencies);
        }
    }
    for (const widgetInfo of Object.values(widgetNodes || {})) {
        addFieldDependencies(activeFields, widgetInfo.widget.fieldDependencies);
    }
    return activeFields;
};

export const getFieldsSpec = (activeFields, fields) => {
    console.log("getFieldsSpec");
    const fieldsSpec = {};
    for (const fieldName in activeFields) {
        const fieldDescr = activeFields[fieldName];
        // X2M
        if (fieldDescr.related) {
            fieldsSpec[fieldName] = {
                ...getFieldsSpec(fieldDescr.related.activeFields),
                __context: fieldDescr.context,
            };
            continue;
        }
        // all other cases
        fieldsSpec[fieldName] = 1;
    }
    return fieldsSpec;
};
