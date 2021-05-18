/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkComputeProperty({ Model, field }) {
    checkComputePropertyIsString({ Model, field });
    checkExistenceOfMethodForComputeProperty({ Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkComputePropertyIsString({ Model, field }) {
    if (!(typeof field.compute === 'string')) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported type of "compute" property "${field.compute}"`,
            suggestion: `compute value must be a string (the name of an instance method)`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkExistenceOfMethodForComputeProperty({ Model, field }) {
    if (!(Model.prototype[field.compute])) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `"compute" property "${field.compute}" targets to unknown method`,
            suggestion: `ensure the name of an instance method of this model is given, and check for typos`,
        });
    }
}
