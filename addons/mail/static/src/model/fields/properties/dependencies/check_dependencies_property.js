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
export function checkDependenciesProperty({ Models, Model, field }) {
    if (!field.dependencies) {
        return;
    }
    checkDependenciesPropetyGoesWithComputeProperty({ Model, field });
    checkDependenciesPropertyIsArray({ Model, field });
    checkExistenceOfTargetFieldForDependencies({ Models, Model, field });
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkDependenciesPropetyGoesWithComputeProperty({ Model, field }) {
    if (!field.compute) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `unsupported "dependendencies" property on field without the "compute" property`,
            suggestion: `either remove the "dependencies" property or add the "compute" property`,
        });
    }
}

/**
 * @param {Object} param0
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkDependenciesPropertyIsArray({ Model, field }) {
    if (!(field.dependencies instanceof Array)) {
        throw new InvalidFieldError({
            modelName: Model.modelName,
            fieldName: field.properties.fieldName,
            error: `property "dependencies" must be an array of field names instead of "${field.dependencies}"`,
            suggestion: `make it an array`,
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
function checkExistenceOfTargetFieldForDependencies({ Models, Model, field }) {
    for (const dependency of field.dependencies) {
        const fields = getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName: dependency });
        if (fields.size === 0) {
            throw new InvalidFieldError({
                modelName: Model.modelName,
                fieldName: field.properties.fieldName,
                error: `unsupported dependency "${dependency}"`,
                suggestion: `make sure dependencies target only fields of current model, or check for typos`,
            });
        }
    }
}
