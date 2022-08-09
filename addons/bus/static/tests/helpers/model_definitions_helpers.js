/** @odoo-module **/

import { registry } from '@web/core/registry';

const modelDefinitionsRegistry = registry.category('bus.model.definitions');
const customModelFieldsRegistry = modelDefinitionsRegistry.category('fieldsToInsert');
const recordsToInsertRegistry = modelDefinitionsRegistry.category('recordsToInsert');
const fakeModelsRegistry = modelDefinitionsRegistry.category('fakeModels');
/**
 * Add models whose definitions need to be fetched on the server.
 *
 * @param {string[]} modelName
 */
export function addModelNamesToFetch(modelNames) {
    if (!modelDefinitionsRegistry.contains('modelNamesToFetch')) {
        modelDefinitionsRegistry.add('modelNamesToFetch', []);
    }
    modelDefinitionsRegistry.get('modelNamesToFetch').push(...modelNames);
}

/**
 * Add models that will be added to the model definitions. We should
 * avoid to rely on fake models and use real models instead.
 *
 * @param {string} modelName
 * @param {Object} fields
 */
export function addFakeModel(modelName, fields) {
    fakeModelsRegistry.add(modelName, fields);
}

/**
 * Add model fields that are not present on the server side model's definitions
 * but are required to ease testing or add default values for existing fields.
 *
 * @param {string} modelName
 * @param {Object} fieldNamesToFields
 */
 export function insertModelFields(modelName, fieldNamesToFields) {
    const modelCustomFieldsRegistry = customModelFieldsRegistry.category(modelName);
    for (const fname in fieldNamesToFields) {
        modelCustomFieldsRegistry.add(fname, fieldNamesToFields[fname]);
    }
}

/**
 * Add records to the initial server data.
 *
 * @param {string} modelName
 * @param {Object[]} records
 */
export function insertRecords(modelName, records) {
    if (!recordsToInsertRegistry.contains(modelName)) {
        recordsToInsertRegistry.add(modelName, []);
    }
    recordsToInsertRegistry.get(modelName).push(...records);
}
