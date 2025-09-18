// @ts-check

/** @module @web/model/relational_model/field_metadata - ActiveField construction with visibility, readonly, and required modifiers */

/**
 * @param {boolean | string} value boolean or string encoding a python expression
 * @returns {string} string encoding a python expression
 */

import { omit } from "@web/core/utils/collections/objects";
function convertBoolToPyExpr(value) {
    if (value === true || value === false) {
        return value ? "True" : "False";
    }
    return value;
}

/**
 * @typedef {{
 *   context?: string;
 *   invisible?: boolean | string;
 *   readonly?: boolean | string;
 *   required?: boolean | string;
 *   onChange?: boolean | string;
 *   forceSave?: boolean;
 *   isHandle?: boolean;
 * }} ActiveFieldOptions
 */

/**
 * @param {ActiveFieldOptions} [options]
 * @returns {Object}
 */
export function makeActiveField({
    context,
    invisible,
    readonly,
    required,
    onChange,
    forceSave,
    isHandle,
} = {}) {
    return {
        context: context || "{}",
        invisible: convertBoolToPyExpr(invisible || false),
        readonly: convertBoolToPyExpr(readonly || false),
        required: convertBoolToPyExpr(required || false),
        onChange: onChange || false,
        forceSave: forceSave || false,
        isHandle: isHandle || false,
    };
}

export function addFieldDependencies(activeFields, fields, fieldDependencies = []) {
    for (const field of fieldDependencies) {
        if (!("readonly" in field)) {
            field.readonly = true;
        }
        if (field.name in activeFields) {
            patchActiveFields(activeFields[field.name], makeActiveField(field));
        } else {
            activeFields[field.name] = makeActiveField(field);
            if (["one2many", "many2many"].includes(field.type)) {
                activeFields[field.name].related = {
                    activeFields: {},
                    fields: {},
                };
            }
        }
        if (!fields[field.name]) {
            const newField = omit(
                field,
                "context",
                "invisible",
                "required",
                "readonly",
                "onChange",
            );
            fields[field.name] = newField;
            if (newField.type === "selection" && !Array.isArray(newField.selection)) {
                newField.selection = [];
            }
        }
    }
}

function completeActiveField(activeField, extra) {
    if (extra.related) {
        for (const fieldName in extra.related.activeFields) {
            if (fieldName in activeField.related.activeFields) {
                completeActiveField(
                    activeField.related.activeFields[fieldName],
                    extra.related.activeFields[fieldName],
                );
            } else {
                activeField.related.activeFields[fieldName] = {
                    ...extra.related.activeFields[fieldName],
                };
            }
        }
        Object.assign(activeField.related.fields, extra.related.fields);
    }
}

export function completeActiveFields(activeFields, extraActiveFields) {
    for (const fieldName in extraActiveFields) {
        const extraActiveField = {
            ...extraActiveFields[fieldName],
            invisible: "True",
        };
        if (fieldName in activeFields) {
            completeActiveField(activeFields[fieldName], extraActiveField);
        } else {
            activeFields[fieldName] = extraActiveField;
        }
    }
}

export function createPropertyActiveField(property) {
    const { type } = property;

    const activeField = makeActiveField();
    if (type === "one2many" || type === "many2many") {
        activeField.related = {
            fields: {
                id: { name: "id", type: "integer" },
                display_name: { name: "display_name", type: "char" },
            },
            activeFields: {
                id: makeActiveField({ readonly: true }),
                display_name: makeActiveField(),
            },
        };
    }
    return activeField;
}

export function combineModifiers(mod1, mod2, operator) {
    if (operator === "AND") {
        if (!mod1 || mod1 === "False" || !mod2 || mod2 === "False") {
            return "False";
        }
        if (mod1 === "True") {
            return mod2;
        }
        if (mod2 === "True") {
            return mod1;
        }
        return `(${mod1}) and (${mod2})`;
    } else if (operator === "OR") {
        if (mod1 === "True" || mod2 === "True") {
            return "True";
        }
        if (!mod1 || mod1 === "False") {
            return mod2;
        }
        if (!mod2 || mod2 === "False") {
            return mod1;
        }
        return `(${mod1}) or (${mod2})`;
    }
    throw new Error(
        `Operator provided to "combineModifiers" must be "AND" or "OR", received ${operator}`,
    );
}

export function patchActiveFields(activeField, patch) {
    activeField.invisible = combineModifiers(
        activeField.invisible,
        patch.invisible,
        "AND",
    );
    activeField.readonly = combineModifiers(
        activeField.readonly,
        patch.readonly,
        "AND",
    );
    activeField.required = combineModifiers(activeField.required, patch.required, "OR");
    activeField.onChange = activeField.onChange || patch.onChange;
    activeField.forceSave = activeField.forceSave || patch.forceSave;
    activeField.isHandle = activeField.isHandle || patch.isHandle;
    // x2manys
    if (patch.related) {
        const related = activeField.related;
        for (const fieldName in patch.related.activeFields) {
            if (fieldName in related.activeFields) {
                patchActiveFields(
                    related.activeFields[fieldName],
                    patch.related.activeFields[fieldName],
                );
            } else {
                related.activeFields[fieldName] = {
                    ...patch.related.activeFields[fieldName],
                };
            }
        }
        Object.assign(related.fields, patch.related.fields);
    }
    if ("limit" in patch) {
        activeField.limit = patch.limit;
    }
    if (patch.defaultOrderBy) {
        activeField.defaultOrderBy = patch.defaultOrderBy;
    }
}

export function extractFieldsFromArchInfo({ fieldNodes, widgetNodes }, fields) {
    const activeFields = {};
    for (const fieldNode of Object.values(fieldNodes)) {
        const fieldName = fieldNode.name;
        const activeField = makeActiveField({
            context: fieldNode.context,
            invisible: combineModifiers(
                fieldNode.invisible,
                fieldNode.column_invisible,
                "OR",
            ),
            readonly: fieldNode.readonly,
            required: fieldNode.required,
            onChange: fieldNode.onChange,
            forceSave: fieldNode.forceSave,
            isHandle: fieldNode.isHandle,
        });
        if (["one2many", "many2many"].includes(fields[fieldName].type)) {
            activeField.related = {
                activeFields: {},
                fields: {},
            };
            if (fieldNode.views) {
                const viewDescr = fieldNode.views[fieldNode.viewMode];
                if (viewDescr) {
                    activeField.related = extractFieldsFromArchInfo(
                        viewDescr,
                        viewDescr.fields,
                    );
                    activeField.limit = viewDescr.limit;
                    activeField.defaultOrderBy = viewDescr.defaultOrder;
                    if (fieldNode.views.form) {
                        // we already know the form view (it is inline), so add its fields (in invisible)
                        // s.t. they will be sent in the spec for onchange, and create commands returned
                        // by the onchange could return values for those fields (that would be displayed
                        // later if the user opens the form view)
                        const formArchInfo = extractFieldsFromArchInfo(
                            fieldNode.views.form,
                            fieldNode.views.form.fields,
                        );
                        completeActiveFields(
                            activeField.related.activeFields,
                            formArchInfo.activeFields,
                        );
                        Object.assign(activeField.related.fields, formArchInfo.fields);
                    }

                    if (fieldNode.viewMode !== "default" && fieldNode.views.default) {
                        const defaultArchInfo = extractFieldsFromArchInfo(
                            fieldNode.views.default,
                            fieldNode.views.default.fields,
                        );
                        for (const fieldName in defaultArchInfo.activeFields) {
                            if (fieldName in activeField.related.activeFields) {
                                patchActiveFields(
                                    activeField.related.activeFields[fieldName],
                                    defaultArchInfo.activeFields[fieldName],
                                );
                            } else {
                                activeField.related.activeFields[fieldName] = {
                                    ...defaultArchInfo.activeFields[fieldName],
                                };
                            }
                        }
                        activeField.related.fields = Object.assign(
                            {},
                            defaultArchInfo.fields,
                            activeField.related.fields,
                        );
                    }
                }
            }
            if (fieldNode.field?.useSubView) {
                activeField.required = "False";
            }
        }
        if (
            ["many2one", "many2one_reference"].includes(fields[fieldName].type) &&
            fieldNode.views
        ) {
            const viewDescr = fieldNode.views.default;
            activeField.related = extractFieldsFromArchInfo(
                viewDescr,
                viewDescr.fields,
            );
        }

        if (fieldName in activeFields) {
            patchActiveFields(activeFields[fieldName], activeField);
        } else {
            activeFields[fieldName] = activeField;
        }

        if (fieldNode.field) {
            let fieldDependencies = fieldNode.field.fieldDependencies;
            if (typeof fieldDependencies === "function") {
                fieldDependencies = fieldDependencies(fieldNode);
            }
            addFieldDependencies(activeFields, fields, fieldDependencies);
        }
    }

    for (const widgetInfo of Object.values(widgetNodes || {})) {
        let fieldDependencies = widgetInfo.widget.fieldDependencies;
        if (typeof fieldDependencies === "function") {
            fieldDependencies = fieldDependencies(widgetInfo);
        }
        addFieldDependencies(activeFields, fields, fieldDependencies);
    }
    return { activeFields, fields };
}
