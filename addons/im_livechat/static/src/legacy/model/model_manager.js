/** @odoo-module **/

import { useRefToModel } from "@im_livechat/legacy/component_hooks/use_ref_to_model";
import { IS_RECORD, patchesAppliedPromise, registry } from "@im_livechat/legacy/model/model_core";
import { ModelField } from "@im_livechat/legacy/model/model_field";
import { ModelIndexAnd } from "@im_livechat/legacy/model/model_index_and";
import { ModelIndexXor } from "@im_livechat/legacy/model/model_index_xor";
import { FieldCommand, unlinkAll } from "@im_livechat/legacy/model/model_field_command";
import { RelationSet } from "@im_livechat/legacy/model/model_field_relation_set";
import { Listener } from "@im_livechat/legacy/model/model_listener";
import { followRelations } from "@im_livechat/legacy/model/model_utils";
import { makeDeferred } from "@im_livechat/legacy/utils/deferred";
import {
    componentRegistry,
    registerMessagingComponent,
    unregisterMessagingComponent,
} from "@im_livechat/legacy/utils/messaging_component";

import { LegacyComponent } from "@web/legacy/legacy_component";

import { Component } from "@odoo/owl";

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
        await patchesAppliedPromise;
        this._generateModels();
        /**
         * Create the messaging singleton record.
         */
        this.models["Messaging"].insert(values);
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
        this._flushUpdateCycle();
    }

    /**
     * Destroys this model manager, which consists of cleaning all possible
     * references in order to avoid memory leaks.
     */
    destroy() {
        this.messaging.delete();
        for (const model of Object.values(this.models)) {
            if (model.__messagingComponent) {
                delete model.__fieldAndRefNames;
                unregisterMessagingComponent(model.name);
                delete model.__messagingComponent;
            }
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
        this._preInsertIdentifyingFieldsFromData(model, data);
        const record = model.__recordsIndex.findRecord(data);
        if (!record) {
            return;
        }
        for (const listener of this._listeners) {
            listener.lastObservedRecords.add(record);
            const entry = record.__listenersObservingRecord;
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
        const isMulti = typeof data[Symbol.iterator] === "function";
        const records = this._insert(model, isMulti ? data : [data]);
        this._flushUpdateCycle();
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
            const isMulti = typeof recordsData[Symbol.iterator] === "function";
            this._insert(this.models[modelName], isMulti ? recordsData : [recordsData]);
        }
        this._flushUpdateCycle();
    }

    /**
     * Returns the messaging singleton associated to this model manager.
     *
     * @returns {Messaging|undefined}
     */
    get messaging() {
        if (!this.models["Messaging"]) {
            return undefined;
        }
        // Use "findFromIdentifyingData" specifically to ensure the record still
        // exists and to ensure listeners are properly notified of this access.
        return this.models["Messaging"].findFromIdentifyingData({});
    }

    /**
     * Removes a listener, with the same object reference as given to `startListening`.
     * Removing the listener effectively makes its `onChange` function no longer
     * called.
     *
     * @param {Listener} listener
     */
    removeListener(listener) {
        if (!listener) {
            return;
        }
        this._listeners.delete(listener);
        this._listenersToNotifyInUpdateCycle.delete(listener);
        this._listenersToNotifyAfterUpdateCycle.delete(listener);
        for (const record of listener.lastObservedRecords) {
            if (!record.exists()) {
                continue;
            }
            record.__listenersObservingRecord.delete(listener);
            const listenersObservingFieldOfRecord = record.__listenersObservingFieldsOfRecord;
            for (const field of listener.lastObservedFieldsByRecord.get(record) || []) {
                listenersObservingFieldOfRecord.get(field).delete(listener);
            }
        }
        for (const model of listener.lastObservedAllByModel) {
            this._listenersObservingAllByModel.get(model).delete(listener);
        }
        listener.lastObservedRecords.clear();
        listener.lastObservedFieldsByRecord.clear();
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
        if (definition.get("template")) {
            const ComponentClass = definition.get("isLegacyComponent")
                ? LegacyComponent
                : Component;
            const ModelComponent = { [model.name]: class extends ComponentClass {} }[model.name];
            Object.assign(ModelComponent, {
                props: { record: Object },
                template: definition.get("template"),
            });
            if (!(model.name in componentRegistry)) {
                registerMessagingComponent(ModelComponent);
            }
            model.__messagingComponent = ModelComponent;
            model.__fieldAndRefNames = [];
        }
        Object.assign(model, Object.fromEntries(definition.get("modelMethods")));
        Object.assign(model.prototype, Object.fromEntries(definition.get("recordMethods")));
        for (const [getterName, getter] of definition.get("modelGetters")) {
            Object.defineProperty(model, getterName, { get: getter });
        }
        for (const [getterName, getter] of definition.get("recordGetters")) {
            Object.defineProperty(model.prototype, getterName, { get: getter });
        }
        // Make model manager accessible from model.
        model.modelManager = this;
        model.fields = {};
        model.identifyingMode = definition.get("identifyingMode");
        model.__records = new Set();
        model.__recordCount = 0;
        model.__recordsIndex = (() => {
            switch (model.identifyingMode) {
                case "and":
                    return new ModelIndexAnd(model);
                case "xor":
                    return new ModelIndexXor(model);
            }
        })();
        this._listenersObservingAllByModel.set(model, new Map());
        this.models[model.name] = model;
    }

    /**
     * @private
     * @throws {Error} in case some declared fields are not correct.
     */
    _checkDeclaredFieldsOnModels() {
        for (const model of Object.values(this.models)) {
            for (const [fieldName, field] of registry.get(model.name).get("fields")) {
                // 0. Forbidden name.
                if (fieldName in model.prototype) {
                    throw new Error(`Field ${model}/${fieldName} has a forbidden name.`);
                }
                // 1. Field type is required.
                if (!["attribute", "relation"].includes(field.fieldType)) {
                    throw new Error(
                        `Field ${model}/${fieldName} has unsupported type "${field.fieldType}".`
                    );
                }
                // 2. Invalid keys based on field type.
                if (field.fieldType === "attribute") {
                    const invalidKeys = Object.keys(field).filter(
                        (key) =>
                            ![
                                "compute",
                                "default",
                                "fieldType",
                                "identifying",
                                "readonly",
                                "ref",
                                "related",
                                "required",
                                "sum",
                            ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(
                            `Field ${model}/${fieldName} contains some invalid keys: "${invalidKeys.join(
                                ", "
                            )}".`
                        );
                    }
                }
                if (field.fieldType === "relation") {
                    const invalidKeys = Object.keys(field).filter(
                        (key) =>
                            ![
                                "compute",
                                "default",
                                "fieldType",
                                "identifying",
                                "inverse",
                                "isCausal",
                                "readonly",
                                "related",
                                "relationType",
                                "required",
                                "sort",
                                "to",
                            ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(
                            `Field ${model}/${fieldName} contains some invalid keys: "${invalidKeys.join(
                                ", "
                            )}".`
                        );
                    }
                    if (!this.models[field.to]) {
                        throw new Error(
                            `Relational field ${model}/${fieldName} targets to unknown model name "${field.to}".`
                        );
                    }
                    if (field.required && field.relationType !== "one") {
                        throw new Error(
                            `Relational field ${model}/${fieldName} has "required" true with a relation of type "${field.relationType}" but "required" is only supported for "one".`
                        );
                    }
                    if (field.sort && field.relationType !== "many") {
                        throw new Error(
                            `Relational field "${model}/${fieldName}" has "sort" with a relation of type "${field.relationType}" but "sort" is only supported for "many".`
                        );
                    }
                }
                // 3. Check for redundant or unsupported attributes on identifying fields.
                if (field.identifying) {
                    if ("readonly" in field) {
                        throw new Error(
                            `Identifying field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for identifying fields).`
                        );
                    }
                    if ("required" in field && model.identifyingMode === "and") {
                        throw new Error(
                            `Identifying field ${model}/${fieldName} has unnecessary "required" attribute (required is implicit for AND identifying fields).`
                        );
                    }
                    if ("default" in field) {
                        throw new Error(
                            `Identifying field ${model}/${fieldName} has "default" attribute, but default values are not supported for identifying fields.`
                        );
                    }
                }
                // 4. Computed field.
                if (field.compute) {
                    if (typeof field.compute !== "function") {
                        throw new Error(
                            `Property "compute" of field ${model}/${fieldName} must be a string (instance method name) or a function (the actual compute).`
                        );
                    }
                    if ("readonly" in field) {
                        throw new Error(
                            `Computed field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for computed fields).`
                        );
                    }
                }
                // 5. Related field.
                if (field.related) {
                    if (field.compute) {
                        throw new Error(
                            `field ${model}/${fieldName} cannot be a related and compute field at the same time.`
                        );
                    }
                    if (!(typeof field.related === "string")) {
                        throw new Error(
                            `Property "related" of field ${model}/${fieldName} has invalid format.`
                        );
                    }
                    const [relationName, relatedFieldName, other] = field.related.split(".");
                    if (!relationName || !relatedFieldName || other) {
                        throw new Error(
                            `Property "related" of field ${model}/${fieldName} has invalid format.`
                        );
                    }
                    // find relation on self or parents.
                    let relatedRelation;
                    let targetModel = model;
                    while (this.models[targetModel.name] && !relatedRelation) {
                        relatedRelation = registry
                            .get(targetModel.name)
                            .get("fields")
                            .get(relationName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedRelation) {
                        throw new Error(
                            `Related field ${model}/${fieldName} relates to unknown relation name "${relationName}".`
                        );
                    }
                    if (relatedRelation.fieldType !== "relation") {
                        throw new Error(
                            `Related field ${model}/${fieldName} relates to non-relational field "${relationName}".`
                        );
                    }
                    // Assuming related relation is valid...
                    // find field name on related model or any parents.
                    const relatedModel = this.models[relatedRelation.to];
                    let relatedField;
                    targetModel = relatedModel;
                    while (this.models[targetModel.name] && !relatedField) {
                        relatedField = registry
                            .get(targetModel.name)
                            .get("fields")
                            .get(relatedFieldName);
                        targetModel = targetModel.__proto__;
                    }
                    if (!relatedField) {
                        throw new Error(
                            `Related field ${model}/${fieldName} relates to unknown related model field "${relatedFieldName}".`
                        );
                    }
                    if (relatedField.fieldType !== field.fieldType) {
                        throw new Error(
                            `Related field ${model}/${fieldName} has mismatched type with its related model field.`
                        );
                    }
                    if (relatedField.fieldType === "relation" && relatedField.to !== field.to) {
                        throw new Error(
                            `Related field ${model}/${fieldName} has mismatched target model name with its related model field.`
                        );
                    }
                    if ("readonly" in field) {
                        throw new Error(
                            `Related field ${model}/${fieldName} has unnecessary "readonly" attribute (readonly is implicit for related fields).`
                        );
                    }
                }
                if (field.ref) {
                    if (!model.__messagingComponent) {
                        throw new Error(
                            `Field ${model}/${fieldName} has a 'ref' attribute but its model is not linked to any component.`
                        );
                    }
                }
            }
        }
    }

    /**
     * @private
     * @throws {Error}
     */
    _checkOnChangesOnModels() {
        for (const model of Object.values(this.models)) {
            for (const { dependencies, methodName } of registry.get(model.name).get("onChanges")) {
                for (const dependency of dependencies) {
                    let currentModel = model;
                    let currentField;
                    for (const fieldName of dependency) {
                        if (!currentModel) {
                            throw new Error(
                                `OnChange '${methodName}' defines a dependency with path '${dependency.join(
                                    "."
                                )}', but this dependency does not resolve: ${currentField} is not a relational field, therefore there is no relation to follow.`
                            );
                        }
                        currentField = currentModel.__fieldMap.get(fieldName);
                        if (!currentField) {
                            throw new Error(
                                `OnChange '${methodName}' defines a dependency with path '${dependency.join(
                                    "."
                                )}', but this path does not resolve: ${currentModel}/${fieldName} does not exist.`
                            );
                        }
                        if (currentField.to) {
                            currentModel = this.models[currentField.to];
                        } else {
                            currentModel = undefined;
                        }
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
            if (!["and", "xor"].includes(model.identifyingMode)) {
                throw new Error(
                    `Unsupported identifying mode "${model.identifyingMode}" on ${model}. Must be one of 'and' or 'xor'.`
                );
            }
            for (const field of model.__fieldList) {
                const fieldName = field.fieldName;
                if (!["attribute", "relation"].includes(field.fieldType)) {
                    throw new Error(`${field} has unsupported type "${field.fieldType}".`);
                }
                if (field.compute && field.related) {
                    throw new Error(
                        `${field} cannot be a related and compute field at the same time.`
                    );
                }
                if (field.fieldType === "attribute") {
                    continue;
                }
                if (!field.relationType) {
                    throw new Error(`${field} must define a relation type in "relationType".`);
                }
                if (!["many", "one"].includes(field.relationType)) {
                    throw new Error(`${field} has invalid relation type "${field.relationType}".`);
                }
                if (!field.inverse) {
                    throw new Error(`${field} must define an inverse relation name in "inverse".`);
                }
                if (!field.to) {
                    throw new Error(
                        `${field} must define a model name in "to" (1st positional parameter of relation field helpers).`
                    );
                }
                const relatedModel = this.models[field.to];
                if (!relatedModel) {
                    throw new Error(
                        `${field} defines a relation to model ${field.to}, but there is no model registered with this name.`
                    );
                }
                const inverseField = relatedModel.__fieldMap.get(field.inverse);
                if (!inverseField) {
                    throw new Error(
                        `${field} defines its inverse as field ${relatedModel}/${field.inverse}, but it does not exist.`
                    );
                }
                if (inverseField.inverse !== fieldName) {
                    throw new Error(
                        `The name of ${field} does not match with the name defined in its inverse ${inverseField}.`
                    );
                }
                if (![model.name, "Record"].includes(inverseField.to)) {
                    throw new Error(
                        `${field} has its inverse ${inverseField} referring to an invalid model (${inverseField.to}).`
                    );
                }
                if (field.sort) {
                    for (const path of field.sortedFieldSplittedPaths) {
                        let currentField = field;
                        for (const fieldName of path) {
                            if (!currentField.to) {
                                throw new Error(
                                    `Field ${field} defines a sort with path '${path.join(
                                        "."
                                    )}', but this path does not resolve: ${currentField} is not a relational field, therefore there is no relation to follow.`
                                );
                            }
                            if (!this.models[currentField.to].__fieldMap.has(fieldName)) {
                                throw new Error(
                                    `Field ${field} defines a sort with path '${path.join(
                                        "."
                                    )}', but this path does not resolve: ${
                                        this.models[currentField.to]
                                    }/${fieldName} does not exist.`
                                );
                            }
                            currentField = this.models[currentField.to].__fieldMap.get(fieldName);
                        }
                    }
                }
            }
            for (const identifyingField of model.__identifyingFieldNames) {
                const field = model.__fieldMap.get(identifyingField);
                if (!field) {
                    throw new Error(
                        `Identifying field "${model}/${identifyingField}" is not a field on ${model}.`
                    );
                }
                if (field.to) {
                    if (field.relationType !== "one") {
                        throw new Error(
                            `Identifying field "${model}/${identifyingField}" has a relation of type "${field.relationType}" but identifying field is only supported for "one".`
                        );
                    }
                    const relatedModel = this.models[field.to];
                    const inverseField = relatedModel.__fieldMap.get(field.inverse);
                    if (!inverseField.isCausal) {
                        throw new Error(
                            `Identifying field "${model}/${identifyingField}" has an inverse "${inverseField}" not declared as "isCausal".`
                        );
                    }
                }
            }
        }
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
            // Listeners that are bound to this record, to be notified of
            // change in dependencies of compute, related and "on change".
            __listeners: [],
            /**
             * Map between listeners that are observing this record and array of
             * information about how the record is observed.
             */
            __listenersObservingRecord: new Map(),
            /**
             * Map between fields and a Map between listeners that are observing
             * the field and array of information about how the field is observed.
             */
            __listenersObservingFieldsOfRecord: new Map(),
            // Field values of record.
            __values: new Map(),
            [IS_RECORD]: true,
        });
        const record = owl.markRaw(
            !this.isDebug
                ? nonProxyRecord
                : new Proxy(nonProxyRecord, {
                      get: function getFromProxy(record, prop) {
                          if (
                              model.__fieldMap &&
                              !model.__fieldMap.has(prop) &&
                              !["_super", "then", "localId"].includes(prop) &&
                              typeof prop !== "symbol" &&
                              !(prop in record)
                          ) {
                              console.warn(`non-field read "${prop}" on ${record}`);
                          }
                          return record[prop];
                      },
                  })
        );
        if (this.isDebug) {
            record.__proxifiedRecord = record;
        }
        // Ensure X2many relations are Set initially (other fields can stay undefined).
        for (const field of model.__fieldList) {
            if (field.fieldType === "relation") {
                if (field.relationType === "many") {
                    record.__values.set(field.fieldName, new RelationSet(record, field));
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
        const recordMethods = registry.get(model.name).get("recordMethods");
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
        const lifecycleHooks = registry.get(model.name).get("lifecycleHooks");
        if (lifecycleHooks.has("_willDelete")) {
            lifecycleHooks.get("_willDelete").call(record);
        }
        for (const listener of record.__listeners) {
            this.removeListener(listener);
        }
        for (const field of model.__fieldList) {
            if (field.fieldType === "relation") {
                // ensure inverses are properly unlinked
                field.parseAndExecuteCommands(record, unlinkAll(), { allowWriteReadonly: true });
                if (!record.exists()) {
                    return; // current record might have been deleted from causality
                }
            }
        }
        model.__recordsIndex.removeRecord(record);
        this._createdRecordsComputes.delete(record);
        this._createdRecordsCreated.delete(record);
        this._createdRecordsOnChange.delete(record);
        this._updatedRecordsCheckRequired.delete(record);
        for (const [listener, infoList] of record.__listenersObservingRecord) {
            this._markListenerToNotify(listener, {
                listener,
                reason: this.isDebug && `_delete: record - ${record}`,
                infoList,
            });
        }
        for (const [listener, infoList] of this._listenersObservingAllByModel.get(model)) {
            this._markListenerToNotify(listener, {
                listener,
                reason: this.isDebug && `_delete: allByModel - ${record}`,
                infoList,
            });
        }
        delete record.__values;
        delete record.__listeners;
        delete record.__listenersObservingRecord;
        delete record.__listenersObservingFieldsOfRecord;
        model.__records.delete(record);
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
                throw Error(
                    `Model manager locked by ${listener}. It is not allowed to insert/update/delete from inside a lock.`
                );
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
                            const res = field.compute.call(record);
                            this.stopListening(listener);
                            this._update(
                                record,
                                { [field.fieldName]: res },
                                { allowWriteReadonly: true }
                            );
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
                            this._update(
                                record,
                                { [field.fieldName]: res },
                                { allowWriteReadonly: true }
                            );
                        },
                    });
                    listeners.push(listener);
                }
            }
            record.__listeners.push(...listeners);
            for (const listener of listeners) {
                listener.onChange({
                    listener,
                    reason: this.isDebug && `first call on ${record}`,
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
            const lifecycleHooks = registry.get(record.constructor.name).get("lifecycleHooks");
            if (lifecycleHooks.has("_created")) {
                lifecycleHooks.get("_created").call(record);
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
            for (const onChange of registry.get(record.constructor.name).get("onChanges")) {
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
        const model = { Record: class {} }["Record"];
        this._applyModelDefinition(model);
        // Record is generated separately and before the other models since
        // it is the dependency of all of them.
        const allModelNamesButRecord = [...registry.keys()].filter((name) => name !== "Record");
        for (const modelName of allModelNamesButRecord) {
            const model = { [modelName]: class extends this.models["Record"] {} }[modelName];
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
        this._checkOnChangesOnModels();
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
                this._preInsertIdentifyingFieldsFromData(model, data2);
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
     * @private
     * @param {Object} model
     * @param {ModelField} field
     * @returns {ModelField}
     */
    _makeInverseRelationField(model, field) {
        const inverseField = new ModelField(
            Object.assign({}, ModelField.many(model.name, { inverse: field.fieldName }), {
                fieldName: `_inverse_${model}/${field.fieldName}`,
                // Allows the inverse of an identifying field to be
                // automatically generated.
                isCausal: field.identifying,
                model: this.models[field.to],
            })
        );
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
        for (const [listener, infoList] of record.__listenersObservingFieldsOfRecord.get(field) ||
            []) {
            this._markListenerToNotify(listener, {
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
     * Processes all commands given in data that concerns relation fields that
     * are identifying to execute their respective "insert-and-replace" commands
     * and to replace them by corresponding "replace" commands.
     *
     * @param {Object} model
     * @param {Object} data
     */
    _preInsertIdentifyingFieldsFromData(model, data) {
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
                throw new Error(
                    `Identifying field "${model}/${fieldName}" should receive a single command.`
                );
            }
            const [command] = commands;
            if (!(command instanceof FieldCommand)) {
                throw new Error(
                    `Identifying field "${model}/${fieldName}" should receive a command.`
                );
            }
            if (!["insert-and-replace", "replace"].includes(command._name)) {
                throw new Error(
                    `Identifying field "${model}/${fieldName}" should receive a "replace" or "insert-and-replace" command.`
                );
            }
            if (command._name === "replace") {
                continue;
            }
            if (!command._value) {
                throw new Error(
                    `Identifying field "${model}/${fieldName}" is lacking a relation value.`
                );
            }
            if (typeof command._value[Symbol.iterator] === "function") {
                throw new Error(
                    `Identifying field "${model}/${fieldName}" should receive a single data object.`
                );
            }
            const [record] = this._insert(this.models[field.to], [command._value]);
            data[fieldName] = record;
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
            for (const [fieldName, fieldData] of registry.get(model.name).get("fields")) {
                model.fields[fieldName] = new ModelField(
                    Object.assign({}, fieldData, {
                        fieldName,
                        model,
                    })
                );
                if (fieldData.sum) {
                    const [relationFieldName, contributionFieldName] = fieldData.sum.split(".");
                    if (!sumContributionsByFieldName.has(relationFieldName)) {
                        sumContributionsByFieldName.set(relationFieldName, []);
                    }
                    sumContributionsByFieldName.get(relationFieldName).push({
                        from: contributionFieldName,
                        to: fieldName,
                    });
                }
                if (fieldData.ref) {
                    model.__fieldAndRefNames.push([fieldName, fieldData.ref]);
                }
            }
            for (const [fieldName, sumContributions] of sumContributionsByFieldName) {
                model.fields[fieldName].sumContributions = sumContributions;
            }
            if (model.__messagingComponent) {
                const setupFunctions = [];
                if (registry.get(model.name).has("componentSetup")) {
                    setupFunctions.push(registry.get(model.name).get("componentSetup"));
                }
                if (model.__fieldAndRefNames.length > 0) {
                    setupFunctions.push(function () {
                        for (const [fieldName, refName] of model.__fieldAndRefNames) {
                            useRefToModel({ fieldName, refName });
                        }
                    });
                }
                if (setupFunctions.length > 0) {
                    Object.assign(model.__messagingComponent.prototype, {
                        setup() {
                            for (const fun of setupFunctions) {
                                fun.call(this);
                            }
                        },
                    });
                }
            }
        }
        /**
         * 2. Auto-generate definitions of undeclared inverse relations.
         */
        for (const model of Object.values(this.models)) {
            for (const field of Object.values(model.fields)) {
                if (field.fieldType !== "relation") {
                    continue;
                }
                if (field.inverse) {
                    // Automatically make causal the inverse of an identifying.
                    if (field.identifying) {
                        this.models[field.to].fields[field.inverse].isCausal = true;
                    }
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
            model.__fieldMap = new Map(Object.entries(model.__combinedFields));
            // List of all fields, for iterating.
            model.__fieldList = [...model.__fieldMap.values()];
            model.__requiredFieldsList = model.__fieldList.filter((field) => field.required);
            model.__identifyingFieldNames = new Set();
            for (const [fieldName, field] of model.__fieldMap) {
                if (field.identifying) {
                    model.__identifyingFieldNames.add(fieldName);
                }
                // Add field accessors on model.
                Object.defineProperty(model.prototype, fieldName, {
                    get: function getFieldValue() {
                        // this is bound to record
                        const record = this.modelManager.isDebug ? this.__proxifiedRecord : this;
                        if (this.modelManager._listeners.size) {
                            const entryRecord = record.__listenersObservingRecord;
                            const reason =
                                record.modelManager.isDebug && `getField - ${field} of ${record}`;
                            let entryField = record.__listenersObservingFieldsOfRecord.get(field);
                            if (!entryField) {
                                entryField = new Map();
                                record.__listenersObservingFieldsOfRecord.set(field, entryField);
                            }
                            for (const listener of record.modelManager._listeners) {
                                listener.lastObservedRecords.add(record);
                                const info = { listener, reason };
                                if (entryRecord.has(listener)) {
                                    entryRecord.get(listener).push(info);
                                } else {
                                    entryRecord.set(listener, [info]);
                                }
                                if (!listener.lastObservedFieldsByRecord.has(record)) {
                                    listener.lastObservedFieldsByRecord.set(record, new Set());
                                }
                                listener.lastObservedFieldsByRecord.get(record).add(field);
                                if (entryField.has(listener)) {
                                    entryField.get(listener).push(info);
                                } else {
                                    entryField.set(listener, [info]);
                                }
                            }
                        }
                        return field.get(record);
                    },
                });
                if (model.__messagingComponent) {
                    // Add field accessors on related component
                    Object.defineProperty(model.__messagingComponent.prototype, fieldName, {
                        get: function getFieldValue() {
                            // this is bound to record
                            return this.props.record[fieldName];
                        },
                    });
                }
            }
            if (model.__messagingComponent) {
                // Add record method accessors + localId
                Object.defineProperty(model.__messagingComponent.prototype, "localId", {
                    get: function getFieldValue() {
                        // this is bound to record
                        return this.props.record.localId;
                    },
                });
                const definition = registry.get(model.name);
                for (const name of definition.get("recordMethods").keys()) {
                    Object.defineProperty(model.__messagingComponent.prototype, name, {
                        get() {
                            return this.props.record[name];
                        },
                    });
                }
                for (const name of definition.get("recordGetters").keys()) {
                    Object.defineProperty(model.__messagingComponent.prototype, name, {
                        get() {
                            return this.props.record[name];
                        },
                    });
                }
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
                // console.warn(
                //     `Cannot create/update record with data unrelated to a field. (record: "${record}", non-field attempted update: "${fieldName}")`
                // );
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
            this._markRecordFieldAsChanged(record, field);
        }
        if (hasChanged) {
            this._updatedRecordsCheckRequired.add(record);
        }
        return hasChanged;
    }
}
