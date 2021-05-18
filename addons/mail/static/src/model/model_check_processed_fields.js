/** @odoo-module **/

import { InvalidFieldError } from '@mail/model/model_errors';
import { checkFieldType } from '@mail/model/fields/check_field_type';
import { checkAttributeField } from '@mail/model/fields/types/attribute/check_attribute_field';
import { checkRelationField } from '@mail/model/fields/types/relation/check_relation_field';
import { checkComputeProperty } from '@mail/model/fields/properties/compute/check_compute_property';
import { checkDependenciesProperty } from '@mail/model/fields/properties/dependencies/check_dependencies_property';
import { checkIsOnChangeProperty } from '@mail/model/fields/properties/is_on_change/check_isonchange_property';
import { checkRelatedProperty } from '@mail/model/fields/properties/related/check_related_property';

/**
 * @param {Object} param0
 * @param {Object} param0.Models
 * @param {Map} param0.fieldTypeRegistry
 * @throws {Error} in case some fields are not correct.
 */
export function checkProcessedFieldsOnModels({ Models, fieldTypeRegistry }) {
    for (const Model of Object.values(Models)) {
        for (const field of Object.values(Model.fields)) {
            checkProcessedFieldsOnModel({ Models, fieldTypeRegistry, Model, field });
        }
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Models
 * @param {Map} param0.fieldTypeRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {Error} in case some fields are not correct.
 */
function checkProcessedFieldsOnModel({ Models, fieldTypeRegistry, Model, field }) {
    // checkFieldName({ Model, field });
    checkFieldType({ fieldTypeRegistry, Model, field });
    // TODO SEB breaking because of extra properties (eg. dependents)
    // switch (field.fieldType) {
    //     case 'attribute':
    //         checkAttributeField({ Model, field });
    //         break;
    //     case 'relation':
    //         checkRelationField({ Models, Model, field });
    //         break;
    // }
    if (field.compute) {
        checkComputeProperty({ Model, field });
    }
    // TODO SEB breaking because of dependencies added on non-compute fields
    // if (field.dependencies) {
    //     checkDependenciesProperty({ Models, Model, field });
    // }
    if (field.isOnChange) {
        checkIsOnChangeProperty({ Model, field });
    }
    if (field.related) {
        checkRelatedProperty({ Models, Model, field });
    }
    if (field.compute && field.related) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `cannot be a related and compute field at the same time`,
            suggestion: ``,
        });
    }
    if (field.fieldType === 'attribute') {
        return;
    }
    if (!field.relationType) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `must define a relation type in "relationType"`,
            suggestion: ``,
        });
    }
    if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(field.relationType))) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `has invalid relation type "${field.relationType}"`,
            suggestion: ``,
        });
    }
    if (!field.inverse) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `must define an inverse relation name in "inverse"`,
            suggestion: ``,
        });
    }
    if (!field.to) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `must define a model name in "to" (1st positional parameter of relation field helpers`,
                suggestion: ``,
            });
    }
    const RelatedModel = Models[field.to];
    if (!RelatedModel) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `model name does not exist.`,
            suggestion: ``,
        });
    }
    const inverseField = RelatedModel.fields[field.inverse];
    if (!inverseField) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `has no inverse field "${RelatedModel.modelName}/${field.inverse}"`,
            suggestion: ``,
        });
    }
    if (inverseField.inverse !== field.fieldName) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
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
            fieldName: field.fieldName,
            error: `has inverse relation "${RelatedModel.modelName}/${field.inverse}" misconfigured (currently "${inverseField.to}", should instead refer to this model or parented models: ${allSelfAndParentNames.map(name => `"${name}"`).join(', ')}?)`,
            suggestion: ``,
        });
    }
    if (
        (field.relationType === 'many2many' && inverseField.relationType !== 'many2many') ||
        (field.relationType === 'one2one' && inverseField.relationType !== 'one2one') ||
        (field.relationType === 'one2many' && inverseField.relationType !== 'many2one') ||
        (field.relationType === 'many2one' && inverseField.relationType !== 'one2many')
    ) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.fieldName,
            error: `Mismatch relations types "${Model.modelName}/${field.fieldName}" (${field.relationType}) and "${RelatedModel.modelName}/${field.inverse}" (${inverseField.relationType})`,
            suggestion: ``,
        });
    }
}
