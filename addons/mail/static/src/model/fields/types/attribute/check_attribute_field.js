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
export function checkAttributeField({ fieldPropertyRegistry, Models, Model, field }) {
    checkSupportedPropertiesOnAttributeField({ fieldPropertyRegistry, Model, field });
}

/**
 * @param {Object} param0
 * @param {Map} param0.fieldPropertyRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkSupportedPropertiesOnAttributeField({ fieldPropertyRegistry, Model, field }) {
    for (const property of Object.keys(field)) {
        if (!fieldPropertyRegistry.has(property)) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `unsupported property "${property}" for field of type "attribute"`,
                suggestion: `don't use an unsupported property, or check for typos in property name`,
            });
        }
    }
}
