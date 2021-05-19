/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkFieldNameProperty({ Model, field }) {
    checkPresenceOfFieldInModel({ Model, field });
    checkMatchingFieldOnModel({ Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkPresenceOfFieldInModel({ Model, field }) {
    if (!Model.fields[field.properties.fieldName]) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `field name not present in model`,
            suggestion: `this is likely a bug in model manager, not in your code`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkMatchingFieldOnModel({ Model, field }) {
    if (Model.fields[field.properties.fieldName] !== field) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `field on model not matching given field`,
            suggestion: `this is likely a bug in model manager, not in your code`,
        });
    }
}
