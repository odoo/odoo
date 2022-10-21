/** @odoo-module **/

import { insertRecords } from '@bus/../tests/helpers/model_definitions_helpers';

import { registry } from '@web/core/registry';
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeMockServer } from "@web/../tests/helpers/mock_server";
import core from 'web.core';

const testDataPromise = new Promise(resolve => {
    QUnit.begin(() => resolve(getTestData()));
});

/**
 * Fetch and prepare test data, that is :
 *     1 - Fetch model definitions from the server then insert fields present in the
 *     `bus.model.definitions` registry. Use `addModelNamesToFetch`/`insertModelFields`
 *     helpers in order to add models to be fetched, default values to the fields,
 *     fields to a model definition.
 *
 *     2 - Fetch required records by their xml id and add them to the records to be inserted
 *     every time the mock server is created. Use `addRefsToFetch` helper in order to add
 *     records to be fetched.
 *
 * @return {Object}
 * @see model_definitions_setup.js
 */
async function getTestData() {
    const modelNamesToFetch = registry.category('bus.model.definitions').get('modelNamesToFetch');
    const refsToFetch = registry.category('bus.model.definitions').get('refsToFetch');

    const formData = new FormData();
    formData.append('csrf_token', core.csrf_token);
    formData.append('model_names_to_fetch', JSON.stringify([...modelNamesToFetch]));
    formData.append('refs_to_fetch', JSON.stringify([...refsToFetch]));
    const response = await window.fetch('/bus/get_test_data', { body: formData, method: 'POST' });
    if (response.status !== 200) {
        throw new Error('Error while fetching test data');
    }
    const jsonResponse = await response.json();
    insertRecords('res.users', [jsonResponse['current_user']]);
    insertRecords('res.partner', [jsonResponse['current_partner']]);
    const testData = {
        currentUserId: jsonResponse['current_user'].id,
        modelDefinitions: prepareModelDefinitions(jsonResponse),
        unreachableRefs: jsonResponse['unreachable_refs'],
        xmlIdsToRecordInfo: prepareRecordInfos(jsonResponse),
    };
    return testData;
}

/**
 *
 * @param {Object} testData
 * @param {Object} [testData.model_definitions]
 *
 * @returns {Map<string, object>} Formatted model definitions, fully
 * configured (a map from model names to field definitions).
 */
 function prepareModelDefinitions({ model_definitions }) {
    const modelDefinitions = new Map(Object.entries(model_definitions));
    const modelDefinitionsRegistry = registry.category('bus.model.definitions');
    const fieldsToInsertRegistry = modelDefinitionsRegistry.category('fieldsToInsert');

    for (const [modelName, fields] of modelDefinitions) {
        // insert fields present in the fieldsToInsert registry : if the field
        // exists, update its default value according to the one in the
        // registry; If it does not exist, add it to the model definition.
       const fieldNamesToFieldToInsert = fieldsToInsertRegistry.category(modelName).getEntries();
       for (const [fname, fieldToInsert] of fieldNamesToFieldToInsert) {
           if (fname in fields) {
               fields[fname].default = fieldToInsert.default;
           } else {
               fields[fname] = fieldToInsert;
           }
       }
       // apply default values for date like fields if none was passed.
       for (const fname in fields) {
           const field = fields[fname];
           if (['date', 'datetime'].includes(field.type) && !field.default) {
               const defaultFieldValue = field.type === 'date'
                   ? () => moment.utc().format('YYYY-MM-DD')
                   : () => moment.utc().format("YYYY-MM-DD HH:mm:ss");
               field.default = defaultFieldValue;
           } else if (fname === 'active' && !('default' in field)) {
               // records are active by default.
               field.default = true;
           }
       }
   }
   // add models present in the fake models registry to the model definitions.
   const fakeModels = modelDefinitionsRegistry.category('fakeModels').getEntries();
   for (const [modelName, fields] of fakeModels) {
       modelDefinitions.set(modelName, fields);
   }
   return modelDefinitions;
}

/**
 * @param {Object} testData
 * @param {Object} [testData.records_by_model_name]
 *
 * @returns {Map<string, object>} Map from xml id to record info (modelName, id).
 */
 function prepareRecordInfos({ records_by_model_name }) {
    const recordDataByModelName = new Map(Object.entries(records_by_model_name));
    const xmlIdsToRecordInfo = new Map();
    for (const [modelName, recordsWithXmlId] of recordDataByModelName) {
        const allModelRecords = [];
        for (const [xmlId, record] of recordsWithXmlId) {
            xmlIdsToRecordInfo[xmlId] = { modelName, id: record.id };
            allModelRecords.push(record);
        }
        insertRecords(modelName, allModelRecords.sort((r1, r2) => r1.id - r2.id));
    }
    return xmlIdsToRecordInfo;
}

let pyEnv;
/**
 * Creates an environment that can be used to setup test data as well as
 * creating data after test start.
 *
 * @param {Object} serverData serverData to pass to the mockServer.
 * @param {Object} [serverData.action] actions to be passed to the mock
 * server.
 * @param {Object} [serverData.views] views to be passed to the mock
 * server.
 * @returns {Object} An environment that can be used to interact with
 * the mock server (creation, deletion, update of records...)
 */
 export async function startServer({ actions, views = {} } = {}) {
    const models = {};
    const testData = await testDataPromise;
    const { modelDefinitions, unreachableRefs, xmlIdsToRecordInfo } = testData;

    const recordsToInsertRegistry = registry.category('bus.model.definitions').category('recordsToInsert');
    for (const [modelName, fields] of modelDefinitions) {
        const records = [];
        if (recordsToInsertRegistry.contains(modelName)) {
            // prevent tests from mutating the records.
            records.push(...JSON.parse(JSON.stringify(recordsToInsertRegistry.get(modelName))));
        }
        models[modelName] = { fields: { ...fields }, records };

        // generate default views for this model if none were passed.
        const viewArchsSubRegistries = registry.category('bus.view.archs').subRegistries;
        for (const [viewType, archsRegistry] of Object.entries(viewArchsSubRegistries)) {
            views[`${modelName},false,${viewType}`] =
                views[`${modelName},false,${viewType}`] ||
                archsRegistry.get(modelName, archsRegistry.get('default'));
        }
    }
    let currentUser, currentPartner = null;
    pyEnv = new Proxy(
        {
            get currentUser() {
                return currentUser;
            },
            get currentUserId() {
                return currentUser.id;
            },
            set currentUserId(userId) {
                if (!userId) {
                    currentUser = null;
                    currentPartner = null;
                    return;
                }
                const users = this.mockServer.getRecords('res.users', [['id', '=', userId]]);
                if (users.length === 0) {
                    throw new Error(`Unknown user: id=${userId}`);
                }
                currentUser = users[0];
                currentPartner = null;
                if (currentUser.partner_id) {
                    currentPartner = this.mockServer.getRecords('res.partner', [['id', '=', currentUser.partner_id]])[0] || null;
                }
            },
            get currentPartner() {
                return currentPartner;
            },
            get currentPartnerId() {
                return currentPartner.id;
            },
            getData() {
                return this.mockServer.models;
            },
            getViews() {
                return views;
            },
            ref(xmlId) {
                if (unreachableRefs.includes(xmlId)) {
                    throw new Error(`
                        Cannot access ${xmlId} record.
                        Please start the test suite as administrator/verify that the given xml id exists.
                    `);
                }
                if (!(xmlId in xmlIdsToRecordInfo)) {
                    throw new Error(`Unknown xml id: '${xmlId}', please use 'addRefsToFetch'.`);
                }
                const { modelName, id } = xmlIdsToRecordInfo[xmlId];
                const searchDomain = [['id', '=', id]];
                if ('active' in modelDefinitions.get(modelName)) {
                    searchDomain.push(['active', 'in', [true, false]]);
                }
                return this.mockServer.getRecords(modelName, searchDomain)[0];
            },
            simulateConnectionLost(closeCode) {
                this.mockServer._simulateConnectionLost(closeCode);
            },
        },
        {
            get(target, name) {
                if (name in target) {
                    return target[name];
                }
                const modelAPI = {
                    /**
                     * Simulate a 'create' operation on a model.
                     *
                     * @param {Object[]|Object} values records to be created.
                     * @returns {integer[]|integer} array of ids if more than one value was passed,
                     * id of created record otherwise.
                     */
                    create(values) {
                        if (!values) {
                            return;
                        }
                        if (!Array.isArray(values)) {
                            values = [values];
                        }
                        const recordIds = values.map(value => target.mockServer.mockCreate(name, value));
                        return recordIds.length === 1 ? recordIds[0] : recordIds;
                    },
                    /**
                     * Simulate a 'search' operation on a model.
                     *
                     * @param {Array} domain
                     * @param {Object} context
                     * @returns {integer[]} array of ids corresponding to the given domain.
                     */
                    search(domain, context = {}) {
                        return target.mockServer.mockSearch(name, [domain], context);
                    },
                    /**
                     * Simulate a `search_count` operation on a model.
                     *
                     * @param {Array} domain
                     * @return {number} count of records matching the given domain.
                     */
                    searchCount(domain) {
                        return this.search(domain).length;
                    },
                    /**
                     * Simulate a 'search_read' operation on a model.
                     *
                     * @param {Array} domain
                     * @param {Object} kwargs
                     * @returns {Object[]} array of records corresponding to the given domain.
                     */
                    searchRead(domain, kwargs = {}) {
                        return target.mockServer.mockSearchRead(name, [domain], kwargs);
                    },
                    /**
                     * Simulate an 'unlink' operation on a model.
                     *
                     * @param {integer[]} ids
                     * @returns {boolean} mockServer 'unlink' method always returns true.
                     */
                    unlink(ids) {
                        return target.mockServer.mockUnlink(name, [ids]);
                    },
                    /**
                     * Simulate a 'write' operation on a model.
                     *
                     * @param {integer[]} ids ids of records to write on.
                     * @param {Object} values values to write on the records matching given ids.
                     * @returns {boolean} mockServer 'write' method always returns true.
                     */
                    write(ids, values) {
                        return target.mockServer.mockWrite(name, [ids, values]);
                    },
                };
                if (name === 'bus.bus') {
                    modelAPI['_sendone'] = target.mockServer._mockBusBus__sendone.bind(target.mockServer);
                    modelAPI['_sendmany'] = target.mockServer._mockBusBus__sendmany.bind(target.mockServer);
                }
                return modelAPI;
            },
            set(target, name, value) {
                return target[name] = value;
            },
         },
    );
    pyEnv['mockServer'] = await makeMockServer({ actions, models, views });
    pyEnv['mockServer'].pyEnv = pyEnv;
    currentUser = pyEnv['res.users'].searchRead([['id', '=', testData['currentUserId']]])[0];
    if (currentUser && currentUser.partner_id) {
        currentPartner = pyEnv['res.partner'].searchRead([['id', '=', currentUser.partner_id[0]]])[0];
    }
    registerCleanup(() => pyEnv = undefined);
    return pyEnv;
}

/**
 *
 * @returns {Object} An environment that can be used to interact with the mock
 * server (creation, deletion, update of records...)
 */
export function getPyEnv() {
    return pyEnv || startServer();
}
