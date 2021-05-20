/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';

/**
 * @param {Object} param0
 * @param {Object} param0.Models
 * @param {Object} param0.env
 * @throws {Error} in case some fields are not correct.
 */
export function checkProcessedFieldsOnModels({ Models, env }) {
    for (const Model of Object.values(Models)) {
        for (const field of Object.values(Model.fields)) {
            checkProcessedFieldsOnModel({ Models, env, Model, field });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models
 * @param {Object} param0.env
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {Error} in case some fields are not correct.
 */
function checkProcessedFieldsOnModel({ Models, env, Model, field }) {
    // checkFieldName({ Model, field });
    // TODO SEB fieldType not defined in processed field
    // checkFieldType({ env.modelManager.fieldTypeRegistry, Model, field });
    // TODO SEB breaking because of extra properties (eg. dependents)
    // switch (field.fieldType) {
    //     case 'attribute':
    //         checkAttributeField({ Model, field });
    //         break;
    //     case 'relation':
    //         checkRelationField({ Models, Model, field });
    //         break;
    // }
    // if (field.compute) {
    //     checkComputeProperty({ Model, field });
    // }
    // TODO SEB breaking because of dependencies added on non-compute fields
    // if (field.dependencies) {
    //     checkDependenciesProperty({ Models, Model, field });
    // }
    // if (field.isOnChange) {
    //     checkIsOnChangeProperty({ Model, field });
    // }
    // if (field.related) {
    //     checkRelatedProperty({ Models, Model, field });
    // }
    if (field.compute && field.related) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `cannot be a related and compute field at the same time`,
            suggestion: ``,
        });
    }
    if (!field.to) {
        return;
    }
    // TODO SEB check with x2/2x properties
    // if (!field.relationType) {
    //     throw new InvalidFieldError({
    //         modelName: Model.modelName,
    //         fieldName: field.properties.fieldName,
    //         error: `must define a relation type in "relationType"`,
    //         suggestion: ``,
    //     });
    // }
    // if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(field.relationType))) {
    //     throw new InvalidFieldError({
    //         modelName: Model.modelName,
    //         fieldName: field.properties.fieldName,
    //         error: `has invalid relation type "${field.relationType}"`,
    //         suggestion: ``,
    //     });
    // }
    if (!field.inverse) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `must define an inverse relation name in "inverse"`,
            suggestion: ``,
        });
    }
    const RelatedModel = Models[field.to];
    if (!RelatedModel) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `model name does not exist.`,
            suggestion: ``,
        });
    }
    const inverseField = RelatedModel.fields[field.inverse];
    if (!inverseField) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `has no inverse field "${RelatedModel.modelName}/${field.inverse}"`,
            suggestion: ``,
        });
    }
    if (inverseField.inverse !== field.fieldName) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `inverse field does not match with field name of relation "${RelatedModel.modelName}/${inverseField.inverse}"`,
            suggestion: ``,
        });
    }
    const allSelfAndParentNames = [];
    let TargetModel = Model;
    while (TargetModel) {
        allSelfAndParentNames.push(TargetModel.modelName);
        TargetModel = TargetModel.__proto__;
    }
    if (!allSelfAndParentNames.includes(inverseField.to)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `has inverse relation "${RelatedModel.modelName}/${field.inverse}" misconfigured (currently "${inverseField.to}", should instead refer to this model or parented models: ${allSelfAndParentNames.map(name => `"${name}"`).join(', ')}?)`,
            suggestion: ``,
        });
    }
    // if (
    //     (field.relationType === 'many2many' && inverseField.relationType !== 'many2many') ||
    //     (field.relationType === 'one2one' && inverseField.relationType !== 'one2one') ||
    //     (field.relationType === 'one2many' && inverseField.relationType !== 'many2one') ||
    //     (field.relationType === 'many2one' && inverseField.relationType !== 'one2many')
    // ) {
    //     throw new InvalidFieldError({
    //         modelName: Model.modelName,
    //         fieldName: field.properties.fieldName,
    //         error: `Mismatch relations types "${Model.modelName}/${field.fieldName}" (${field.relationType}) and "${RelatedModel.modelName}/${field.inverse}" (${inverseField.relationType})`,
    //         suggestion: ``,
    //     });
    // }
}
