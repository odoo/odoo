/** @odoo-module **/

import { registry } from '@mail/model/model_core';
import { ModelField } from '@mail/model/model_field';
import { Listener } from '@mail/model/model_listener';
import { patchClassMethods, patchInstanceMethods } from '@mail/utils/utils';
import { link, unlinkAll } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred/deferred';

/**
 * Object that manage models and records, notably their update cycle: whenever
 * some records are requested for update (either with model static method
 * `create()` or record method `update()`), this object processes them with
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
         * cycle. Useful to trigger `_created()` hook methods.
         */
        this._createdRecords = new Set();
        /**
         * States whether an update cycle is currently in progress. The update
         * cycle is considered in progress while there are computed fields still
         * to compute or required fields for which to verify the existence.
         * Life cycle hooks such as `_created()` or "on change" computes are not
         * considerer part of the update cycle by this variable.
         * The main goal of this variable is to detect programming errors: to
         * prevent from calling create/update/delete from inside a compute.
         */
        this._isInUpdateCycle = false;
        /**
         * Set of active listeners. Useful to be able to register which records
         * or fields they accessed to be able to notify them when those change.
         */
        this._listeners = new Set();
        /**
         * Map between Model and a set of listeners that are using all() on that
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
         * Map between listeners and a set of localId that they are using.
         * Useful for easily being able to clean up a listener without having to
         * iterate all localId to be able to find which are using it.
         */
        this._localIdsObservedByListener = new Map();
        /**
         * The messaging singleton associated to this model manager.
         */
        this._messaging = undefined;
        /**
         * All generated models. Keys are model name, values are model class.
         */
        this.models = {};
        /**
         * Set of records that have been updated during the current update
         * cycle.
         */
        this._updatedRecords = new Set();
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
        /**
         * Some models require session data, like locale text direction (depends on
         * fully loaded translation).
         */
        await this.env.session.is_bound;
        /**
         * Generate the models.
         */
        this.models = this._generateModels();
        /**
         * Create the messaging singleton record.
         */
        this.models['mail.messaging'].create(values);
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
     * @param {mail.model} Model class
     * @param {function} [filterFunc]
     * @returns {mail.model[]} records matching criteria.
     */
    all(Model, filterFunc) {
        for (const listener of this._listeners) {
            const entry = this._listenersObservingAllByModel.get(Model);
            const info = {
                error: Error(),
                reason: `all() - ${Model}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        const allRecords = Object.values(Model.__records);
        if (filterFunc) {
            return allRecords.filter(filterFunc);
        }
        return allRecords;
    }

    /**
     * Register a record that has been created, and manage update of records
     * from this record creation.
     *
     * @param {mail.model} Model class
     * @param {Object|Object[]} [data={}]
     *  If data is an iterable, multiple records will be created.
     * @returns {mail.model|mail.model[]} newly created record(s)
     */
    create(Model, data = {}) {
        const res = this._create(Model, data);
        this._flushUpdateCycle();
        return res;
    }

    /**
     * Delete the record. After this operation, it's as if this record never
     * existed. Note that relation are removed, which may delete more relations
     * if some of them are causal.
     *
     * @param {mail.model} record
     */
    delete(record) {
        this._delete(record);
        this._flushUpdateCycle();
    }

    /**
     * Returns whether the given record still exists.
     *
     * @param {mail.model} Model class
     * @param {mail.model} record
     * @returns {boolean}
     */
    exists(Model, record) {
        return Model.__records[record.localId] ? true : false;
    }

    /**
     * Get the record of provided model that has provided
     * criteria, if it exists.
     *
     * @param {mail.model} Model class
     * @param {function} findFunc
     * @returns {mail.model|undefined} the record of model matching criteria, if
     *   exists.
     */
    find(Model, findFunc) {
        return this.all(Model).find(findFunc);
    }

    /**
     * Gets the unique record of provided model that matches the given
     * identifying data, if it exists.
     * @see `_createRecordLocalId` for criteria of identification.
     *
     * @param {mail.model} Model class
     * @param {Object} data
     * @returns {mail.model|undefined}
     */
    findFromIdentifyingData(Model, data) {
        const localId = Model._createRecordLocalId(data);
        return Model.get(localId);
    }

    /**
     * This method returns the record of provided model that matches provided
     * local id. Useful to convert a local id to a record.
     * Note that even if there's a record in the system having provided local
     * id, if the resulting record is not an instance of this model, this getter
     * assumes the record does not exist.
     *
     * @param {mail.model} Model class
     * @param {string} localId
     * @param {Object} param2
     * @param {boolean} [param2.isCheckingInheritance=false]
     * @returns {mail.model|undefined} record, if exists
     */
    get(Model, localId, { isCheckingInheritance = false } = {}) {
        if (!localId) {
            return;
        }
        for (const listener of this._listeners) {
            this._localIdsObservedByListener.get(listener).add(localId);
            if (!this._listenersObservingLocalId.has(localId)) {
                this._listenersObservingLocalId.set(localId, new Map());
            }
            const entry = this._listenersObservingLocalId.get(localId);
            const info = {
                error: Error(),
                reason: `get record - ${localId}`,
            };
            if (entry.has(listener)) {
                entry.get(listener).push(info);
            } else {
                entry.set(listener, [info]);
            }
        }
        const record = Model.__records[localId];
        if (record) {
            return record;
        }
        if (!isCheckingInheritance) {
            return;
        }
        // support for inherited models (eg. relation targeting `mail.model`)
        for (const SubModel of Object.values(this.models)) {
            if (!(SubModel.prototype instanceof Model)) {
                continue;
            }
            const record = SubModel.__records[localId];
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
     * @returns {mail.messaging}
     **/
    async getMessaging() {
        await this.messagingCreatedPromise;
        await this.messagingInitializedPromise;
        return this.messaging;
    }

    /**
     * This method creates a record or updates one of provided Model, based on
     * provided data. This method assumes that records are uniquely identifiable
     * per "unique find" criteria from data on Model.
     *
     * @param {mail.model} Model class
     * @param {Object|Object[]} data
     *  If data is an iterable, multiple records will be created/updated.
     * @returns {mail.model|mail.model[]} created or updated record(s).
     */
    insert(Model, data) {
        const res = this._insert(Model, data);
        this._flushUpdateCycle();
        return res;
    }

    /**
     * Returns the messaging singleton associated to this model manager.
     *
     * @returns {mail.messaging}
     */
    get messaging() {
        if (!this.models || !this._messaging) {
            return undefined;
        }
        // Use "get" specifically to ensure the record still exists and to
        // ensure listeners are properly notified of this access.
        return this.get(this.models['mail.messaging'], this._messaging.localId);
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
        for (const localId of this._localIdsObservedByListener.get(listener) || []) {
            this._listenersObservingLocalId.get(localId).delete(listener);
            if (this._listenersObservingFieldOfLocalId.has(localId)) {
                for (const [, listenersUsingField] of this._listenersObservingFieldOfLocalId.get(localId)) {
                    listenersUsingField.delete(listener);
                }
            }
        }
        this._localIdsObservedByListener.delete(listener);
        for (const [, listeners] of this._listenersObservingAllByModel) {
            listeners.delete(listener);
        }
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
        this._localIdsObservedByListener.set(listener, new Set());
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
     * @param {mail.model} record
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
     * @private
     * @param {mail.model} Model class
     * @param {Object} patch
     */
    _applyModelPatchFields(Model, patch) {
        for (const [fieldName, field] of Object.entries(patch)) {
            Model.fields[fieldName] = field;
        }
    }

    /**
     * @private
     * @param {Object} Models
     * @throws {Error} in case some declared fields are not correct.
     */
    _checkDeclaredFieldsOnModels(Models) {
        for (const Model of Object.values(Models)) {
            for (const fieldName in Model.fields) {
                const field = Model.fields[fieldName];
                // 0. Forbidden name.
                if (fieldName in Model.prototype) {
                    throw new Error(`Field "${Model}/${fieldName}" has a forbidden name.`);
                }
                // 1. Field type is required.
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`Field "${Model}/${fieldName}" has unsupported type ${field.fieldType}.`);
                }
                // 2. Invalid keys based on field type.
                if (field.fieldType === 'attribute') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'dependencies',
                            'fieldType',
                            'readonly',
                            'related',
                            'required',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field "${Model}/${fieldName}" contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                }
                if (field.fieldType === 'relation') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'dependencies',
                            'fieldType',
                            'inverse',
                            'isCausal',
                            'readonly',
                            'related',
                            'relationType',
                            'required',
                            'to',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field "${Model}/${fieldName}" contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                    if (!Models[field.to]) {
                        throw new Error(`Relational field "${Model}/${fieldName}" targets to unknown model name "${field.to}".`);
                    }
                    if (field.isCausal && !(['one2many', 'one2one'].includes(field.relationType))) {
                        throw new Error(`Relational field "${Model}/${fieldName}" has "isCausal" true with a relation of type "${field.relationType}" but "isCausal" is only supported for "one2many" and "one2one".`);
                    }
                    if (field.required && !(['one2one', 'many2one'].includes(field.relationType))) {
                        throw new Error(`Relational field "${Model}/${fieldName}" has "required" true with a relation of type "${field.relationType}" but "required" is only supported for "one2one" and "many2one".`);
                    }
                }
                // 3. Computed field.
                if (field.compute && !(typeof field.compute === 'string')) {
                    throw new Error(`Field "${Model}/${fieldName}" property "compute" must be a string (instance method name).`);
                }
                if (field.compute && !(Model.prototype[field.compute])) {
                    throw new Error(`Field "${Model}/${fieldName}" property "compute" does not refer to an instance method of this Model.`);
                }
                // 4. Related field.
                if (field.compute && field.related) {
                    throw new Error(`Field "${Model}/${fieldName}" cannot be a related and compute field at the same time.`);
                }
                if (field.related) {
                    if (!(typeof field.related === 'string')) {
                        throw new Error(`Field "${Model}/${fieldName}" property "related" has invalid format.`);
                    }
                    const [relationName, relatedFieldName, other] = field.related.split('.');
                    if (!relationName || !relatedFieldName || other) {
                        throw new Error(`Field "${Model}/${fieldName}" property "related" has invalid format.`);
                    }
                    // find relation on self or parents.
                    let relatedRelation;
                    let TargetModel = Model;
                    while (Models[TargetModel.modelName] && !relatedRelation) {
                        if (TargetModel.fields) {
                            relatedRelation = TargetModel.fields[relationName];
                        }
                        TargetModel = TargetModel.__proto__;
                    }
                    if (!relatedRelation) {
                        throw new Error(`Related field "${Model}/${fieldName}" relates to unknown relation name "${relationName}".`);
                    }
                    if (relatedRelation.fieldType !== 'relation') {
                        throw new Error(`Related field "${Model}/${fieldName}" relates to non-relational field "${relationName}".`);
                    }
                    // Assuming related relation is valid...
                    // find field name on related model or any parents.
                    const RelatedModel = Models[relatedRelation.to];
                    let relatedField;
                    TargetModel = RelatedModel;
                    while (Models[TargetModel.modelName] && !relatedField) {
                        if (TargetModel.fields) {
                            relatedField = TargetModel.fields[relatedFieldName];
                        }
                        TargetModel = TargetModel.__proto__;
                    }
                    if (!relatedField) {
                        throw new Error(`Related field "${Model}/${fieldName}" relates to unknown related model field "${relatedFieldName}".`);
                    }
                    if (relatedField.fieldType !== field.fieldType) {
                        throw new Error(`Related field "${Model}/${fieldName}" has mismatch type with its related model field.`);
                    }
                    if (
                        relatedField.fieldType === 'relation' &&
                        relatedField.to !== field.to
                    ) {
                        throw new Error(`Related field "${Model}/${fieldName}" has mismatch target model name with its related model field.`);
                    }
                }
            }
        }
    }

    /**
     * @private
     * @param {Object} Models
     * @throws {Error} in case some fields are not correct.
     */
    _checkProcessedFieldsOnModels(Models) {
        for (const Model of Object.values(Models)) {
            for (const fieldName in Model.fields) {
                const field = Model.fields[fieldName];
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`Field "${Model}/${fieldName}" has unsupported type ${field.fieldType}.`);
                }
                if (field.compute && field.related) {
                    throw new Error(`Field "${Model}/${fieldName}" cannot be a related and compute field at the same time.`);
                }
                if (field.fieldType === 'attribute') {
                    continue;
                }
                if (!field.relationType) {
                    throw new Error(
                        `Field "${Model}/${fieldName}" must define a relation type in "relationType".`
                    );
                }
                if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(field.relationType))) {
                    throw new Error(
                        `Field "${Model}/${fieldName}" has invalid relation type "${field.relationType}".`
                    );
                }
                if (!field.inverse) {
                    throw new Error(
                        `Field "${
                            Model.modelName
                        }/${
                            fieldName
                        }" must define an inverse relation name in "inverse".`
                    );
                }
                if (!field.to) {
                    throw new Error(
                        `Relation "${
                            Model.modelNames
                        }/${
                            fieldName
                        }" must define a model name in "to" (1st positional parameter of relation field helpers).`
                    );
                }
                const RelatedModel = Models[field.to];
                if (!RelatedModel) {
                    throw new Error(
                        `Model name of relation "${Model}/${fieldName}" does not exist.`
                    );
                }
                const inverseField = RelatedModel.fields[field.inverse];
                if (!inverseField) {
                    throw new Error(
                        `Relation "${
                            Model.modelName
                        }/${
                            fieldName
                        }" has no inverse field "${RelatedModel}/${field.inverse}".`
                    );
                }
                if (inverseField.inverse !== fieldName) {
                    throw new Error(
                        `Inverse field name of relation "${
                            Model.modelName
                        }/${
                            fieldName
                        }" does not match with field name of relation "${
                            RelatedModel.modelName
                        }/${
                            inverseField.inverse
                        }".`
                    );
                }
                const allSelfAndParentNames = [];
                let TargetModel = Model;
                while (TargetModel) {
                    allSelfAndParentNames.push(TargetModel.modelName);
                    TargetModel = TargetModel.__proto__;
                }
                if (!allSelfAndParentNames.includes(inverseField.to)) {
                    throw new Error(
                        `Relation "${
                            Model.modelName
                        }/${
                            fieldName
                        }" has inverse relation "${
                            RelatedModel.modelName
                        }/${
                            field.inverse
                        }" misconfigured (currently "${
                            inverseField.to
                        }", should instead refer to this model or parented models: ${
                            allSelfAndParentNames.map(name => `"${name}"`).join(', ')
                        }?)`
                    );
                }
                if (
                    (field.relationType === 'many2many' && inverseField.relationType !== 'many2many') ||
                    (field.relationType === 'one2one' && inverseField.relationType !== 'one2one') ||
                    (field.relationType === 'one2many' && inverseField.relationType !== 'many2one') ||
                    (field.relationType === 'many2one' && inverseField.relationType !== 'one2many')
                ) {
                    throw new Error(
                        `Mismatch relations types "${
                            Model.modelName
                        }/${
                            fieldName
                        }" (${
                            field.relationType
                        }) and "${
                            RelatedModel.modelName
                        }/${
                            field.inverse
                        }" (${
                            inverseField.relationType
                        }).`
                    );
                }
            }
        }
    }

    /**
     * @private
     * @param {mail.model} Model class
     * @param {Object|Object[]} [data={}]
     * @returns {mail.model|mail.model[]}
     */
    _create(Model, data = {}) {
        const isMulti = typeof data[Symbol.iterator] === 'function';
        const dataList = isMulti ? data : [data];
        const records = [];
        for (const data of dataList) {
            /**
             * 1. Ensure the record can be created: localId must be unique.
             */
            const localId = Model._createRecordLocalId(data);
            if (Model.get(localId)) {
                throw Error(`A record already exists for model "${Model}" with localId "${localId}".`);
            }
            /**
             * 2. Prepare record state. Assign various keys and values that are
             * expected to be found on every record.
             */
            const record = new Model({ valid: true });
            if (Model.modelName === 'mail.messaging') {
                if (this._messaging) {
                    throw Error('messaging should be a singleton');
                }
                this._messaging = record;
            }
            Object.assign(record, {
                // The unique record identifier.
                localId,
                // Listeners that are bound to this record, to be notified of
                // change in dependencies of compute, related and "on change".
                __listeners: [],
                // Field values of record.
                __values: {},
            });
            // Ensure X2many relations are Set initially (other fields can stay undefined).
            for (const field of Model.__fieldList) {
                record.__values[field.fieldName] = undefined;
                if (field.fieldType === 'relation') {
                    if (['one2many', 'many2many'].includes(field.relationType)) {
                        record.__values[field.fieldName] = new Set();
                    }
                }
            }
            if (!this._listenersObservingLocalId.has(localId)) {
                this._listenersObservingLocalId.set(localId, new Map());
            }
            this._listenersObservingFieldOfLocalId.set(localId, new Map());
            for (const field of Model.__fieldList) {
                this._listenersObservingFieldOfLocalId.get(localId).set(field, new Map());
            }
            /**
             * 3. Register record and invoke the life-cycle hook `_willCreate.`
             * After this step the record is in a functioning state and it is
             * considered existing.
             */
            Model.__records[record.localId] = record;
            record._willCreate();
            /**
             * 4. Write provided data, default data, and register computes.
             */
            const data2 = {};
            for (const field of Model.__fieldList) {
                // `undefined` should have the same effect as not passing the field
                if (data[field.fieldName] !== undefined) {
                    data2[field.fieldName] = data[field.fieldName];
                } else {
                    data2[field.fieldName] = field.default;
                }
            }
            data2.messaging = link(this._messaging);
            this._update(record, data2, { allowWriteReadonly: true });
            for (const field of Model.__fieldList) {
                if (field.compute) {
                    const listener = new Listener({
                        isPartOfUpdateCycle: true,
                        onChange: (info) => {
                            this.startListening(listener);
                            const res = record[field.compute]();
                            this.stopListening(listener);
                            this._update(record, { [field.fieldName]: res }, { allowWriteReadonly: true });
                        },
                    });
                    record.__listeners.push(listener);
                    listener.onChange();
                }
                if (field.related) {
                    const listener = new Listener({
                        isPartOfUpdateCycle: true,
                        onChange: (info) => {
                            this.startListening(listener);
                            const res = field.computeRelated(record);
                            this.stopListening(listener);
                            this._update(record, { [field.fieldName]: res }, { allowWriteReadonly: true });
                        },
                    });
                    record.__listeners.push(listener);
                    listener.onChange();
                }
            }
            /**
             * 5. Register post processing operation that are to be delayed at
             * the end of the update cycle.
             */
            this._createdRecords.add(record);
            for (const [listener, infoList] of this._listenersObservingAllByModel.get(Model).entries()) {
                this._markListenerToNotify(listener, {
                    error: Error(),
                    reason: `_create: allByModel - ${Model}`,
                    infoList,
                });
            }
            for (const [listener, infoList] of this._listenersObservingLocalId.get(localId).entries()) {
                this._markListenerToNotify(listener, {
                    error: Error(),
                    reason: `_create: localId - ${localId}`,
                    infoList,
                });
            }
            records.push(record);
        }
        return isMulti ? records : records[0];
    }

    /**
     * @private
     * @param {mail.model} record
     */
    _delete(record) {
        const Model = record.constructor;
        if (!record.exists()) {
            throw Error(`Cannot delete already deleted record ${record.localId}.`);
        }
        record._willDelete();
        for (const listener of record.__listeners) {
            this.removeListener(listener);
        }
        for (const field of Model.__fieldList) {
            if (field.fieldType === 'relation') {
                // ensure inverses are properly unlinked
                field.parseAndExecuteCommands(record, unlinkAll(), { allowWriteReadonly: true });
            }
        }
        this._createdRecords.delete(record);
        for (const [listener, infoList] of this._listenersObservingLocalId.get(record.localId).entries()) {
            this._markListenerToNotify(listener, {
                error: Error(),
                reason: `_delete: localId - ${Model}`,
                infoList,
            });
        }
        for (const [listener, infoList] of this._listenersObservingAllByModel.get(Model).entries()) {
            this._markListenerToNotify(listener, {
                error: Error(),
                reason: `_delete: allByModel - ${Model}`,
                infoList,
            });
        }
        delete Model.__records[record.localId];
        if (record === this._messaging) {
            this._messaging = undefined;
        }
    }

    /**
     * Terminates an update cycle by executing its pending operations: execute
     * computed fields, execute life-cycle hooks, update rev numbers.
     *
     * @private
     */
    _flushUpdateCycle(func) {
        if (this._isInUpdateCycle) {
            throw Error('Already in update cycle. You are probably trying to manually create/update/delete a record from inside a compute method, which is not supported.');
        }
        try {
            this._isInUpdateCycle = true;
            this._notifyListenersInUpdateCycle();
            // Verify the existence of value for required fields (of non-deleted records).
            for (const record of this._updatedRecords) {
                if (!record.exists()) {
                    continue;
                }
                for (const required of record.constructor.__requiredFieldsList) {
                    if (record[required.fieldName] === undefined) {
                        throw Error(`Field ${required.fieldName} of ${record.localId} is required.`);
                    }
                }
            }
            this._updatedRecords.clear();
        } finally {
            this._isInUpdateCycle = false;
        }
        // Execution of `_created` and "on change" (after the update cycle itself).
        while (this._createdRecords.size > 0) {
            for (const record of this._createdRecords) {
                // Delete at every step to avoid recursion, indeed _created
                // might trigger an update cycle itself.
                this._createdRecords.delete(record);
                if (!record.exists()) {
                    throw Error(`Cannot call _created for already deleted record ${record.localId}.`);
                }
                record._created();
                for (const onChange of record.constructor.onChanges || []) {
                    const listener = new Listener({
                        onChange: (info) => {
                            this.startListening(listener);
                            for (const dependency of onChange.dependencies) {
                                let target = record;
                                for (const field of dependency.split('.')) {
                                    target = target[field];
                                    if (!target) {
                                        break;
                                    }
                                }
                            }
                            this.stopListening(listener);
                            record[onChange.methodName]();
                        },
                    });
                    listener.onChange();
                    record.__listeners.push(listener);
                }
            }
        }
        this._notifyListenersAfterUpdateCycle();
    }

    /**
     * @private
     * @returns {Object}
     * @throws {Error} in case it cannot generate models.
     */
    _generateModels() {
        const allNames = Object.keys(registry);
        const Models = {};
        const generatedNames = [];
        let toGenerateNames = [...allNames];
        while (toGenerateNames.length > 0) {
            const generatable = toGenerateNames.map(name => registry[name]).find(entry => {
                let isGenerateable = true;
                for (const dependencyName of entry.dependencies) {
                    if (!generatedNames.includes(dependencyName)) {
                        isGenerateable = false;
                    }
                }
                return isGenerateable;
            });
            if (!generatable) {
                throw new Error(`Cannot generate following Model: ${toGenerateNames.join(', ')}`);
            }
            // Make model manager accessible from Model.
            const Model = generatable.factory(Models);
            Model.modelManager = this;
            /**
            * Contains all records. key is local id, while value is the record.
            */
            Model.__records = {};
            for (const patch of generatable.patches) {
                switch (patch.type) {
                    case 'class':
                        patchClassMethods(Model, patch.name, patch.patch);
                        break;
                    case 'instance':
                        patchInstanceMethods(Model, patch.name, patch.patch);
                        break;
                    case 'field':
                        this._applyModelPatchFields(Model, patch.patch);
                        break;
                }
            }
            if (!Object.prototype.hasOwnProperty.call(Model, 'modelName')) {
                throw new Error(`Missing static property "modelName" on Model class "${Model.name}".`);
            }
            if (generatedNames.includes(Model.modelName)) {
                throw new Error(`Duplicate model name "${Model}" shared on 2 distinct Model classes.`);
            }
            Models[Model.modelName] = Model;
            generatedNames.push(Model.modelName);
            toGenerateNames = toGenerateNames.filter(name => name !== Model.modelName);
            this._listenersObservingAllByModel.set(Model, new Map());
        }
        /**
         * Check that declared model fields are correct.
         */
        this._checkDeclaredFieldsOnModels(Models);
        /**
         * Process declared model fields definitions, so that these field
         * definitions are much easier to use in the system. For instance, all
         * relational field definitions have an inverse.
         */
        this._processDeclaredFieldsOnModels(Models);
        /**
         * Check that all model fields are correct, notably one relation
         * should have matching reversed relation.
         */
        this._checkProcessedFieldsOnModels(Models);
        return Models;
    }

    /**
     * @private
     * @param {mail.model}
     * @param {Object|Object[]} data
     * @returns {mail.model|mail.model[]}
     */
    _insert(Model, data) {
        const isMulti = typeof data[Symbol.iterator] === 'function';
        const dataList = isMulti ? data : [data];
        const records = [];
        for (const data of dataList) {
            let record = Model.findFromIdentifyingData(data);
            if (!record) {
                record = this._create(Model, data);
            } else {
                this._update(record, data);
            }
            records.push(record);
        }
        return isMulti ? records : records[0];
    }

    /**
     * @private
     * @param {mail.model} Model class
     * @param {ModelField} field
     * @returns {ModelField}
     */
    _makeInverseRelationField(Model, field) {
        const relFunc =
            field.relationType === 'many2many' ? ModelField.many2many
            : field.relationType === 'many2one' ? ModelField.one2many
            : field.relationType === 'one2many' ? ModelField.many2one
            : field.relationType === 'one2one' ? ModelField.one2one
            : undefined;
        if (!relFunc) {
            throw new Error(`Cannot compute inverse Relation of "${Model}/${field.fieldName}".`);
        }
        const inverseField = new ModelField(Object.assign(
            {},
            relFunc(Model.modelName, { inverse: field.fieldName }),
            {
                fieldName: `_inverse_${Model}/${field.fieldName}`,
            }
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
     * Notifies the listeners that have been flagged to be notified and for
     * which the `onChange` function was defined to be called after the update
     * cycle.
     *
     * In particular this is the case of components using models that need to
     * re-render and for records with "on change".
     */
    _notifyListenersAfterUpdateCycle() {
        for (const [listener, infoList] of this._listenersToNotifyAfterUpdateCycle.entries()) {
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
     */
    _notifyListenersInUpdateCycle() {
        while (this._listenersToNotifyInUpdateCycle.size > 0) {
            for (const [listener, infoList] of this._listenersToNotifyInUpdateCycle.entries()) {
                this._listenersToNotifyInUpdateCycle.delete(listener);
                listener.onChange(infoList);
            }
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
     * @param {Object} Models
     */
    _processDeclaredFieldsOnModels(Models) {
        /**
         * 1. Prepare fields.
         */
        for (const Model of Object.values(Models)) {
            if (!Object.prototype.hasOwnProperty.call(Model, 'fields')) {
                Model.fields = {};
            }
            Model.inverseRelations = [];
            // Make fields aware of their field name.
            for (const [fieldName, fieldData] of Object.entries(Model.fields)) {
                Model.fields[fieldName] = new ModelField(Object.assign({}, fieldData, {
                    fieldName,
                }));
            }
        }
        /**
         * 2. Auto-generate definitions of undeclared inverse relations.
         */
        for (const Model of Object.values(Models)) {
            for (const field of Object.values(Model.fields)) {
                if (field.fieldType !== 'relation') {
                    continue;
                }
                if (field.inverse) {
                    continue;
                }
                const RelatedModel = Models[field.to];
                const inverseField = this._makeInverseRelationField(Model, field);
                field.inverse = inverseField.fieldName;
                RelatedModel.fields[inverseField.fieldName] = inverseField;
            }
        }
        /**
         * 3. Extend definition of fields of a model with the definition of
         * fields of its parents.
         */
        for (const Model of Object.values(Models)) {
            Model.__combinedFields = {};
            for (const field of Object.values(Model.fields)) {
                Model.__combinedFields[field.fieldName] = field;
            }
            let TargetModel = Model.__proto__;
            while (TargetModel && TargetModel.fields) {
                for (const targetField of Object.values(TargetModel.fields)) {
                    const field = Model.__combinedFields[targetField.fieldName];
                    if (!field) {
                        Model.__combinedFields[targetField.fieldName] = targetField;
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
        for (const Model of Object.values(Models)) {
            // Object with fieldName/field as key/value pair, for quick access.
            Model.__fieldMap = Model.__combinedFields;
            // List of all fields, for iterating.
            Model.__fieldList = Object.values(Model.__fieldMap);
            Model.__requiredFieldsList = Model.__fieldList.filter(
                field => field.required
            );
            // Add field accessors.
            for (const field of Model.__fieldList) {
                Object.defineProperty(Model.prototype, field.fieldName, {
                    get() { // this is bound to record
                        for (const listener of this.modelManager._listeners) {
                            this.modelManager._localIdsObservedByListener.get(listener).add(this.localId);
                            if (!this.modelManager._listenersObservingLocalId.has(this.localId)) {
                                this.modelManager._listenersObservingLocalId.set(this.localId, new Map());
                            }
                            const entryLocalId = this.modelManager._listenersObservingLocalId.get(this.localId);
                            const info = {
                                error: Error(),
                                reason: `getField - ${this.localId} / ${field.fieldName}`,
                            };
                            if (entryLocalId.has(listener)) {
                                entryLocalId.get(listener).push(info);
                            } else {
                                entryLocalId.set(listener, [info]);
                            }
                            const entryField = this.modelManager._listenersObservingFieldOfLocalId.get(this.localId).get(field);
                            if (entryField.has(listener)) {
                                entryField.get(listener).push(info);
                            } else {
                                entryField.set(listener, [info]);
                            }
                        }
                        return field.get(this);
                    },
                });
            }
            delete Model.__combinedFields;
        }
    }

    /**
     * @private
     * @param {mail.model} record
     * @param {Object} data
     * @param {Object} [options]
     * @param [options.allowWriteReadonly=false]
     * @returns {boolean} whether any value changed for the current record
     */
    _update(record, data, options = {}) {
        if (!record.exists()) {
            throw Error(`Cannot update already deleted record ${record.localId}.`);
        }
        const { allowWriteReadonly = false } = options;
        const Model = record.constructor;
        let hasChanged = false;
        for (const fieldName of Object.keys(data)) {
            if (data[fieldName] === undefined) {
                // `undefined` should have the same effect as not passing the field
                continue;
            }
            const field = Model.__fieldMap[fieldName];
            if (!field) {
                throw new Error(`Cannot create/update record with data unrelated to a field. (record: "${record.localId}", non-field attempted update: "${fieldName}")`);
            }
            const newVal = data[fieldName];
            if (field.readonly && !allowWriteReadonly && record[fieldName] !== newVal) {
                throw new Error(`Can't update "${field.fieldName}" (record: "${record.localId}") because it's readonly.`);
            }
            if (!field.parseAndExecuteCommands(record, newVal, options)) {
                continue;
            }
            hasChanged = true;
            for (const [listener, infoList] of this._listenersObservingFieldOfLocalId.get(record.localId).get(field).entries()) {
                this._markListenerToNotify(listener, {
                    error: Error(),
                    reason: `_update: field - ${record.localId} / ${field.fieldName}`,
                    infoList,
                });
            }
        }
        if (hasChanged) {
            this._updatedRecords.add(record);
        }
        return hasChanged;
    }

}
