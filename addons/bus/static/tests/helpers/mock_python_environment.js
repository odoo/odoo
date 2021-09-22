/** @odoo-module **/

import { TEST_USER_IDS } from '@bus/../tests/helpers/test_constants';

import { registry } from '@web/core/registry';
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeMockServer } from "@web/../tests/helpers/mock_server";
import core from 'web.core';

const modelDefinitionsPromise = new Promise(resolve => {
    QUnit.begin(() => resolve(getModelDefinitions()));
});

/**
 * Fetch model definitions from the server then insert fields present in the
 * `bus.model.definitions` registry. Use `addModelNamesToFetch`/`insertModelFields`
 * helpers in order to add models to be fetched, default values to the fields,
 * fields to a model definition.
 *
 * @return {Map<string, Object>} A map from model names to model fields definitions.
 * @see model_definitions_setup.js
 */
async function getModelDefinitions() {
    const modelDefinitionsRegistry = registry.category('bus.model.definitions');
    const modelNamesToFetch = modelDefinitionsRegistry.get('modelNamesToFetch');
    const fieldsToInsertRegistry = modelDefinitionsRegistry.category('fieldsToInsert');

    // fetch the model definitions.
    const formData = new FormData();
    formData.append('csrf_token', core.csrf_token);
    formData.append('model_names_to_fetch', JSON.stringify(modelNamesToFetch));
    const response = await window.fetch('/bus/get_model_definitions', { body: formData, method: 'POST' });
    if (response.status !== 200) {
        throw new Error('Error while fetching required models');
    }
    const modelDefinitions = new Map(Object.entries(await response.json()));

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
    const modelDefinitions = await modelDefinitionsPromise;
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
    pyEnv = new Proxy(
        {
            get currentPartner() {
                return this.mockServer.currentPartner;
            },
            getData() {
                return this.mockServer.models;
            },
            getViews() {
                return views;
            },
            simulateConnectionLost(closeCode) {
                this.mockServer._simulateConnectionLost(closeCode);
            },
            ...TEST_USER_IDS,
        },
        {
            get(target, name) {
                if (target[name]) {
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
