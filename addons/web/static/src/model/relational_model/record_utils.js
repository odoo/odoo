// @ts-check

/** @module @web/model/relational_model/record_utils - Pure utility functions for field attribute evaluation (invisible, readonly, required) */

/**
 * Pure utility functions extracted from Record.
 *
 * These functions encapsulate domain logic that was previously embedded
 * in Record methods but has zero dependency on OWL reactivity (no reactive,
 * markRaw, toRaw, or Component imports). They can be tested with plain
 * assert in <1ms without any browser or framework setup.
 *
 * @see record_value_transforms.js for value formatting and context building
 * @see record_validator.js for field validation logic
 */

import { evaluateBooleanExpr } from "@web/core/py_js/py";

import { formatServerValue } from "./record_value_transforms";
// ---------------------------------------------------------------------------
// Field attribute evaluation
// ---------------------------------------------------------------------------

/**
 * Evaluate a field attribute expression (invisible, readonly, required).
 *
 * This is the pure core of Record._isInvisible, _isReadonly, _isRequired.
 * Given a Python boolean expression string and an eval context, returns
 * whether the expression evaluates to true.
 *
 * @param {string|false} expr - Python boolean expression (e.g. "state == 'done'")
 * @param {Object} evalContext - record data context for expression evaluation
 * @returns {boolean}
 */
export function evaluateFieldAttr(expr, evalContext) {
    return expr ? evaluateBooleanExpr(expr, evalContext) : false;
}

/**
 * Check if a field is invisible given its active field definition and eval context.
 *
 * @param {Object} activeField - the activeFields[fieldName] entry
 * @param {Object} evalContext
 * @returns {boolean}
 */
export function isFieldInvisible(activeField, evalContext) {
    return evaluateFieldAttr(activeField.invisible, evalContext);
}

/**
 * Check if a field is readonly given its active field definition and eval context.
 *
 * @param {Object} activeField - the activeFields[fieldName] entry
 * @param {Object} evalContext
 * @returns {boolean}
 */
export function isFieldReadonly(activeField, evalContext) {
    return evaluateFieldAttr(activeField.readonly, evalContext);
}

/**
 * Check if a field is required given its active field definition and eval context.
 *
 * @param {Object} activeField - the activeFields[fieldName] entry
 * @param {Object} evalContext
 * @returns {boolean}
 */
export function isFieldRequired(activeField, evalContext) {
    return evaluateFieldAttr(activeField.required, evalContext);
}

// ---------------------------------------------------------------------------
// Changeset computation
// ---------------------------------------------------------------------------

/**
 * Compute the minimal changeset to send to the server from pending changes.
 *
 * This is the pure core of Record._getChanges. It determines which fields
 * have changed, skips readonly fields (unless forceSave), skips property
 * fields, and formats values for the server.
 *
 * For x2many fields, the caller must provide a `getCommands` callback that
 * retrieves the ORM command list from the StaticList datapoint.
 *
 * @param {Object} params
 * @param {Object} params.changes - pending field changes (Record._changes)
 * @param {Object} params.values - server-confirmed values (Record._values)
 * @param {boolean} params.isNew - whether the record has no resId
 * @param {Object} params.fields - field definitions
 * @param {Object} params.activeFields - active field metadata
 * @param {Object} params.evalContext - for evaluating readonly expressions
 * @param {Object} [params.options]
 * @param {boolean} [params.options.withReadonly] - include readonly fields
 * @param {(fieldName: string, value: any, withReadonly: boolean) => any[]} params.getCommands
 *     Callback to get ORM commands for x2many fields.
 * @returns {Object} changeset keyed by field name, values in server format
 */
export function computeChangeset({
    changes,
    values,
    isNew,
    fields,
    activeFields,
    evalContext,
    options = {},
    getCommands,
}) {
    const { withReadonly = false } = options;
    const effectiveChanges = isNew ? { ...values, ...changes } : changes;

    /** @type {Record<string, any>} */
    const result = {};

    for (const [fieldName, value] of Object.entries(effectiveChanges)) {
        const field = fields[fieldName];

        // Skip the id pseudo-field
        if (fieldName === "id") {
            continue;
        }

        // Skip readonly fields unless explicitly requested or forceSave is set
        if (
            !withReadonly &&
            fieldName in activeFields &&
            isFieldReadonly(activeFields[fieldName], evalContext) &&
            !activeFields[fieldName].forceSave
        ) {
            continue;
        }

        // Skip computed property fields (handled by their parent)
        if (field.relatedPropertyField) {
            continue;
        }

        // x2many fields: delegate to command builder
        if (field.type === "one2many" || field.type === "many2many") {
            const commands = getCommands(fieldName, value, withReadonly);
            if (!isNew && !commands.length && !withReadonly) {
                continue;
            }
            result[fieldName] = commands;
        } else {
            result[fieldName] = formatServerValue(field.type, value);
        }
    }

    return result;
}
