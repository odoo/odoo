/** @odoo-module **/

import { checkFieldName } from '@mail/model/fields/check_field_name';
import { checkFieldType } from '@mail/model/fields/check_field_type';
import { checkComputeProperty } from '@mail/model/fields/properties/compute/check_compute_property';
import { checkDependenciesProperty } from '@mail/model/fields/properties/dependencies/check_dependencies_property';
import { checkIsOnChangeProperty } from '@mail/model/fields/properties/is_on_change/check_isonchange_property';
import { checkRelatedProperty } from '@mail/model/fields/properties/related/check_related_property';

/**
 * This module provides an utility function to check the consistency of model
 * fields as they are declared. These checks allow early detection of developer
 * mistakes when writing model fields.
 */

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Map<string, Object>} param0.fieldTypeRegistry
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
 * @param {Map<string, Object>} param0.fieldTypeRegistry
 * @param {Object} param0.Model model being currently checked
 * @param {Object} param0.field field being currently checked
 * @throws {InvalidFieldError}
 */
function checkDeclaredFieldOnModel({ Models, fieldTypeRegistry, Model, field }) {
    checkFieldName({ Model, field });
    checkFieldType({ fieldTypeRegistry, Model, field });
    const fieldType = fieldTypeRegistry.get(field.fieldType);
    fieldType.checkDeclaration({ Models, Model, field });
    // TODO SEB iterate over registered properties (depending on each field type)
    if (field.compute) {
        checkComputeProperty({ Model, field });
    }
    if (field.dependencies) {
        checkDependenciesProperty({ Models, Model, field });
    }
    if (field.isOnChange) {
        checkIsOnChangeProperty({ Model, field });
    }
    if (field.related) {
        checkRelatedProperty({ Models, Model, field });
    }
}
