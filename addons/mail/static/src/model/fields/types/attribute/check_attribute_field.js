/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkAttributeField({ Models, Model, field }) {
    checkSupportedPropertiesOnAttributeField({ Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkSupportedPropertiesOnAttributeField({ Model, field }) {
    const supportedProperties = new Set([
        'compute',
        'default',
        'dependencies',
        'fieldName',
        'fieldType',
        'isOnChange',
        'readonly',
        'related',
        'required',
    ]);
    for (const property of Object.keys(field)) {
        if (!supportedProperties.has(property)) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `unsupported property "${property}" for field of type "attribute"`,
                suggestion: `don't use an unsupported property, or check for typos in property name`,
            });
        }
    }
}
