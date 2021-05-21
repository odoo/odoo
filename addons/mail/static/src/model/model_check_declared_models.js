/** @odoo-module **/

import { getMatchingFieldsDefinitionFromParents } from '@mail/model/fields/get_matching_fields_definition_from_parents';

/**
 * This module provides an utility function to check the consistency of models
 * that are registered. These checks allow early detection of developer mistakes
 * when writing models.
 */

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @throws {Error} in case some declared fields are not correct.
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
 * @throws {Error}
 */
function checkDeclaredModel({ env, Models, Model }) {
    checkDeclaredFields({ env, Models, Model });
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @throws {Error}
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
 * @throws {Error}
 */
function checkDeclaredField({ env, Models, Model, fieldDefinition }) {
    checkTypeIsRegistered({ env, nameOfType: fieldDefinition.fieldType });
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    if (fieldType.get('nameOfRequiredProperties')) {
        checkPresenceOfRequiredProperties({ env, fieldDefinition });
    }
    checkDeclaredProperties({ env, fieldDefinition, Models, Model });
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {string} param0.nameOfType
 * @throws {Error}
 */
function checkTypeIsRegistered({ env, nameOfType }) {
    if (!env.modelManager.fieldTypeRegistry.get(nameOfType)) {
        throw new Error(`Undefined type "${nameOfType}". Use a registered type, or check for typos.`);
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @throws {Error}
 */
function checkPresenceOfRequiredProperties({ env, fieldDefinition }) {
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    for (const nameOfRequiredProperty of fieldType.get('nameOfRequiredProperties')) {
        if (!fieldDefinition.properties[nameOfRequiredProperty]) {
            throw new Error(`Missing required property "${nameOfRequiredProperty}". Add the missing property, or check for typos, or change field type to one that supports this property.`);
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @throws {Error}
 */
function checkDeclaredProperties({ fieldDefinition, env, Models, Model }) {
    for (const propertyName of Object.keys(fieldDefinition.properties)) {
        if (!env.modelManager.fieldPropertyRegistry.get(propertyName)) {
            throw new Error(`Undefined property "${propertyName}". Use a registered property, or check for typos.`);
        }
        const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
        if (fieldType.get('nameOfAvailableProperties')) {
            checkAvailabilityOfProperty({ env, fieldDefinition, propertyName });
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
 * @param {string} param0.propertyName property being currently checked
 * @throws {Error}
 */
function checkAvailabilityOfProperty({ env, fieldDefinition, propertyName }) {
    const fieldType = env.modelManager.fieldTypeRegistry.get(fieldDefinition.fieldType);
    if (!fieldType.get('nameOfAvailableProperties').has(propertyName)) {
        throw new Error(`Unsupported property "${propertyName}". Don't use an unsupported property, or change field type to one that supports this property.`);
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {Error}
 */
function checkDeclaredProperty({ env, fieldDefinition, Models, Model, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    const propertyValue = fieldDefinition.properties[propertyName];
    if (propertyDefinition.get('requiredProperties')) {
        checkPresenceOfSiblingProperties({ env, fieldDefinition, propertyName });
    }
    if (propertyDefinition.get('excludedProperties')) {
        checkAbsenceOfSiblingProperties({ env, fieldDefinition, propertyName });
    }
    if (propertyDefinition.get('isArray')) {
        checkPropertyIsArray({ propertyValue });
    }
    if (propertyDefinition.get('isArrayOfFieldNames')) {
        checkPropertyIsArrayOfFieldNames({ Models, Model, propertyValue });
    }
    if (propertyDefinition.get('isBoolean')) {
        checkPropertyIsBoolean({ propertyValue });
    }
    if (propertyDefinition.get('isString')) {
        checkPropertyIsString({ propertyValue });
    }
    if (propertyDefinition.get('isInstanceMethodName')) {
        checkPropertyIsInstanceMethodName({ Model, propertyValue });
    }
    if (propertyDefinition.get('isModelName')) {
        checkPropertyIsModelName({ Models, propertyValue });
    }
    if (propertyDefinition.get('isStringWithTwoPartsSeparatedByDot')) {
        checkPropertyIsStringWithTwoPartsSeparatedByDot({ propertyValue });
    }
    if (propertyDefinition.get('isRelationNameDotFieldName')) {
        checkPropertyIsRelationNameDotFieldName({ fieldDefinition, Models, Model, propertyValue });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {Error}
 */
function checkPresenceOfSiblingProperties({ env, fieldDefinition, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    for (const requiredPropertyName of propertyDefinition.get('requiredProperties')) {
        const nameOfPossibleProperties = (requiredPropertyName instanceof Set)
            ? [...requiredPropertyName]
            : [requiredPropertyName];
        if (!nameOfPossibleProperties.some(name => fieldDefinition.properties[name])) {
            if (nameOfPossibleProperties.length === 1) {
                throw new Error(`Property "${nameOfPossibleProperties[0]}" is required together with the current property. Add the missing property, or check for typos in its name, or remove the current property.`);
            }
            throw new Error(`One property of "${nameOfPossibleProperties.join(', ')}" must be used together with property "${propertyName}". Add the missing property, or check for typos in its name, or remove the current property.`);
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.env
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {string} param0.propertyName name of the property being currently checked
 * @throws {Error}
 */
function checkAbsenceOfSiblingProperties({ env, fieldDefinition, propertyName }) {
    const propertyDefinition = env.modelManager.fieldPropertyRegistry.get(propertyName);
    for (const excludedPropertyName of propertyDefinition.get('excludedProperties')) {
        if (fieldDefinition.properties[excludedPropertyName]) {
            throw new Error(`Property "${excludedPropertyName}" cannot be used together with the current property. Remove one of the incompatible properties.`);
        }
    }
}

/**
 * @param {Object} param0
 * @param {any} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsArray({ propertyValue }) {
    if (!Array.isArray(propertyValue)) {
        throw new Error(`Value "${propertyValue}" should be Array. Check for syntax error.`);
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {any} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsArrayOfFieldNames({ Models, Model, propertyValue }) {
    for (const fieldName of propertyValue) {
        const fields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName });
        if (fields.size === 0) {
            throw new Error(`Element of value "${fieldName}" does not target a field of current model. Ensure only field names of current model are provided, or check for typos.`);
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {string} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsModelName({ Models, propertyValue }) {
    if (!Models[propertyValue]) {
        throw new Error(`Value "${propertyValue}" does not target a model name. Target a registered model, or check for typos.`);
    }
}

/**
 * @param {Object} param0
 * @param {any} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsBoolean({ propertyValue }) {
    if (typeof propertyValue !== 'boolean') {
        throw new Error(`Value "${propertyValue}" should be boolean. Check for syntax error.`);
    }
}

/**
 * @param {Object} param0
 * @param {any} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsString({ propertyValue }) {
    if (typeof propertyValue !== 'string') {
        throw new Error(`Value "${propertyValue}" should be string. Check for syntax error.`);
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsInstanceMethodName({ Model, propertyValue }) {
    if (!(Model.prototype[propertyValue])) {
        throw new Error(`Value "${propertyValue}" targets to unknown method. Ensure the name of an instance method of this model is given, or check for typos.`);
    }
}

/**
 * @param {Object} param0
 * @param {string} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsStringWithTwoPartsSeparatedByDot({ propertyValue }) {
    const [part1, part2, part3] = propertyValue.split('.');
    if (!part1 || !part2 || part3) {
        throw new Error(`Value "${propertyValue}" should be a 2 parts string separared by a single dot. Follow the expected format, or check for typos`);
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.fieldDefinition field being currently checked
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.propertyValue
 * @throws {Error}
 */
function checkPropertyIsRelationNameDotFieldName({ fieldDefinition, Models, Model, propertyValue }) {
    const [relationName, relatedName] = propertyValue.split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    if (relationFields.size === 0) {
        throw new Error(`Undefined relation "${relationName}". Target a field on the current model, or check for typos.`);
    }
    for (const relationField of relationFields) {
        if (!relationField.properties.to) {
            throw new Error(`Invalid field type of relation "${relationName}". Target a relation field.`);
        }
    }
    const relatedModelName = [...relationFields].find(relationField => relationField.properties.to).properties.to;
    const relatedFields = getMatchingFieldsDefinitionFromParents({ Models, Model: Models[relatedModelName], fieldName: relatedName });
    if (relatedFields.size === 0) {
        throw new Error(`Undefined related field "${relatedName}". Target a field on the relation model, or check for typos.`);
    }
    for (const relatedField of relatedFields) {
        if (relatedField.properties.to !== fieldDefinition.properties.to) {
            throw new Error(`Related field "${relatedModelName}/${relatedName}" has mismatch type. Change the type of either the related field or the target field.`);
        }
    }
}
