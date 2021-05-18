/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Map<string, Object>} param0.fieldTypeRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkFieldType({ fieldTypeRegistry, Model, field }) {
    if (!fieldTypeRegistry.has(field.fieldType)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported field type "${field.fieldType}"`,
            suggestion: `check for syntax error or remove "fieldType" property, field type should normally not be provided directly anyway. Registered field types: ${[...fieldTypeRegistry.keys()].join(', ')}`,
        });
    }
}
