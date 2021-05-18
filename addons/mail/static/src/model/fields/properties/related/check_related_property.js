/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';
import { getMatchingFieldsDefinitionFromParents } from '@mail/model/fields/get_matching_fields_definition_from_parents';

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
export function checkRelatedProperty({ Models, Model, field }) {
    if (!field.related) {
        return;
    }
    checkRelatedPropertyGoesWithoutComputeProperty({ Models, Model, field });
    checkRelatedPropertyIsString({ Model, field });
    checkFormatOfRelatedProperty({ Model, field });
    checkRelationOfRelatedProperty({ Models, Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkRelatedPropertyGoesWithoutComputeProperty({ Models, Model, field }) {
    const fields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: field.fieldName });
    if ([...fields].some(field => field.compute)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported "related" property on field with the "compute" property`,
            suggestion: `either remove the "related" property or remove the "compute" property`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkRelatedPropertyIsString({ Model, field }) {
    if (!(typeof field.related === 'string')) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `property "related" must be a string instead of "${field.related}"`,
            suggestion: `make it a string (with the format "relationFieldName.relatedFieldName")`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkFormatOfRelatedProperty({ Model, field }) {
    const [relationName, relatedFieldName, other] = field.related.split('.');
    if (!relationName || !relatedFieldName || other) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported related format "${field.related}"`,
            suggestion: `use the format "relationFieldName.relatedFieldName".`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkRelationOfRelatedProperty({ Models, Model, field }) {
    checkExistenceOfRelationFieldForRelatedProperty({ Models, Model, field });
    checkFieldTypeOfRelationFieldForRelatedProperty({ Models, Model, field });
    checkExistenceOfRelatedFieldForRelatedProperty({ Models, Model, field });
    checkFieldTypeOfRelatedFieldForRelatedProperty({ Models, Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkExistenceOfRelationFieldForRelatedProperty({ Models, Model, field }) {
    const [relationName] = field.related.split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    if (relationFields.size === 0) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `undefined relation "${relationName}"`,
            suggestion: `target a field on the current model, or check for typos`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkFieldTypeOfRelationFieldForRelatedProperty({ Models, Model, field }) {
    const [relationName] = field.related.split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    for (const relationField of relationFields) {
        if (relationField.fieldType !== 'relation') {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `invalid field type of relation "${relationName}"`,
                suggestion: `target a relation field`,
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
function checkExistenceOfRelatedFieldForRelatedProperty({ Models, Model, field }) {
    const [relationName, relatedName] = field.related.split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    const RelatedModelName = [...relationFields].find(relationField => relationField.to).to;
    const relatedFields = getMatchingFieldsDefinitionFromParents({ Models, Model: Models[RelatedModelName], fieldName: relatedName });
    if (relatedFields.size === 0) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `unsupported related field "${relatedName}"`,
            suggestion: `target a field on the relation model, or check for typos`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkFieldTypeOfRelatedFieldForRelatedProperty({ Models, Model, field }) {
    const [relationName, relatedName] = field.related.split('.');
    const relationFields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: relationName });
    const RelatedModelName = [...relationFields].find(relationField => relationField.to).to;
    const relatedFields = getMatchingFieldsDefinitionFromParents({ Models, Model: Models[RelatedModelName], fieldName: relatedName });
    for (const relatedField of relatedFields) {
        if (relatedField.fieldType !== field.fieldType) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `related field "${Model.modelName}/${field.fieldName}" has mismatch type`,
                suggestion: `change the type of either the related field or the target field`,
            });
        }
        if (
            relatedField.fieldType === 'relation' &&
            relatedField.to !== field.to
        ) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.fieldName,
                error: `related field "${Model.modelName}/${field.fieldName}" has mismatch target model name`,
                suggestion: `change the relation model name of either the related field or the target field`,
            });
        }
    }
}
