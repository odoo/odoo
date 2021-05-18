/** @odoo-module **/

/**
 * @param {Object} param0
 * @param {Object} param0.Models all existing models
 * @param {Object} param0.Model model being currently checked
 * @param {string} param0.fieldName name of the field being currently checked
 * @returns {Set<Object>}
 */
export function getMatchingFieldsDefinitionFromParents({ Models, Model, fieldName }) {
    if (!Models[Model.modelName]) {
        return new Set();
    }
    const field = Model.fields && Model.fields[fieldName];
    const parentFields = getMatchingFieldsDefinitionFromParents({ Models, Model: Model.__proto__, fieldName });
    if (!field) {
        return parentFields;
    }
    return new Set([field, ...parentFields]);
}
