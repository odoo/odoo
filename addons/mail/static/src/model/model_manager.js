/** @odoo-module **/

import { registry } from '@mail/model/model_core';
import { ModelField } from '@mail/model/model_field';
import { FieldCommand, unlinkAll } from '@mail/model/model_field_command';
import { RelationSet } from '@mail/model/model_field_relation_set';
import { Listener } from '@mail/model/model_listener';
import { followRelations } from '@mail/model/model_utils';
import { makeDeferred } from '@mail/utils/deferred';

/**
 * Object that manage models and records, notably their update cycle: whenever
 * some records are requested for update (either with model static method
 * `insert()` or record method `update()`), this object processes them with
 * direct field & and computed field updates.
 */
export class ModelManager {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    constructor(env) {
        /**
         * The messaging env.
         */
        this.env = env;
        /**
         * Promise which becomes resolved when messaging is created. Useful for
         * waiting before accessing `this.messaging`.
         */
        this.messagingCreatedPromise = makeDeferred();
        /**
         * Promise which becomes resolved when messaging is initialized. Useful
         * for waiting before accessing `this.messaging`.
         */
        this.messagingInitializedPromise = makeDeferred();

        //----------------------------------------------------------------------
        // Various variables that are necessary to handle an update cycle. The
        // goal of having an update cycle is to delay the execution of computes,
        // life-cycle hooks and potential UI re-renders until the last possible
        // moment, for performance reasons.
        //----------------------------------------------------------------------

        /**
         * Set of records that have been created during the current update
         * cycle and for which the compute/related methods still have to be
         * executed a first time.
         */
        this._createdRecordsComputes = new Set();
        /**
         * Set of records that have been created during the current update
         * cycle and for which the _created method still has to be executed.
         */
        this._createdRecordsCreated = new Set();
        /**
         * Set of records that have been created during the current update
         * cycle and for which the onChange methods still have to be executed
         * a first time.
         */
        this._createdRecordsOnChange = new Set();
        /**
         * Set of active listeners. Useful to be able to register which records
         * or fields they accessed to be able to notify them when those change.
         */
        this._listeners = new Set();
        /**
         * Map between model and a set of listeners that are using all() on that
         * model.
         */
        this._listenersObservingAllByModel = new Map();
        /**
         * Map between localId and a set of listeners that are using it. The
         * following fields use localId instead of record reference because the
         * listener might try to use a record that doesn't exist yet.
         */
        this._listenersObservingLocalId = new Map();
        /**
         * Map between fields of localId and a set of listeners that are
         * using it.
         */
        this._listenersObservingFieldOfLocalId = new Map();
        /**
         * Map of listeners that should be notified at the end of the current
         * update cycle. Value contains list of info to help for debug.
         */
        this._listenersToNotifyAfterUpdateCycle = new Map();
        /**
         * Map of listeners that should be notified as part of the current
         * update cycle. Value contains list of info to help for debug.
         */
        this._listenersToNotifyInUpdateCycle = new Map();
        /**
         * All generated models. Keys are model name, values are model class.
         */
        this.models = {};
        /**
         * Set of records that have been updated during the current update cycle
         * and for which required fields check still has to be executed.
         */
        this._updatedRecordsCheckRequired = new Set();
        /**
         * Determines whether this model manager should run in debug mode. Debug
         * mode adds more integrity checks and more verbose error messages, at
         * the cost of performance.
         */
        this.isDebug = false;
    }

    /**
     * Starts the generation of models as soon as all files have been loaded and
     * starts messaging itself afterwards.
     *
     * @param {Object} values field name/value pairs to give at messaging create
     */
    async start(values) {
        if (document.readyState === 'loading') {
            await new Promise(resolve => {
                /**
                 * Called when all JS resources are loaded. This is useful in order
                 * to do some processing after other JS files have been parsed, for
                 * example new models or patched models that are coming from
                 * other modules, because some of those patches might need to be
                 * applied before messaging initialization.
                 */
                window.addEventListener('load', resolve);
            });
        }
        /**
         * All JS resources are loaded, but not necessarily processed.
         * We assume no messaging-related modules return any Promise,
         * therefore they should be processed *at most* asynchronously at
         * "Promise time".
         */
        await new Promise(resolve => setTimeout(resolve));
        this._generateModels();
        /**
         * Create the messaging singleton record.
         */
        this.models['Messaging'].insert(values);
        this.messagingCreatedPromise.resolve();
        await this.messaging.start();
        this.messagingInitializedPromise.resolve();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns all records of provided model that match provided criteria.
     *
     * @param {Object} model
     * @param {function} [filterFunc]
     * @returns {Record[]} records matching criteria.
     */
    all(model, filterFunc) {
        for (const listener of this._listeners) {
            listener.lastObservedAllByModel.add(model);
            const entry = this._listenersObservingAllByModel.get(model);
            const info = {
                listener,
                reason: `all() - ${model}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        const allRecords = Object.values(model.__records);
        if (filterFunc) {
            return allRecords.filter(filterFunc);
        }
        return allRecords;
    }

    /**
     * Delete the record. After this operation, it's as if this record never
     * existed. Note that relation are removed, which may delete more relations
     * if some of them are causal.
     *
     * @param {Record} record
     */
    delete(record) {
        this._delete(record);
        this._flushUpdateCycle();
    }

    /**
     * Destroys this model manager, which consists of cleaning all possible
     * references in order to avoid memory leaks.
     */
    destroy() {
        this.messaging.delete();
        for (const model of Object.values(this.models)) {
            delete model.__fieldList;
            delete model.__fieldMap;
            delete model.__identifyingFieldNames;
            delete model.__records;
            delete model.__requiredFieldsList;
            delete model.fields;
            delete model.modelManager;
        }
    }

    /**
     * Returns whether the given record still exists.
     *
     * @param {Object} model
     * @param {Record} record
     * @returns {boolean}
     */
    exists(model, record) {
        return Boolean(record.localId);
    }

    /**
     * Gets the unique record of provided model that matches the given
     * identifying data, if it exists.
     *
     * @param {Object} model
     * @param {Object} data
     * @returns {Record|undefined}
     */
    findFromIdentifyingData(model, data) {
        return this.get(model, this._getRecordIndex(model, data));
    }

    /**
     * This method returns the record of provided model that matches provided
     * local id. Useful to convert a local id to a record.
     * Note that even if there's a record in the system having provided local
     * id, if the resulting record is not an instance of this model, this getter
     * assumes the record does not exist.
     *
     * @param {Object} model
     * @param {string} localId
     * @param {Object} param2
     * @param {boolean} [param2.isCheckingInheritance=false]
     * @returns {Record|undefined} record, if exists
     */
    get(model, localId, { isCheckingInheritance = false } = {}) {
        if (!localId) {
            return;
        }
        if (!isCheckingInheritance && this.isDebug) {
            const modelName = localId.split('(')[0];
            if (modelName !== model.name) {
                throw Error(`wrong format of localId ${localId} for ${model}.`);
            }
        }
        for (const listener of this._listeners) {
            listener.lastObservedLocalIds.add(localId);
            if (!this._listenersObservingLocalId.has(localId)) {
                this._listenersObservingLocalId.set(localId, new Map());
            }
            const entry = this._listenersObservingLocalId.get(localId);
            const info = {
                listener,
                reason: `get record - ${localId}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        const record = model.__records[localId];
        if (record) {
            return record;
        }
        if (!isCheckingInheritance) {
            return;
        }
        // support for inherited models (eg. relation targeting `Record`)
        for (const subModel of Object.values(this.models)) {
            if (!(subModel.prototype instanceof model)) {
                continue;
            }
            const record = subModel.__records[localId];
            if (record) {
                return record;
            }
        }
        return;
    }

    /**
     * Returns the messaging record once it is initialized. This method should
     * be considered the main entry point to the messaging system for outside
     * code.
     *
     * @returns {Messaging}
     **/
    async getMessaging() {
        await this.messagingCreatedPromise;
        await this.messagingInitializedPromise;
        return this.messaging;
    }

    /**
     * This method creates a record or updates one of provided model, based on
     * provided data. This method assumes that records are uniquely identifiable
     * per "unique find" criteria from data on model.
     *
     * @param {Object} model
     * @param {Object|Object[]} data
     *  If data is an iterable, multiple records will be created/updated.
     * @returns {Record|Record[]} created or updated record(s).
     */
    insert(model, data) {
        const isMulti = typeof data[Symbol.iterator] === 'function';
        const records = this._insert(model, isMulti ? data : [data]);
        this._flushUpdateCycle();
        return isMulti ? records : records[0];
    }

    /**
     * Returns the messaging singleton associated to this model manager.
     *
     * @returns {Messaging|undefined}
     */
    get messaging() {
        if (!this.models['Messaging']) {
            return undefined;
        }
        // Use "findFromIdentifyingData" specifically to ensure the record still
        // exists and to ensure listeners are properly notified of this access.
        return this.models['Messaging'].findFromIdentifyingData({});
    }

    /**
     * Removes a listener, with the same object reference as given to `startListening`.
     * Removing the listener effectively makes its `onChange` function no longer
     * called.
     *
     * @param {Listener} listener
     */
    removeListener(listener) {
        this._listeners.delete(listener);
        this._listenersToNotifyInUpdateCycle.delete(listener);
        this._listenersToNotifyAfterUpdateCycle.delete(listener);
        for (const localId of listener.lastObservedLocalIds) {
            this._listenersObservingLocalId.get(localId).delete(listener);
            const listenersObservingFieldOfLocalId = this._listenersObservingFieldOfLocalId.get(localId);
            for (const field of listener.lastObservedFieldsByLocalId.get(localId) || []) {
                listenersObservingFieldOfLocalId.get(field).delete(listener);
            }
        }
        for (const model of listener.lastObservedAllByModel) {
            this._listenersObservingAllByModel.get(model).delete(listener);
        }
        listener.lastObservedLocalIds.clear();
        listener.lastObservedFieldsByLocalId.clear();
        listener.lastObservedAllByModel.clear();
    }

    /**
     * Starts a listener. All records or fields accessed between `startListening`
     * and `stopListening` will be saved. When their value later changes,
     * `listener.onChange` will be called.
     *
     * @param {Listener} listener
     */
    startListening(listener) {
        this.removeListener(listener);
        this._listeners.add(listener);
    }

    /**
     * Stops a listener, with the same object reference as given to `startListening`.
     *
     * @param {Listener} listener
     */
    stopListening(listener) {
        this._listeners.delete(listener);
    }

    /**
     * Process an update on provided record with provided data. Updating
     * a record consists of applying direct updates first (i.e. explicit
     * ones from `data`) and then indirect ones (i.e. compute/related fields
     * and "after updates").
     *
     * @param {Record} record
     * @param {Object} data
     * @returns {boolean} whether any value changed for the current record
     */
    update(record, data) {
        const res = this._update(record, data);
        this._flushUpdateCycle();
        return res;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Returns the given data object completed with the default values of the
     * given model.
     *
     * @private
     * @param {Object} model
     * @param {Object} [data={}]
     */
    _addDefaultData(model, data = {}) {
        const data2 = { ...data };
        for (const field of model.__fieldList) {
            if (data2[field.fieldName] === undefined && field.default !== undefined) {
                data2[field.fieldName] = field.default;
            }
        }
        return data2;
    }

    /**
     * Adds fields, methods, getters, and identifyingMode from the model
     * definition to the model, then registers it in `this.models`.
     *
     * @private
     * @param {Object} model
     */
    _applyModelDefinition(model) {
        const definition = registry.get(model.name);
        Object.assign(model, Object.fromEntries(definition.get('modelMethods')));
        Object.assign(model.prototype, Object.fromEntries(definition.get('recordMethods')));
        for (const [getterName, getter] of definition.get('modelGetters')) {
            Object.defineProperty(model, getterName, { get: getter });
        }
        for (const [getterName, getter] of definition.get('recordGetters')) {
            Object.defineProperty(model.prototype, getterName, { get: getter });
        }
        // Make model manager accessible from model.
        model.modelManager = this;
        model.fields = {};
        // Contains all records. key is local id, while value is the record.
        model.__records = {};
        model.identifyingMode = definition.get('identifyingMode');
        this._listenersObservingAllByModel.set(model, new Map());
        this.models[model.name] = model;
    }

    /**
     * @private
     * @throws {Error} in case some declared fields are not correct.
     */
    _checkDeclaredFieldsOnModels() {
        for (const model of Object.values(this.models)) {
            for (const [fieldName, field] of registry.get(model.name).get('fields')) {
                // 0. Forbidden name.
                if (fieldName in model.prototype) {
                    throw new Error(`field(${fieldName}) on ${model} has a forbidden name.`);
                }
                // 1. Field type is required.
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`field(${fieldName}) on ${model} has unsupported type ${field.fieldType}.`);
                }
                // 2. Invalid keys based on field type.
                if (field.fieldType === 'attribute') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'fieldType',
                            'identifying',
                            'readonly',
                            'related',
                            'required',
                            'sum',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`field(${fieldName}) on ${model} contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                }
                if (field.fieldType === 'relation') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'fieldType',
                            'identifying',
                            'inverse',
                            'isCausal',
                            'readonly',
                            'related',
                            'relationType',
                            'required',
                            'sort',
                            'to',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`field(${fieldName}) on ${model} contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                    if (!this.models[field.to]) {
                        throw new Error(`Relational field(${fieldName}) on ${model} targets to unknown model name "${field.to}".`);
                    }
                    if (field.required && field.relationType !== 'one') {
                        throw new Error(`Relational field(${fieldName}) on ${model} has "required" true with a relation of type "${field.relationType}" but "required" is only supported for "one".`);
                    }
                    if (field.sort && field.relationType !== 'many') {
                        throw new Error(`Relational field "${model}/${fieldName}" has "sort" with a relation of type "${field.relationType}" but "sort" is only supported for "many".`);
                    }
                }
                // 3. Check for redundant attributes on identifying fields.
                if (field.identifying) {
                    if ('readonly' in field) {
                        throw new Error(`Identifying field(${fieldName}) on ${model} has unnecessary "readonly" attribute (readonly is implicit for identifying fields).`);
                    }
                    if ('required' in field && model.identifyingMode === 'and') {
                        throw new Error(`Identifying field(${fieldName}) on ${model} has unnecessary "required" attribute (required is implicit for AND identifying fields).`);
                    }
                }
                // 4. Computed field.
                if (field.compute && !(typeof field.compute === 'string')) {
                    throw new Error(`Property "compute" of field(${fieldName}) on ${model} must be a string (instance method name).`);
                }
                if (field.compute && !(model.prototype[field.compute])) {
                    throw new Error(`Property "compute" of field(${fieldName}) on ${model} does not refer to an instance method of this model.`);
                }
                // 5. Related field.
                if (field.compute && field.related) {
                    throw new Error(`field(${fieldName}) on ${model} cannot be a related and compute field at the same time.`);
                }
                if (field.related) {
                    if (!(typeof field.related === 'string')) {
                        throw new Error(`Property "related" of field(${fieldName}) on ${model} has invalid format.`);
                    }
                    const [relationName, relatedFieldName, other] = field.related.split('.');
                    if (!relationName || !relatedFieldName || other) {
                        throw new Error(`Property "related" of field(${fieldName}) on ${model} has invalid format.`);
                    }
                    // find relation on self or parents.
                    let relatedRelation;
                    let targetModel = model;
                    while (this.models[targetModel.name] && !relatedRelation) {
                        relatedRelation = registry.get(targetModel.name).get('fields').get(relationName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedRelation) {
                        throw new Error(`Related field(${fieldName}) on ${model} relates to unknown relation name "${relationName}".`);
                    }
                    if (relatedRelation.fieldType !== 'relation') {
                        throw new Error(`Related field(${fieldName}) on ${model} relates to non-relational field "${relationName}".`);
                    }
                    // Assuming related relation is valid...
                    // find field name on related model or any parents.
                    const relatedModel = this.models[relatedRelation.to];
                    let relatedField;
                    targetModel = relatedModel;
                    while (this.models[targetModel.name] && !relatedField) {
                        relatedField = registry.get(targetModel.name).get('fields').get(relatedFieldName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedField) {
                        throw new Error(`Related field(${fieldName}) on ${model} relates to unknown related model field "${relatedFieldName}".`);
                    }
                    if (relatedField.fieldType !== field.fieldType) {
                        throw new Error(`Related field(${fieldName}) on ${model} has mismatched type with its related model field.`);
                    }
                    if (
                        relatedField.fieldType === 'relation' &&
                        relatedField.to !== field.to
                    ) {
                        throw new Error(`Related field(${fieldName}) on ${model} has mismatched target model name with its related model field.`);
                    }
                }
            }
        }
    }

    /**
     * @private
     * @throws {Error} in case some fields are not correct.
     */
    _checkProcessedFieldsOnModels() {
        for (const model of Object.values(this.models)) {
            switch (model.identifyingMode) {
                case 'and':
                    break;
                case 'xor':
                    if (model.__identifyingFieldNames.size === 0) {
                        throw new Error(`No identifying fields has been specified for 'xor' identifying mode on ${model}`);
                    }
                    break;
                default:
                    throw new Error(`Unsupported identifying mode "${model.identifyingMode}" on ${model}. Must be one of 'and' or 'xor'.`);
            }
            for (const field of model.__fieldList) {
                const fieldName = field.fieldName;
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`${field} on ${model} has unsupported type ${field.fieldType}.`);
                }
                if (field.compute && field.related) {
                    throw new Error(`${field} on ${model} cannot be a related and compute field at the same time.`);
                }
                if (field.fieldType === 'attribute') {
                    continue;
                }
                if (!field.relationType) {
                    throw new Error(`${field} on ${model} must define a relation type in "relationType".`);
                }
                if (!(['many', 'one'].includes(field.relationType))) {
                    throw new Error(`${field} on ${model} has invalid relation type "${field.relationType}".`);
                }
                if (!field.inverse) {
                    throw new Error(`${field} on ${model} must define an inverse relation name in "inverse".`);
                }
                if (!field.to) {
                    throw new Error(`${field} on ${model} must define a model name in "to" (1st positional parameter of relation field helpers).`);
                }
                const relatedModel = this.models[field.to];
                if (!relatedModel) {
                    throw new Error(`${field} on ${model} defines a relation to model(${field.to}), but there is no model registered with this name.`);
                }
                const inverseField = relatedModel.__fieldMap[field.inverse];
                if (!inverseField) {
                    throw new Error(`${field} on ${model} defines its inverse as field(${field.inverse}) on ${relatedModel}, but it does not exist.`);
                }
                if (inverseField.inverse !== fieldName) {
                    throw new Error(`The name of ${field} on ${model} does not match with the name defined in its inverse ${inverseField} on ${relatedModel}.`);
                }
                if (![model.name, 'Record'].includes(inverseField.to)) {
                    throw new Error(`${field} on ${model} has its inverse ${inverseField} on ${relatedModel} referring to an invalid model (model(${inverseField.to})).`);
                }
            }
            for (const identifyingField of model.__identifyingFieldNames) {
                const field = model.__fieldMap[identifyingField];
                if (!field) {
                    throw new Error(`Identifying field "${identifyingField}" is not a field on ${model}.`);
                }
                if (field.to) {
                    if (field.relationType !== 'one') {
                        throw new Error(`Identifying field "${identifyingField}" on ${model} has a relation of type "${field.relationType}" but identifying field is only supported for "one".`);
                    }
                    const relatedModel = this.models[field.to];
                    const inverseField = relatedModel.__fieldMap[field.inverse];
                    if (!inverseField.isCausal) {
                        throw new Error(`Identifying field "${identifyingField}" on ${model} has an inverse "${field.inverse}" not declared as "isCausal" on ${relatedModel}.`);
                    }
                }
            }
        }
    }

    /**
     * @private
     * @param {Object} model
     * @param {string} localId
     * @returns {Record}
     */
    _create(model, localId) {
        /**
         * Prepare record state. Assign various keys and values that are
         * expected to be found on every record.
         */
        const nonProxyRecord = new model();
        Object.assign(nonProxyRecord, {
            // The unique record identifier.
            localId,
            // Listeners that are bound to this record, to be notified of
            // change in dependencies of compute, related and "on change".
            __listeners: [],
            // Field values of record.
            __values: {},
        });
        const record = owl.markRaw(!this.isDebug ? nonProxyRecord : new Proxy(nonProxyRecord, {
            get: function getFromProxy(record, prop) {
                if (
                    !model.__fieldMap[prop] &&
                    !['_super', 'then', 'localId'].includes(prop) &&
                    typeof prop !== 'symbol' &&
                    !(prop in record)
                ) {
                    console.warn(`non-field read "${prop}" on ${record}`);
                }
                return record[prop];
            },
        }));
        // Ensure X2many relations are Set initially (other fields can stay undefined).
        for (const field of model.__fieldList) {
            record.__values[field.fieldName] = undefined;
            if (field.fieldType === 'relation') {
                if (field.relationType === 'many') {
                    record.__values[field.fieldName] = new RelationSet(record, field);
                }
            }
        }
        if (!this._listenersObservingLocalId.has(localId)) {
            this._listenersObservingLocalId.set(localId, new Map());
        }
        this._listenersObservingFieldOfLocalId.set(localId, new Map());
        for (const field of model.__fieldList) {
            this._listenersObservingFieldOfLocalId.get(localId).set(field, new Map());
        }
        /**
         * Register record.
         */
        model.__records[record.localId] = record;
        /**
         * Auto-bind record methods so that `this` always refer to the record.
         */
        const recordMethods = registry.get(model.name).get('recordMethods');
        for (const methodName of recordMethods.keys()) {
            record[methodName] = record[methodName].bind(record);
        }
        /**
         * Register post processing operation that are to be delayed at
         * the end of the update cycle.
         */
        this._createdRecordsComputes.add(record);
        this._createdRecordsCreated.add(record);
        this._createdRecordsOnChange.add(record);
        for (const [listener, infoList] of this._listenersObservingAllByModel.get(model)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: `_create: allByModel - ${record}`,
                infoList,
            });
        }
        for (const [listener, infoList] of this._listenersObservingLocalId.get(localId)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: `_create: localId - ${record}`,
                infoList,
            });
        }
        return record;
    }

    /**
     * @private
     * @param {Record} record
     */
    _delete(record) {
        this._ensureNoLockingListener();
        const model = record.constructor;
        if (!record.exists()) {
            throw Error(`Cannot delete already deleted record ${record.localId}.`);
        }
        const lifecycleHooks = registry.get(model.name).get('lifecycleHooks');
        if (lifecycleHooks.has('_willDelete')) {
            lifecycleHooks.get('_willDelete').call(record);
        }
        for (const listener of record.__listeners) {
            this.removeListener(listener);
        }
        for (const field of model.__fieldList) {
            if (field.fieldType === 'relation') {
                // ensure inverses are properly unlinked
                field.parseAndExecuteCommands(record, unlinkAll(), { allowWriteReadonly: true });
                if (!record.exists()) {
                    return; // current record might have been deleted from causality
                }
            }
        }
        this._createdRecordsComputes.delete(record);
        this._createdRecordsCreated.delete(record);
        this._createdRecordsOnChange.delete(record);
        this._updatedRecordsCheckRequired.delete(record);
        for (const [listener, infoList] of this._listenersObservingLocalId.get(record.localId)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: `_delete: localId - ${record}`,
                infoList,
            });
        }
        for (const [listener, infoList] of this._listenersObservingAllByModel.get(model)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: `_delete: allByModel - ${record}`,
                infoList,
            });
        }
        delete record.__values;
        delete record.__listeners;
        delete model.__records[record.localId];
        delete record.localId;
    }

    /**
     * Ensures there is currently no locking listener on this model manager, and
     * throws if there is one.
     *
     * @throws {Error}
     */
    _ensureNoLockingListener() {
        for (const listener of this._listeners) {
            if (listener.isLocking) {
                throw Error(`Model manager locked by ${listener}. It is not allowed to insert/update/delete from inside a lock.`);
            }
        }
    }

    /**
     * Executes the compute methods of the created records.
     */
    _executeCreatedRecordsComputes() {
        const hasChanged = this._createdRecordsComputes.size > 0;
        for (const record of this._createdRecordsComputes) {
            // Delete at every step to avoid recursion, indeed compute/related
            // method might trigger an update cycle itself.
            this._createdRecordsComputes.delete(record);
            if (!record.exists()) {
                throw Error(`Cannot start compute/related for already deleted ${record}.`);
            }
            const listeners = [];
            for (const field of record.constructor.__fieldList) {
                if (field.compute) {
                    const listener = new Listener({
                        isPartOfUpdateCycle: true,
                        name: `compute ${field} of ${record}`,
                        onChange: (info) => {
                            this.startListening(listener);
                            const res = record[field.compute]();
                            this.stopListening(listener);
                            this._update(record, { [field.fieldName]: res }, { allowWriteReadonly: true });
                        },
                    });
                    listeners.push(listener);
                }
                if (field.related) {
                    const listener = new Listener({
                        isPartOfUpdateCycle: true,
                        name: `related ${field} of ${record}`,
                        onChange: (info) => {
                            this.startListening(listener);
                            const res = field.computeRelated(record);
                            this.stopListening(listener);
                            this._update(record, { [field.fieldName]: res }, { allowWriteReadonly: true });
                        },
                    });
                    listeners.push(listener);
                }
            }
            record.__listeners.push(...listeners);
            for (const listener of listeners) {
                listener.onChange({
                    listener,
                    reason: `first call on ${record}`,
                });
            }
        }
        if (hasChanged) {
            this._flushUpdateCycle();
        }
    }

    /**
     * Executes the _created method of the created records.
     */
    _executeCreatedRecordsCreated() {
        for (const record of this._createdRecordsCreated) {
            // Delete at every step to avoid recursion, indeed _created might
            // trigger an update cycle itself.
            this._createdRecordsCreated.delete(record);
            if (!record.exists()) {
                throw Error(`Cannot call _created for already deleted ${record}.`);
            }
            const lifecycleHooks = registry.get(record.constructor.name).get('lifecycleHooks');
            if (lifecycleHooks.has('_created')) {
                lifecycleHooks.get('_created').call(record);
            }
        }
    }

    /**
     * Executes the onChange method of the created records.
     */
    _executeCreatedRecordsOnChange() {
        for (const record of this._createdRecordsOnChange) {
            // Delete at every step to avoid recursion, indeed _created
            // might trigger an update cycle itself.
            this._createdRecordsOnChange.delete(record);
            if (!record.exists()) {
                throw Error(`Cannot call onChange for already deleted ${record}.`);
            }
            for (const onChange of registry.get(record.constructor.name).get('onChanges')) {
                const listener = new Listener({
                    name: `${onChange} of ${record}`,
                    onChange: (info) => {
                        this.startListening(listener);
                        for (const dependency of onChange.dependencies) {
                            followRelations(record, dependency);
                        }
                        this.stopListening(listener);
                        record[onChange.methodName]();
                    },
                });
                record.__listeners.push(listener);
                listener.onChange({
                    listener,
                    reason: `first call on ${record}`,
                });
                if (!record.exists()) {
                    break; // onChange might have deleted the record, other onChange shouldn't be executed
                }
            }
        }
    }


    /**
     * Executes the check of the required field of updated records.
     */
    _executeUpdatedRecordsCheckRequired() {
        for (const record of this._updatedRecordsCheckRequired) {
            for (const required of record.constructor.__requiredFieldsList) {
                if (record[required.fieldName] === undefined) {
                    throw Error(`required ${required} of ${record} is missing`);
                }
            }
        }
        this._updatedRecordsCheckRequired.clear();
    }

    /**
     * Terminates an update cycle by executing its pending operations: execute
     * computed fields, execute life-cycle hooks, update rev numbers.
     *
     * @private
     */
    _flushUpdateCycle() {
        this._executeCreatedRecordsComputes();
        this._notifyListenersInUpdateCycle();
        this._executeUpdatedRecordsCheckRequired();
        this._executeCreatedRecordsCreated();
        this._executeCreatedRecordsOnChange();
        this._notifyListenersAfterUpdateCycle();
    }

    /**
     * @private
     * @returns {Object}
     */
    _generateModels() {
        // Create the model through a class to give it a meaningful name to be
        // displayed in stack traces and stuff.
        const model = { 'Record': class {} }['Record'];
        this._applyModelDefinition(model);
        // Record is generated separately and before the other models since
        // it is the dependency of all of them.
        const allModelNamesButRecord = [...registry.keys()].filter(name => name !== 'Record');
        for (const modelName of allModelNamesButRecord) {
            const model = { [modelName]: class extends this.models['Record'] {} }[modelName];
            this._applyModelDefinition(model);
        }
        /**
         * Check that fields on the generated models are correct.
         */
        this._checkDeclaredFieldsOnModels();
        /**
         * Process declared model fields definitions, so that these field
         * definitions are much easier to use in the system. For instance, all
         * relational field definitions have an inverse.
         */
        this._processDeclaredFieldsOnModels();
        /**
         * Check that all model fields are correct, notably one relation
         * should have matching reversed relation.
         */
        this._checkProcessedFieldsOnModels();
    }

    /**
     * Returns an index on the given model for the given data.
     *
     * @param {Object} model
     * @param {Object|Record} data insert data or record
     * @returns {string}
     */
    _getRecordIndex(model, data) {
        const parts = [];
        switch (model.identifyingMode) {
            case 'and':
                for (const fieldName of model.__identifyingFieldNames) {
                    const fieldValue = this._getValueFromDataOrFromDefault(model, fieldName, data);
                    if (fieldValue === undefined) {
                        throw new Error(`Identifying field "${fieldName}" is lacking a value on ${model} with 'and' identifying mode`);
                    }
                    parts.push(this._getRecordIndexFromField(model, fieldName, fieldValue));
                }
                break;
            case 'xor': {
                const [fieldName, fieldValue] = [...model.__identifyingFieldNames].reduce(([fieldName, fieldValue], currentFieldName) => {
                    const currentFieldValue = this._getValueFromDataOrFromDefault(model, currentFieldName, data);
                    if (currentFieldValue === undefined) {
                        return [fieldName, fieldValue];
                    }
                    if (fieldName) {
                        throw new Error(`Identifying field on ${model} with 'xor' identifying mode should have only one of the conditional values given in data. Currently have both "${fieldName}" and "${currentFieldName}".`);
                    }
                    return [currentFieldName, currentFieldValue];
                }, [undefined, undefined]);
                parts.push(this._getRecordIndexFromField(model, fieldName, fieldValue));
                break;
            }
        }
        return `${model.name}(${parts.join(', ')})`;
    }

    /**
     * Returns the part of the record index that comes from the given fieldName
     * with the given fieldValue.
     *
     * @param {Object} model
     * @param {string} fieldName
     * @param {any} fieldValue
     * @returns {string}
     */
    _getRecordIndexFromField(model, fieldName, fieldValue) {
        const relationTo = model.__fieldMap[fieldName].to;
        if (!relationTo) {
            return `${fieldName}: ${fieldValue}`;
        }
        const OtherModel = this.models[relationTo];
        if (fieldValue instanceof OtherModel) {
            return `${fieldName}: ${this._getRecordIndex(OtherModel, fieldValue)}`;
        }
        const fieldValue2 = model.__fieldMap[fieldName].convertToFieldCommandList(fieldValue)[0];
        if (!(fieldValue2 instanceof FieldCommand)) {
            throw new Error(`Identifying element "${model}/${fieldName}" is expecting a command for relational field.`);
        }
        if (!['link', 'insert', 'replace', 'insert-and-replace'].includes(fieldValue2._name)) {
            throw new Error(`Identifying element "${model}/${fieldName}" is expecting a command of type "insert-and-replace", "replace", "insert" or "link". "${fieldValue2._name}" was given instead.`);
        }
        const relationValue = fieldValue2._value;
        if (!relationValue) {
            throw new Error(`Identifying element "${model}/${fieldName}" is lacking a relation value.`);
        }
        return `${fieldName}: ${this._getRecordIndex(OtherModel, relationValue)}`;
    }

    /**
     * Returns the value for the given fieldName from the provided data if it is
     * defined or from default value of this field otherwise.
     *
     * @param {Object} model
     * @param {string} fieldName
     * @param {Object} data
     * @returns {any}
     */
    _getValueFromDataOrFromDefault(model, fieldName, data) {
        if (data[fieldName] !== undefined) {
            return data[fieldName];
        }
        return model.__fieldMap[fieldName].default;
    }

    /**
     * @private
     * @param {Object} model
     * @param {Object[]} dataList
     * @param {Object} [options={}]
     * @returns {Record[]}
     */
    _insert(model, dataList, options = {}) {
        this._ensureNoLockingListener();
        const records = [];
        for (const data of dataList) {
            const localId = this._getRecordIndex(model, data);
            let record = this.get(model, localId);
            if (!record) {
                record = this._create(model, localId);
                this._update(record, this._addDefaultData(model, data), { ...options, allowWriteReadonly: true });
            } else {
                this._update(record, data, options);
            }
            records.push(record);
        }
        return records;
    }

    /**
     * @private
     * @param {Object} model
     * @param {ModelField} field
     * @returns {ModelField}
     */
    _makeInverseRelationField(model, field) {
        const inverseField = new ModelField(Object.assign(
            {},
            ModelField.many(model.name, { inverse: field.fieldName }),
            {
                fieldName: `_inverse_${model}/${field.fieldName}`,
                // Allows the inverse of an identifying field to be
                // automatically generated.
                isCausal: field.identifying,
                model: this.models[field.to],
            },
        ));
        return inverseField;
    }

    /**
     * Marks the given listener to be notified. This function should be called
     * when the dependencies of a listener have changed, in order to inform the
     * listener of the change at the proper time during the update cycle
     * (according to its configuration).
     *
     * @private
     * @param {Object} listener
     */
    _markListenerToNotify(listener, info) {
        if (!(listener instanceof Listener)) {
            throw new Error(`Listener is not a listener ${listener}`);
        }
        if (listener.isPartOfUpdateCycle) {
            const entry = this._listenersToNotifyInUpdateCycle.get(listener);
            if (entry) {
                entry.push(info);
            } else {
                this._listenersToNotifyInUpdateCycle.set(listener, [info]);
            }
        }
        if (!listener.isPartOfUpdateCycle) {
            const entry = this._listenersToNotifyAfterUpdateCycle.get(listener);
            if (entry) {
                entry.push(info);
            } else {
                this._listenersToNotifyAfterUpdateCycle.set(listener, [info]);
            }
        }
    }

    /**
     * Marks the given field of the given record as changed.
     *
     * @param {Record} record
     * @param {ModelField} field
     */
    _markRecordFieldAsChanged(record, field) {
        for (const [listener, infoList] of this._listenersObservingFieldOfLocalId.get(record.localId).get(field)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: `_update: ${field} of ${record}`,
                infoList,
            });
        }
    }

    /**
     * Notifies the listeners that have been flagged to be notified and for
     * which the `onChange` function was defined to be called after the update
     * cycle.
     *
     * In particular this is the case of components using models that need to
     * re-render and for records with "on change".
     *
     * @returns {boolean} whether any change happened
     */
    _notifyListenersAfterUpdateCycle() {
        for (const [listener, infoList] of this._listenersToNotifyAfterUpdateCycle) {
            this._listenersToNotifyAfterUpdateCycle.delete(listener);
            listener.onChange(infoList);
        }
    }

    /**
     * Notifies the listeners that have been flagged to be notified and for
     * which the `onChange` function was defined to be called while still in the
     * update cycle.
     *
     * In particular this is the case of records with compute or related fields.
     *
     * Note: A double loop is used because calling the `onChange` function might
     * lead to more listeners being flagged to be notified.
     *
     * @returns {boolean} whether any change happened
     */
    _notifyListenersInUpdateCycle() {
        const hasChanged = this._listenersToNotifyInUpdateCycle.size > 0;
        for (const [listener, infoList] of this._listenersToNotifyInUpdateCycle) {
            this._listenersToNotifyInUpdateCycle.delete(listener);
            listener.onChange(infoList);
        }
        if (hasChanged) {
            this._flushUpdateCycle();
        }
    }

    /**
     * This function processes definition of declared fields in provided models.
     * Basically, models have fields declared in static prop `fields`, and this
     * function processes and modifies them in place so that they are fully
     * configured. For instance, model relations need bi-directional mapping, but
     * inverse relation may be omitted in declared field: this function auto-fill
     * this inverse relation.
     *
     * @private
     */
    _processDeclaredFieldsOnModels() {
        /**
         * 1. Prepare fields.
         */
        for (const model of Object.values(this.models)) {
            const sumContributionsByFieldName = new Map();
            // Make fields aware of their field name.
            for (const [fieldName, fieldData] of registry.get(model.name).get('fields')) {
                model.fields[fieldName] = new ModelField(Object.assign({}, fieldData, {
                    fieldName,
                    model,
                }));
                if (fieldData.sum) {
                    const [relationFieldName, contributionFieldName] = fieldData.sum.split('.');
                    if (!sumContributionsByFieldName.has(relationFieldName)) {
                        sumContributionsByFieldName.set(relationFieldName, []);
                    }
                    sumContributionsByFieldName.get(relationFieldName).push({
                        from: contributionFieldName,
                        to: fieldName,
                    });
                }
            }
            for (const [fieldName, sumContributions] of sumContributionsByFieldName) {
                model.fields[fieldName].sumContributions = sumContributions;
            }
        }
        /**
         * 2. Auto-generate definitions of undeclared inverse relations.
         */
        for (const model of Object.values(this.models)) {
            for (const field of Object.values(model.fields)) {
                if (field.fieldType !== 'relation') {
                    continue;
                }
                if (field.inverse) {
                    continue;
                }
                const relatedModel = this.models[field.to];
                const inverseField = this._makeInverseRelationField(model, field);
                field.inverse = inverseField.fieldName;
                relatedModel.fields[inverseField.fieldName] = inverseField;
            }
        }
        /**
         * 3. Extend definition of fields of a model with the definition of
         * fields of its parents.
         */
        for (const model of Object.values(this.models)) {
            model.__combinedFields = {};
            for (const field of Object.values(model.fields)) {
                model.__combinedFields[field.fieldName] = field;
            }
            let TargetModel = model.__proto__;
            while (TargetModel && TargetModel.fields) {
                for (const targetField of Object.values(TargetModel.fields)) {
                    const field = model.__combinedFields[targetField.fieldName];
                    if (!field) {
                        model.__combinedFields[targetField.fieldName] = targetField;
                    }
                }
                TargetModel = TargetModel.__proto__;
            }
        }
        /**
         * 4. Register final fields and make field accessors, to redirects field
         * access to field getter and to prevent field from being written
         * without calling update (which is necessary to process update cycle).
         */
        for (const model of Object.values(this.models)) {
            // Object with fieldName/field as key/value pair, for quick access.
            model.__fieldMap = model.__combinedFields;
            // List of all fields, for iterating.
            model.__fieldList = Object.values(model.__fieldMap);
            model.__requiredFieldsList = model.__fieldList.filter(
                field => field.required
            );
            model.__identifyingFieldNames = new Set();
            for (const [fieldName, field] of Object.entries(model.__fieldMap)) {
                if (field.identifying) {
                    model.__identifyingFieldNames.add(fieldName);
                }
                // Add field accessors.
                Object.defineProperty(model.prototype, fieldName, {
                    get: function getFieldValue() { // this is bound to record
                        const field = model.__fieldMap[fieldName];
                        if (this.modelManager._listeners.size) {
                            if (!this.modelManager._listenersObservingLocalId.has(this.localId)) {
                                this.modelManager._listenersObservingLocalId.set(this.localId, new Map());
                            }
                            const entryLocalId = this.modelManager._listenersObservingLocalId.get(this.localId);
                            const reason = `getField - ${field} of ${this}`;
                            const entryField = this.modelManager._listenersObservingFieldOfLocalId.get(this.localId).get(field);
                            for (const listener of this.modelManager._listeners) {
                                listener.lastObservedLocalIds.add(this.localId);
                                const info = { listener, reason };
                                if (entryLocalId.has(listener)) {
                                    entryLocalId.get(listener).push(info);
                                } else {
                                    entryLocalId.set(listener, [info]);
                                }
                                if (!listener.lastObservedFieldsByLocalId.has(this.localId)) {
                                    listener.lastObservedFieldsByLocalId.set(this.localId, new Set());
                                }
                                listener.lastObservedFieldsByLocalId.get(this.localId).add(field);
                                if (entryField.has(listener)) {
                                    entryField.get(listener).push(info);
                                } else {
                                    entryField.set(listener, [info]);
                                }
                            }
                        }
                        return field.get(this);
                    },
                });
            }
            delete model.__combinedFields;
        }
    }

    /**
     * @private
     * @param {Record} record
     * @param {Object} data
     * @param {Object} [options={}]
     * @param {boolean} [options.allowWriteReadonly=false]
     * @returns {boolean} whether any value changed for the current record
     */
    _update(record, data, options = {}) {
        this._ensureNoLockingListener();
        if (!record.exists()) {
            throw Error(`Cannot update already deleted record ${record.localId}.`);
        }
        const { allowWriteReadonly = false } = options;
        const model = record.constructor;
        let hasChanged = false;
        const sortedFieldNames = Object.keys(data);
        sortedFieldNames.sort((a, b) => {
            // Always update identifying fields first because updating other relational field will
            // trigger update of inverse field, which will require this identifying fields to be set
            // beforehand to properly detect whether this is already linked or not on the inverse.
            if (model.__identifyingFieldNames.has(a) && !model.__identifyingFieldNames.has(b)) {
                return -1;
            }
            if (!model.__identifyingFieldNames.has(a) && model.__identifyingFieldNames.has(b)) {
                return 1;
            }
            return 0;
        });
        for (const fieldName of sortedFieldNames) {
            if (data[fieldName] === undefined) {
                // `undefined` should have the same effect as not passing the field
                continue;
            }
            const field = model.__fieldMap[fieldName];
            if (!field) {
                throw new Error(`Cannot create/update record with data unrelated to a field. (record: "${record.localId}", non-field attempted update: "${fieldName}")`);
            }
            const newVal = data[fieldName];
            if (!field.parseAndExecuteCommands(record, newVal, options)) {
                continue;
            }
            if (field.readonly && !allowWriteReadonly) {
                throw new Error(`read-only ${field} on ${record} was updated`);
            }
            hasChanged = true;
            this._markRecordFieldAsChanged(record, field);
        }
        if (hasChanged) {
            this._updatedRecordsCheckRequired.add(record);
        }
        return hasChanged;
    }

}
