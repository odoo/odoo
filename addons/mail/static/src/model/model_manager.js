/** @odoo-module **/

import { IS_RECORD, patchesAppliedPromise, registry } from '@mail/model/model_core';
import { ModelGenerator } from '@mail/model/model_generator';
import { FieldCommand, unlinkAll } from '@mail/model/model_field_command';
import { RelationSet } from '@mail/model/model_field_relation_set';
import { Listener } from '@mail/model/model_listener';
import { RecordInfo } from '@mail/model/record_info';
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
        this.created = makeDeferred();
        /**
         * Promise which becomes resolved when messaging is initialized. Useful
         * for waiting before accessing `this.messaging`.
         */
        this.initialized = makeDeferred();

        this.generator = new ModelGenerator(this);

        //----------------------------------------------------------------------
        // Various variables that are necessary to handle an update cycle. The
        // goal of having an update cycle is to delay the execution of computes,
        // life-cycle hooks and potential UI re-renders until the last possible
        // moment, for performance reasons.
        //----------------------------------------------------------------------

        this.cycle = {
            /**
             * Set of records that have been created during the current update
             * cycle and for which the compute/related methods still have to be
             * executed a first time.
             */
            newCompute: new Set(),
            /**
             * Set of records that have been created during the current update
             * cycle and for which the _created method still has to be executed.
             */
            newCreated: new Set(),
            /**
             * Set of records that have been created during the current update
             * cycle and for which the onChange methods still have to be executed
             * a first time.
             */
            newOnChange: new Set(),
            /**
             * Map of listeners that should be notified as part of the current
             * update cycle. Value contains list of info to help for debug.
             */
            notifyNow: new Map(),
            /**
             * Map of listeners that should be notified at the end of the current
             * update cycle. Value contains list of info to help for debug.
             */
            notifyAfter: new Map(),
            /**
             * Set of records that have been updated during the current update cycle
             * and for which required fields check still has to be executed.
             */
            check: new Set(),
        };
        this.recordInfos = {};
        /**
         * Set of active listeners. Useful to be able to register which records
         * or fields they accessed to be able to notify them when those change.
         */
        this._listeners = new Set();
        /**
         * Map between model and a set of listeners that are using all() on that
         * model.
         */
        this.listenersAll = new Map();
        /**
         * All generated models. Keys are model name, values are model class.
         */
        this.models = {};
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
        await patchesAppliedPromise;
        this.generator.start();
        /**
         * Create the messaging singleton record.
         */
        this.models['Messaging'].insert(values);
        this.created.resolve();
        await this.messaging.start();
        this.initialized.resolve();
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
            listener.alls.add(model);
            const entry = this.listenersAll.get(model);
            const info = {
                listener,
                reason: this.isDebug && `all() - ${model}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        const allRecords = [...model.__records];
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
        this.flush();
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
        return model.__records.has(record);
    }

    /**
     * Gets the unique record of provided model that matches the given
     * identifying data, if it exists.
     *
     * @param {Object} model
     * @param {Object} [data={}]
     * @returns {Record|undefined}
     */
    findFromIdentifyingData(model, data = {}) {
        this.preinsert(model, data);
        const record = model.__recordsIndex.findRecord(data);
        if (!record) {
            return;
        }
        for (const listener of this._listeners) {
            listener.records.add(record);
            const entry = this.recordInfos[record.localId].listenersOnRecord;
            const info = {
                listener,
                reason: this.isDebug && `findFromIdentifyingData record - ${record}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        return record;
    }

    /**
     * Returns the messaging record once it is initialized. This method should
     * be considered the main entry point to the messaging system for outside
     * code.
     *
     * @returns {Messaging}
     **/
    async getMessaging() {
        await this.created;
        await this.initialized;
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
        this.flush();
        return isMulti ? records : records[0];
    }

    /**
     * This method creates or updates records, based on provided data. This
     * method assumes that records are uniquely identifiable per "unique find"
     * criteria from data on model.
     *
     * @param {Object} data
     * ```javascript
     * {
     *     Partner: {
     *         ...
     *     },
     *     Guest: [{
     *         ...
     *     }]
     * }
     * ```
     * @returns void
     */
    multiModelInsert(data) {
        for (const [modelName, recordsData] of Object.entries(data)) {
            const isMulti = typeof recordsData[Symbol.iterator] === 'function';
            this._insert(this.models[modelName], isMulti ? recordsData : [recordsData]);
        }
        this.flush();
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
        this.cycle.notifyNow.delete(listener);
        this.cycle.notifyAfter.delete(listener);
        for (const record of listener.records) {
            if (!record.exists()) {
                continue;
            }
            this.recordInfos[record.localId].listenersOnRecord.delete(listener);
            const listenersOnField = record.__listenersOnField;
            for (const field of listener.fields.get(record) || []) {
                listenersOnField.get(field).delete(listener);
            }
        }
        for (const model of listener.alls) {
            this.listenersAll.get(model).delete(listener);
        }
        listener.records.clear();
        listener.fields.clear();
        listener.alls.clear();
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
        this.flush();
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
     * @private
     * @param {Object} model
     * @returns {Record}
     */
    _create(model) {
        const localId = `${model.name}_${++model.__recordCount}`;
        /**
         * Prepare record state. Assign various keys and values that are
         * expected to be found on every record.
         */
        const nonProxyRecord = new model();
        Object.assign(nonProxyRecord, {
            // The unique record identifier.
            localId,
            /**
             * Map between fields and a Map between listeners that are observing
             * the field and array of information about how the field is observed.
             */
            __listenersOnField: new Map(),
            // Field values of record.
            __values: new Map(),
            [IS_RECORD]: true,
        });
        const record = owl.markRaw(!this.isDebug ? nonProxyRecord : new Proxy(nonProxyRecord, {
            get: function getFromProxy(record, prop) {
                if (
                    (model.__fieldMap && !model.__fieldMap.has(prop)) &&
                    !['_super', 'then', 'localId'].includes(prop) &&
                    typeof prop !== 'symbol' &&
                    !(prop in record)
                ) {
                    console.warn(`non-field read "${prop}" on ${record}`);
                }
                return record[prop];
            },
        }));
        this.recordInfos[localId] = new RecordInfo({ record });
        if (this.isDebug) {
            record.__proxifiedRecord = record;
        }
        // Ensure X2many relations are Set initially (other fields can stay undefined).
        for (const field of model.__fieldList) {
            if (field.fieldType === 'relation') {
                if (field.relationType === 'many') {
                    record.__values.set(field.fieldName, new RelationSet(this, record, field));
                }
            }
        }
        /**
         * Register record.
         */
        model.__records.add(record);
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
        this.cycle.newCompute.add(record);
        this.cycle.newCreated.add(record);
        this.cycle.newOnChange.add(record);
        for (const [listener, infoList] of this.listenersAll.get(model)) {
            this.markToNotify(listener, {
                listener,
                reason: this.isDebug && `_create: allByModel - ${record}`,
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
        if (this.isDebug) {
            this._ensureNoLockingListener();
        }
        const model = record.constructor;
        if (!record.exists()) {
            throw Error(`Cannot delete already deleted record ${record}.`);
        }
        const lifecycleHooks = registry.get(model.name).get('lifecycleHooks');
        if (lifecycleHooks.has('_willDelete')) {
            lifecycleHooks.get('_willDelete').call(record);
        }
        for (const listener of this.recordInfos[record.localId].listeners) {
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
        model.__recordsIndex.removeRecord(record);
        this.cycle.newCompute.delete(record);
        this.cycle.newCreated.delete(record);
        this.cycle.newOnChange.delete(record);
        this.cycle.check.delete(record);
        for (const [listener, infoList] of this.recordInfos[record.localId].listenersOnRecord) {
            this.markToNotify(listener, {
                listener,
                reason: this.isDebug && `_delete: record - ${record}`,
                infoList,
            });
        }
        for (const [listener, infoList] of this.listenersAll.get(model)) {
            this.markToNotify(listener, {
                listener,
                reason: this.isDebug && `_delete: allByModel - ${record}`,
                infoList,
            });
        }
        delete record.__values;
        delete this.recordInfos[record.localId].listeners;
        delete this.recordInfos[record.localId].listenersOnRecord;
        delete record.__listenersOnField;
        model.__records.delete(record);
        delete this.recordInfos[record.localId];
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
    doNewCompute() {
        const hasChanged = this.cycle.newCompute.size > 0;
        for (const record of this.cycle.newCompute) {
            // Delete at every step to avoid recursion, indeed compute/related
            // method might trigger an update cycle itself.
            this.cycle.newCompute.delete(record);
            if (!record.exists()) {
                throw Error(`Cannot start compute/related for already deleted ${record}.`);
            }
            const listeners = [];
            for (const field of record.constructor.__fieldList) {
                if (field.compute) {
                    const listener = new Listener({
                        name: `compute ${field} of ${record}`,
                        type: 'compute',
                        onChange: (info) => {
                            this.startListening(listener);
                            const res = field.compute.call(record);
                            this.stopListening(listener);
                            this._update(record, { [field.fieldName]: res }, { allowWriteReadonly: true });
                        },
                    });
                    listeners.push(listener);
                }
                if (field.related) {
                    const listener = new Listener({
                        name: `related ${field} of ${record}`,
                        type: 'related',
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
            this.recordInfos[record.localId].listeners.push(...listeners);
            for (const listener of listeners) {
                listener.onChange({
                    listener,
                    reason: this.isDebug && `first call on ${record}`,
                });
            }
        }
        if (hasChanged) {
            this.flush();
        }
    }

    /**
     * Executes the _created method of the created records.
     */
    doNewCreated() {
        for (const record of this.cycle.newCreated) {
            // Delete at every step to avoid recursion, indeed _created might
            // trigger an update cycle itself.
            this.cycle.newCreated.delete(record);
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
    doNewOnChange() {
        for (const record of this.cycle.newOnChange) {
            // Delete at every step to avoid recursion, indeed _created
            // might trigger an update cycle itself.
            this.cycle.newOnChange.delete(record);
            if (!record.exists()) {
                throw Error(`Cannot call onChange for already deleted ${record}.`);
            }
            for (const onChange of registry.get(record.constructor.name).get('onChanges')) {
                const listener = new Listener({
                    name: `${onChange} of ${record}`,
                    type: 'onChange',
                    onChange: (info) => {
                        this.startListening(listener);
                        for (const dependency of onChange.dependencies) {
                            this.followRelations(record, dependency);
                        }
                        this.stopListening(listener);
                        record[onChange.methodName]();
                    },
                });
                this.recordInfos[record.localId].listeners.push(listener);
                listener.onChange({
                    listener,
                    reason: this.isDebug && `first call on ${record}`,
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
    doCheck() {
        for (const record of this.cycle.check) {
            for (const required of record.constructor.__requiredFieldsList) {
                if (record[required.fieldName] === undefined) {
                    throw Error(`required ${required} of ${record} is missing`);
                }
            }
        }
        this.cycle.check.clear();
    }

    /**
     * Terminates an update cycle by executing its pending operations: execute
     * computed fields, execute life-cycle hooks, update rev numbers.
     */
    flush() {
        this.doNewCompute();
        this.doNotifyNow();
        this.doCheck();
        this.doNewCreated();
        this.doNewOnChange();
        this.doNotifyAfter();
    }

    /**
     * Follows the given related path starting from the given record, and returns
     * the resulting value, or undefined if a relation can't be followed because it
     * is undefined.
     *
     * @param {Record} record
     * @param {string[]} relatedPath Array of field names.
     * @returns {any}
     */
    followRelations(record, relatedPath) {
        let target = record;
        for (const field of relatedPath) {
            target = target[field];
            if (!target) {
                break;
            }
        }
        return target;
    }

    /**
     * @private
     * @param {Object} model
     * @param {Object[]} dataList
     * @param {Object} [options={}]
     * @returns {Record[]}
     */
    _insert(model, dataList, options = {}) {
        if (this.isDebug) {
            this._ensureNoLockingListener();
        }
        const records = [];
        for (const data of dataList) {
            let record = this.findFromIdentifyingData(model, data);
            if (!record) {
                const data2 = this._addDefaultData(model, data);
                this.preinsert(model, data2);
                record = this._create(model);
                model.__recordsIndex.addRecord(record, data2);
                this._update(record, data2, { ...options, allowWriteReadonly: true });
            } else {
                this._update(record, data, options);
            }
            records.push(record);
        }
        return records;
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
    markToNotify(listener, info) {
        if (!(listener instanceof Listener)) {
            throw new Error(`Listener is not a listener ${listener}`);
        }
        if (listener.isPartOfUpdateCycle) {
            const entry = this.cycle.notifyNow.get(listener);
            if (entry) {
                entry.push(info);
            } else {
                this.cycle.notifyNow.set(listener, [info]);
            }
        }
        if (!listener.isPartOfUpdateCycle) {
            const entry = this.cycle.notifyAfter.get(listener);
            if (entry) {
                entry.push(info);
            } else {
                this.cycle.notifyAfter.set(listener, [info]);
            }
        }
    }

    /**
     * Marks the given field of the given record as changed.
     *
     * @param {Record} record
     * @param {ModelField} field
     */
    markAsChanged(record, field) {
        for (const [listener, infoList] of record.__listenersOnField.get(field) || []) {
            this.markToNotify(listener, {
                listener,
                reason: this.isDebug && `_update: ${field} of ${record}`,
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
    doNotifyAfter() {
        for (const [listener, infoList] of this.cycle.notifyAfter) {
            this.cycle.notifyAfter.delete(listener);
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
    doNotifyNow() {
        const hasChanged = this.cycle.notifyNow.size > 0;
        for (const [listener, infoList] of this.cycle.notifyNow) {
            this.cycle.notifyNow.delete(listener);
            listener.onChange(infoList);
        }
        if (hasChanged) {
            this.flush();
        }
    }

    /**
     * Processes all commands given in data that concerns relation fields that
     * are identifying to execute their respective "insert-and-replace" commands
     * and to replace them by corresponding "replace" commands.
     *
     * @param {Object} model
     * @param {Object} data
     */
    preinsert(model, data) {
        for (const fieldName of model.__identifyingFieldNames) {
            if (data[fieldName] === undefined) {
                continue;
            }
            const field = model.__fieldMap.get(fieldName);
            if (!field.to) {
                continue;
            }
            const commands = field.convertToFieldCommandList(data[fieldName]);
            if (commands.length !== 1) {
                throw new Error(`Identifying field "${model}/${fieldName}" should receive a single command.`);
            }
            const [command] = commands;
            if (!(command instanceof FieldCommand)) {
                throw new Error(`Identifying field "${model}/${fieldName}" should receive a command.`);
            }
            if (!['insert-and-replace', 'replace'].includes(command._name)) {
                throw new Error(`Identifying field "${model}/${fieldName}" should receive a "replace" or "insert-and-replace" command.`);
            }
            if (command._name === 'replace') {
                continue;
            }
            if (!command._value) {
                throw new Error(`Identifying field "${model}/${fieldName}" is lacking a relation value.`);
            }
            if (typeof command._value[Symbol.iterator] === 'function') {
                throw new Error(`Identifying field "${model}/${fieldName}" should receive a single data object.`);
            }
            const [record] = this._insert(this.models[field.to], [command._value]);
            data[fieldName] = record;
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
        if (this.isDebug) {
            this._ensureNoLockingListener();
        }
        if (this.isDebug && !record.exists()) {
            throw Error(`Cannot update already deleted record ${record}.`);
        }
        const { allowWriteReadonly = false } = options;
        const model = record.constructor;
        let hasChanged = false;
        for (const fieldName of Object.keys(data)) {
            if (data[fieldName] === undefined) {
                // `undefined` should have the same effect as not passing the field
                continue;
            }
            const field = model.__fieldMap.get(fieldName);
            if (!field) {
                console.warn(`Cannot create/update record with data unrelated to a field. (record: "${record}", non-field attempted update: "${fieldName}")`);
                continue;
            }
            const newVal = data[fieldName];
            if (!field.parseAndExecuteCommands(record, newVal, options)) {
                continue;
            }
            if (field.readonly && !allowWriteReadonly) {
                console.warn(`read-only ${field} on ${record} was updated`);
            }
            hasChanged = true;
            this.markAsChanged(record, field);
        }
        if (hasChanged) {
            this.cycle.check.add(record);
        }
        return hasChanged;
    }

}
