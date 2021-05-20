/** @odoo-module **/

import { getMatchingFieldsDefinitionFromParents } from '@mail/model/fields/get_matching_fields_definition_from_parents';
import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * This module provides an utility function to check the consistency of model
 * fields as they are declared. These checks allow early detection of developer
 * mistakes when writing model fields.
 */

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @throws {InvalidFieldError} in case some declared fields are not correct.
 */
export function checkDeclaredModels({ env, Models }) {
    for (const Model of Object.values(Models)) {
        checkDeclaredModel({ env, Models, Model });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @throws {InvalidFieldError} in case some declared fields are not correct.
 */
function checkDeclaredModel({ env, Models, Model }) {
    checkDeclaredFields({ env, Models, Model });
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @throws {InvalidFieldError} in case some declared fields are not correct.
 */
function checkDeclaredFields({ env, Models, Model }) {
    for (const fieldDefinition of Object.values(Model.fields)) {
        checkDeclaredField({ Models, env, Model, fieldDefinition });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.fieldDefinition field being currently checked
 * @throws {InvalidFieldError}
 */
function checkDeclaredField({ env, Models, Model, fieldDefinition }) {
    checkFieldType({ env, Model, fieldDefinition });
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    if (fieldType.get('nameOfRequiredProperties')) {
        checkPresenceOfRequiredProperties({ env, Model, fieldDefinition });
    }
    checkDeclaredProperties({ env, fieldDefinition, Models, Model });
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.fieldDefinition field being currently checked
 * @throws {InvalidFieldError}
 */
function checkFieldType({ env, Model, fieldDefinition }) {
    if (!env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `unsupported field type "${fieldDefinition.fieldType}"`,
            suggestion: `use a registered field type, or check for typos. Registered field types: ${[...env.modelManager.fieldTypeRegistry.keys()].join(', ')}`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.fieldDefinition field being currently checked
 * @throws {InvalidFieldError}
 */
function checkPresenceOfRequiredProperties({ env, Model, fieldDefinition }) {
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    for (const nameOfRequiredProperty of fieldType.get('nameOfRequiredProperties')) {
        if (!fieldDefinition.properties[nameOfRequiredProperty]) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: fieldDefinition.properties.fieldName,
                error: `missing required property "${nameOfRequiredProperty}" for field of type "${fieldDefinition.fieldType}"`,
                suggestion: `add the missing property, or check for typos in its name, or change field type to one that supports this property`,
            });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @throws {InvalidFieldError}
 */
function checkDeclaredProperties({ fieldDefinition, env, Models, Model }) {
    for (const propertyName of Object.keys(fieldDefinition.properties)) {
        const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
        if (fieldType.get('nameOfAvailableProperties')) {
            checkAvailabilityOfProperty({ env, fieldDefinition, Model, propertyName });
        }
        checkDeclaredProperty({ fieldDefinition, env, Models, Model, propertyName });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName property being currently checked
 * @throws {InvalidFieldError}
 */
function checkAvailabilityOfProperty({ env, fieldDefinition, Model, propertyName }) {
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    if (!fieldType.get('nameOfAvailableProperties').has(propertyName)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `unsupported property "${propertyName}" for field of type "${fieldDefinition.fieldType}"`,
            suggestion: `don't use an unsupported property, or check for typos in property name. Supported properties: ${[...fieldType.get('nameOfAvailableProperties')].join(', ')}.`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkDeclaredProperty({ env, fieldDefinition, Models, Model, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    if (propertyDefinition.get('requiredProperties')) {
        checkPresenceOfSiblingProperties({ env, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('excludedProperties')) {
        checkAbsenceOfSiblingProperties({ env, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isInstanceMethodName')) {
        checkPropertyIsInstanceMethodName({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isModelName')) {
    // TODO SEB check
    }
    if (propertyDefinition.get('isArray')) {
        checkPropertyIsArray({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isArrayOfFieldNames')) {
        checkPropertyIsArrayOfFieldNames({ Models, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isFieldName')) {
        checkPropertyIsFieldName({ Models, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isString')) {
        checkPropertyIsString({ fieldDefinition, Model, propertyName });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPresenceOfSiblingProperties({ env, fieldDefinition, Model, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    for (const requiredPropertyName of propertyDefinition.get('requiredProperties')) {
        const nameOfPossibleProperties = (requiredPropertyName instanceof Set)
            ? [...requiredPropertyName]
            : [requiredPropertyName];
        if (!nameOfPossibleProperties.some(propertyName => fieldDefinition.properties[propertyName])) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: fieldDefinition.properties.fieldName,
                error: `one property of "${nameOfPossibleProperties.join(', ')}" must be used together with property "${propertyName}"`,
                suggestion: `add the missing property, or check for typos in its name, or remove the current property`,
            });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkAbsenceOfSiblingProperties({ env, fieldDefinition, Model, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    for (const excludedPropertyName of propertyDefinition.get('excludedProperties')) {
        if (fieldDefinition.properties[excludedPropertyName]) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: fieldDefinition.properties.fieldName,
                error: `property "${excludedPropertyName}" cannot be used together with property "${propertyName}"`,
                suggestion: `remove one of the incompatible properties`,
            });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPropertyIsArray({ fieldDefinition, Model, propertyName }) {
    if (!Array.isArray(fieldDefinition.properties[propertyName])) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `type of "${propertyName}" property should be array instead of "${typeof fieldDefinition.properties[propertyName]}"`,
            suggestion: `check for syntax error`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPropertyIsArrayOfFieldNames({ Models, fieldDefinition, Model, propertyName }) {
    for (const fieldName of fieldDefinition.properties[propertyName]) {
        const fields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName });
        if (fields.size === 0) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: fieldDefinition.properties.fieldName,
                error: `element "${fieldName}" from "${propertyName}" array does not target a field of current model`,
                suggestion: `ensure only field names of current model are provided`,
            });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPropertyIsFieldName({ Models, fieldDefinition, Model, propertyName }) {
    const fieldName = fieldDefinition.properties[propertyName];
    const fields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName });
    if (fields.size === 0) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `"${fieldName}" from "${propertyName}" does not target a field of current model`,
            suggestion: `ensure a field name of current model is provided`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPropertyIsString({ fieldDefinition, Model, propertyName }) {
    if (typeof fieldDefinition.properties[propertyName] !== 'string') {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `type of "${propertyName}" property should be string instead of "${typeof fieldDefinition.properties[propertyName]}"`,
            suggestion: `check for syntax error`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {InvalidFieldError}
 */
function checkPropertyIsInstanceMethodName({ fieldDefinition, Model, propertyName }) {
    if (!(Model.prototype[fieldDefinition.properties[propertyName]])) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: fieldDefinition.properties.fieldName,
            error: `"${propertyName}" property "${fieldDefinition.properties[propertyName]}" targets to unknown method`,
            suggestion: `ensure the name of an instance method of this model is given, and check for typos`,
        });
    }
}
