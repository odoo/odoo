/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

// TODO SEB move these to properties check

/**
 * @param {Object} param0
 * @param {Map} param0.fieldPropertyRegistry
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkRelationField({ fieldPropertyRegistry, Models, Model, field }) {
    checkExistenceOfTargetForRelationField({ Models, Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkExistenceOfTargetForRelationField({ Models, Model, field }) {
    if (!Models[field.to]) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `undefined target model "${field.to}"`,
            suggestion: `ensure the model name is given and targets an existing model, or check for typos in model name`,
        });
    }
}
