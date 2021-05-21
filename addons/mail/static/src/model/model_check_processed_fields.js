/** @odoo-module **/

/**
 * @param {Object} param0
 * @param {Object} param0.Models
 * @param {Object} param0.env
 * @throws {Error} in case some fields are not correct.
 */
export function checkProcessedFieldsOnModels({ Models, env }) {
    for (const [modelName, Model] of Object.entries(Models)) {
        try {
            for (const [fieldName, field] of Object.entries(Model.fields)) {
                try {
                    checkProcessedFieldsOnModel({ Models, env, Model, field });
                } catch (error) {
                    error.message = `Invalid field "${fieldName}": ${error.message}`;
                    throw error;
                }
            }
        } catch (error) {
            error.message = `Invalid Model "${modelName}": ${error.message}`;
            throw error;
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
        throw new Error(`cannot be a related and compute field at the same time`);
    }
    if (!field.to) {
        return;
    }
    // TODO SEB check with x2/2x properties
    // if (!field.relationType) {
    //     throw new /         error: `must define a relation type in "relationType"`);
    // }
    // if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(field.relationType))) {
    //     throw new /         error: `has invalid relation type "${field.relationType}"`);
    // }
    if (!field.inverse) {
        throw new Error(`must define an inverse relation name in "inverse"`);
    }
    const RelatedModel = Models[field.to];
    if (!RelatedModel) {
        throw new Error(`model name does not exist.`);
    }
    const inverseField = RelatedModel.fields[field.inverse];
    if (!inverseField) {
        throw new Error(`has no inverse field "${RelatedModel.modelName}/${field.inverse}"`);
    }
    if (inverseField.inverse !== field.fieldName) {
        throw new Error(`inverse field does not match with field name of relation "${RelatedModel.modelName}/${inverseField.inverse}"`);
    }
    const allSelfAndParentNames = [];
    let TargetModel = Model;
    while (TargetModel) {
        allSelfAndParentNames.push(TargetModel.modelName);
        TargetModel = TargetModel.__proto__;
    }
    if (!allSelfAndParentNames.includes(inverseField.to)) {
        throw new Error(`has inverse relation "${RelatedModel.modelName}/${field.inverse}" misconfigured (currently "${inverseField.to}", should instead refer to this model or parented models: ${allSelfAndParentNames.map(name => `"${name}"`).join(', ')}?)`);
    }
    // if (
    //     (field.relationType === 'many2many' && inverseField.relationType !== 'many2many') ||
    //     (field.relationType === 'one2one' && inverseField.relationType !== 'one2one') ||
    //     (field.relationType === 'one2many' && inverseField.relationType !== 'many2one') ||
    //     (field.relationType === 'many2one' && inverseField.relationType !== 'one2many')
    // ) {
    //     throw new /         error: `Mismatch relations types "${Model.modelName}/${field.fieldName}" (${field.relationType}) and "${RelatedModel.modelName}/${field.inverse}" (${inverseField.relationType})`);
    // }
}
