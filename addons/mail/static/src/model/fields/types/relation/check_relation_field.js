/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Map} param0.fieldPropertyRegistry
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkRelationField({ fieldPropertyRegistry, Models, Model, field }) {
    checkSupportedPropertiesOnRelationField({ fieldPropertyRegistry, Model, field });
    checkExistenceOfTargetForRelationField({ Models, Model, field });
    if (field.isCausal) {
        checkSupportedRelationTypeForIsCausalProperty({ Model, field });
    }
    if (field.required) {
        checkSupportedRelationTypeForRequiredProperty({ Model, field });
    }
}

/**
 * @param {Object} param0
 * @param {Map} param0.fieldPropertyRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkSupportedPropertiesOnRelationField({ fieldPropertyRegistry, Model, field }) {
    for (const property of Object.keys(field)) {
        if (!fieldPropertyRegistry.has(property)) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `unsupported property "${property}" for field of type "relation"`,
                suggestion: `don't use an unsupported property, or check for typos in property name`,
            });
        }
    }
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
            fieldName: field.fieldName,
            error: `undefined target model "${field.to}"`,
            suggestion: `ensure the model name is given and targets an existing model, or check for typos in model name`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkSupportedRelationTypeForIsCausalProperty({ Model, field }) {
    const supportedRelationTypes = new Set(['one2many', 'one2one']);
    if (!supportedRelationTypes.has(field.relationType)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported "isCausal" property for relation of type "${field.relationType}"`,
            suggestion: `do not use "isCausal" on relations that are many2x`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkSupportedRelationTypeForRequiredProperty({ Model, field }) {
    const supportedRelationTypes = new Set(['many2one', 'one2one']);
    if (!supportedRelationTypes.has(field.relationType)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported "required" property for relation of type "${field.relationType}"`,
            suggestion: `do not use "required" on relations that are x2many`,
        });
    }
}
