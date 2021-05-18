/** @odoo-module **/

import { checkFieldType } from '@mail/model/fields/check_field_type';

/**
 * This module provides an utility function to check the consistency of model
 * fields as they are declared. These checks allow early detection of developer
 * mistakes when writing model fields.
 */

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Map} param0.fieldTypeRegistry
 * @throws {InvalidFieldError} in case some declared fields are not correct.
 */
export function checkDeclaredFieldsOnModels({ Models, fieldTypeRegistry }) {
    for (const Model of Object.values(Models)) {
        for (const field of Object.values(Model.fields)) {
            checkDeclaredFieldOnModel({ Models, fieldTypeRegistry, Model, field });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Map} param0.fieldTypeRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkDeclaredFieldOnModel({ Models, fieldTypeRegistry, Model, field }) {
    checkFieldType({ fieldTypeRegistry, Model, field });
    const fieldType = fieldTypeRegistry.get(field.fieldType);
    fieldType.checkDeclaration({ fieldPropertyRegistry: fieldType.fieldPropertyRegistry, Models, Model, field });
    for (const property of fieldType.fieldPropertyRegistry.values()) {
        property.checkDeclaration({ fieldTypeRegistry, Models, Model, field });
        // TODO SEB check excludedProperties
        // TODO SEB check isRequired
        // TODO SEB check requiredProperties
    }
}
