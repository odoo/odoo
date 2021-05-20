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
    for (const [modelName, Model] of Object.entries(Models)) {
        try {
            checkDeclaredModel({ env, Models, Model });
        } catch (error) {
            error.message = `Invalid model "${modelName}": ${error.message}`;
            throw error;
        }
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
    for (const [fieldName, fieldDefinition] of Object.entries(Model.fields)) {
        try {
            checkDeclaredField({ Models, env, Model, fieldDefinition });
        } catch (error) {
            error.message = `Invalid field "${fieldName}": ${error.message}`;
            throw error;
        }
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
        try {
            checkDeclaredProperty({ fieldDefinition, env, Models, Model, propertyName });
        } catch (error) {
            error.message = `Invalid property "${propertyName}": ${error.message}`;
            throw error;
        }
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
    if (propertyDefinition.get('isString')) {
        checkPropertyIsString({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isArray')) {
        checkPropertyIsArray({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isArrayOfFieldNames')) {
        checkPropertyIsArrayOfFieldNames({ Models, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isInstanceMethodName')) {
        checkPropertyIsInstanceMethodName({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isModelName')) {
        checkPropertyIsModelName({ fieldDefinition, Models, Model, propertyName });
    }
    if (propertyDefinition.get('isFieldName')) {
        checkPropertyIsFieldName({ Models, fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isStringWithTwoPartsSeparatedByDot')) {
        checkPropertyIsStringWithTwoPartsSeparatedByDot({ fieldDefinition, Model, propertyName });
    }
    if (propertyDefinition.get('isRelationNameDotFieldName')) {
        checkPropertyIsRelationNameDotFieldName({ fieldDefinition, Models, Model, propertyName });
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
            error: `"${fieldName}" from "${propertyName}" does not target a field of current model`,
            suggestion: `ensure a field name of current model is provided`,
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
function checkPropertyIsModelName({ Models, fieldDefinition, Model, propertyName }) {
    const modelName = fieldDefinition.properties[propertyName];
    if (!Models[modelName]) {
        throw new InvalidFieldError({
            error: `undefined target model "${modelName}" from "${propertyName}"`,
            suggestion: `ensure the model name is given and targets an existing model, or check for typos in model name`,
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
            error: `"${propertyName}" property "${fieldDefinition.properties[propertyName]}" targets to unknown method`,
            suggestion: `ensure the name of an instance method of this model is given, and check for typos`,
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
function checkPropertyIsStringWithTwoPartsSeparatedByDot({ fieldDefinition, Model, propertyName }) {
    const [part1, part2, part3] = fieldDefinition.properties[propertyName].split('.');
    if (!part1 || !part2 || part3) {
        throw new InvalidFieldError({
            error: `value of "${propertyName}" property should be a 2 parts string separared by a single dot instead of "${fieldDefinition.properties[propertyName]}"`,
            suggestion: `follow the expected format, or check for typos`,
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
function checkPropertyIsRelationNameDotFieldName({ fieldDefinition, Models, Model, propertyName }) {
    const [relationName, relatedName] = fieldDefinition.properties[propertyName].split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    if (relationFields.size === 0) {
        throw new InvalidFieldError({
            error: `undefined relation "${relationName}"`,
            suggestion: `target a field on the current model, or check for typos`,
        });
    }
    for (const relationField of relationFields) {
        if (!relationField.properties.to) {
            throw new InvalidFieldError({
                error: `invalid field type of relation "${relationName}"`,
                suggestion: `target a relation field`,
            });
        }
    }
    const relatedModelName = [...relationFields].find(relationField => relationField.properties.to).properties.to;
    const relatedFields = getMatchingFieldsDefinitionFromParents({ Models, Model: Models[relatedModelName], fieldName: relatedName });
    if (relatedFields.size === 0) {
        throw new InvalidFieldError({
            error: `unsupported related field "${relatedName}"`,
            suggestion: `target a field on the relation model, or check for typos`,
        });
    }
    for (const relatedField of relatedFields) {
        // TODO SEB change this to a list of properties that must match between related
        if (relatedField.properties.to !== fieldDefinition.properties.to) {
            throw new InvalidFieldError({
                error: `related field "${relatedModelName}/${relatedField.properties.fieldName}" has mismatch type`,
                suggestion: `change the type of either the related field or the target field`,
            });
        }
    }
}
