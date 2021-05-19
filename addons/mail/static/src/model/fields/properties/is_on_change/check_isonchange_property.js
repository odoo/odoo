/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkIsOnChangeProperty({ Model, field }) {
    if (!field.isOnChange) {
        return;
    }
    checkIsOnChangePropetyGoesWithComputeProperty({ Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkIsOnChangePropetyGoesWithComputeProperty({ Model, field }) {
    if (!field.compute) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `unsupported "isOnChange" property on field without the "compute" property`,
            suggestion: `either remove the "isOnChange" property or add the "compute" property`,
        });
    }
}
