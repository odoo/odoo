/** @odoo-module **/

import { checkRegisteredProperties } from '@mail/model/fields/properties/check_registered_properties';
import { checkRegisteredTypes } from '@mail/model/fields/types/check_registered_types';
import { checkDeclaredModels } from '@mail/model/model_check_declared_models';
import { checkProcessedFieldsOnModels } from '@mail/model/model_check_processed_fields';
import { registry } from '@mail/model/model_core';
import ModelField from '@mail/model/model_field';
import { patchClassMethods, patchInstanceMethods } from '@mail/utils/utils';
import { unlinkAll } from '@mail/model/model_field_command';

/**
 * Inner separator used between bits of information in string that is used to
 * identify a dependent of a field. Useful to determine which record and field
 * to register for compute during this update cycle.
 */
const DEPENDENT_INNER_SEPARATOR = "--//--//--";

/**
 * Object that manage models and records, notably their update cycle: whenever
 * some records are requested for update (either with model static method
 * `create()` or record method `update()`), this object processes them with
 * direct field & and computed field updates.
 */
class ModelManager {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /*
     * @param {Object} param0
     * @param {Object} param0.env
     * @param {Map} param0.fieldPropertyRegistry
     * @param {Map} param0.fieldTypeRegistry
     */
    constructor({ env, fieldPropertyRegistry, fieldTypeRegistry }) {
        /**
         * Inner separator used inside string to represent dependents.
         * Set as public attribute so that it can be used by model field.
         */
        this.DEPENDENT_INNER_SEPARATOR = DEPENDENT_INNER_SEPARATOR;
        /**
         * The messaging env.
         */
        this.env = env;
        this.fieldPropertyRegistry = fieldPropertyRegistry;
        this.fieldTypeRegistry = fieldTypeRegistry;

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
         * Tracks whether something has changed during the current update cycle.
         * Useful to notify components (through the store) that some records
         * have been changed.
         */
        this._hasAnyChangeDuringCycle = false;
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
         * Set of records that have been updated during the current update
         * cycle. Useful to allow observers (typically components) to detect
         * whether specific records have been changed.
         */
        this._updatedRecords = new Set();
        /**
         * Fields flagged to call compute during an update cycle.
         * For instance, when a field with dependents got update, dependent
         * fields should update themselves by invoking compute at end of
         * update cycle. Key is of format
         * <record-local-id><DEPENDENT_INNER_SEPARATOR><fieldName>, and
         * determine record and field to be computed. Keys are strings because
         * it must contain only one occurrence of pair record/field, and we want
         * O(1) reads/writes.
         */
        this._toComputeFields = new Map();
        /**
         * "on change" methods flagged to call during an update cycle. Similar
         * to computes but called after all other computes are done, and does
         * not actually assign any value to its respective field.
         * This is deprecated but when it is necessary due to other limitations
         * in code it is better using "on change" than polluting real computes.
         */
        this._toCallOnChange = new Map();
    }

    /**
     * Called when all JS modules that register or patch models have been
     * done. This launches generation of models.
     */
    start() {
        checkRegisteredProperties({ fieldPropertyRegistry: this.fieldPropertyRegistry });
        checkRegisteredTypes({ env: this.env, fieldTypeRegistry: this.fieldTypeRegistry });
        /**
         * Generate the models.
         */
        Object.assign(this.env.models, this._generateModels());
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
     * Delete all records.
     */
    deleteAll() {
        for (const Model of Object.values(this.env.models)) {
            for (const record of Object.values(Model.__records)) {
                this._delete(record);
            }
        }
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
        const record = Model.__records[localId];
        if (record) {
            return record;
        }
        if (!isCheckingInheritance) {
            return;
        }
        // support for inherited models (eg. relation targeting `mail.model`)
        for (const SubModel of Object.values(this.env.models)) {
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
     * @param {string} patchName
     * @param {Object} patch
     */
    _applyModelPatchFields(Model, patchName, patch) {
        for (const [fieldName, field] of Object.entries(patch)) {
            if (Model.fields[fieldName]) {
                throw new Error(`Invalid field patch "${patchName}" on "${Model.modelName}/${fieldName}" because the field already exists. Don't patch an existing field.`);
            }
            const deeplyCopiedField = Object.assign({}, field);
            if (deeplyCopiedField.dependencies) {
                deeplyCopiedField.dependencies = [...deeplyCopiedField.dependencies];
            }
            Model.fields[fieldName] = deeplyCopiedField;
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
                throw Error(`A record already exists for model "${Model.modelName}" with localId "${localId}".`);
            }
            /**
             * 2. Prepare record state. Assign various keys and values that are
             * expected to be found on every record.
             */
            const record = new Model({ valid: true });
            Object.assign(record, {
                // The messaging env.
                env: this.env,
                // The unique record identifier.
                localId,
                // Field values of record.
                __values: {},
                // revNumber of record for detecting changes in useStore.
                __state: 0,
            });
            // Ensure X2many relations are Set initially (other fields can stay undefined).
            for (const field of Model.__fieldList) {
                record.__values[field.fieldName] = undefined;
                if (field.isX2Many) {
                    record.__values[field.fieldName] = new Set();
                }
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
                if (field.compute || field.related) {
                    // new record should always invoke computed fields.
                    this._registerToComputeField(record, field);
                }
            }
            this._update(record, data2, { allowWriteReadonly: true });
            /**
             * 5. Register post processing operation that are to be delayed at
             * the end of the update cycle.
             */
            this._createdRecords.add(record);
            this._hasAnyChangeDuringCycle = true;

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
        for (const field of Model.__fieldList) {
            if (field.to) {
                // ensure inverses are properly unlinked
                field.parseAndExecuteCommands(record, unlinkAll(), { allowWriteReadonly: true });
            }
        }
        this._hasAnyChangeDuringCycle = true;
        // TODO ideally deleting the record should be done at the top of the
        // method, and it shouldn't be needed to manually remove
        // _toComputeFields, but it is not possible until related are also
        // properly unlinked during `set`.
        this._toComputeFields.delete(record);
        this._toCallOnChange.delete(record);
        delete Model.__records[record.localId];
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
        this._isInUpdateCycle = true;
        // Execution of computes
        while (this._toComputeFields.size > 0) {
            for (const [record, fields] of this._toComputeFields) {
                // Delete at every step to detect if the change due to compute
                // registered extra fields to compute.
                this._toComputeFields.delete(record);
                if (!record.exists()) {
                    throw Error(`Cannot execute computes for already deleted record ${record.localId}.`);
                }
                while (fields.size > 0) {
                    for (const field of fields) {
                        // Delete at every step to detect if the change due to
                        // compute registered extra fields to compute.
                        fields.delete(field);
                        if (field.compute) {
                            this._update(record, { [field.fieldName]: record[field.compute]() }, { allowWriteReadonly: true });
                            continue;
                        }
                        if (field.related) {
                            this._update(record, { [field.fieldName]: field.computeRelated(record) }, { allowWriteReadonly: true });
                            continue;
                        }
                        throw new Error("No compute method defined on this field definition");
                    }
                }
            }
        }
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
        // Increment record rev number (for useStore comparison)
        for (const record of this._updatedRecords) {
            record.__state++;
        }
        this._updatedRecords.clear();
        this._isInUpdateCycle = false;
        // Execution of _created
        while (this._createdRecords.size > 0) {
            for (const record of this._createdRecords) {
                // Delete at every step to avoid recursion, indeed _created
                // might trigger an update cycle itself.
                this._createdRecords.delete(record);
                if (!record.exists()) {
                    throw Error(`Cannot call _created for already deleted record ${record.localId}.`);
                }
                record._created();
            }
        }
        // Execution of "on change".
        while (this._toCallOnChange.size > 0) {
            for (const [record, fields] of this._toCallOnChange) {
                // Delete at every step to detect if the change due to "on change"
                // registered extra fields for which to call "on change".
                this._toCallOnChange.delete(record);
                if (!record.exists()) {
                    throw Error(`Cannot execute 'on change' for already deleted record ${record.localId}.`);
                }
                while (fields.size > 0) {
                    for (const field of fields) {
                        // Delete at every step to detect if the change due to "on change"
                        // registered extra fields for which to call "on change".
                        fields.delete(field);
                        if (field.compute) {
                            const res = record[field.compute]();
                            if (res !== undefined) {
                                throw new Error("'on change' compute method is not supposed to return any value.");
                            }
                            continue;
                        }
                        throw new Error("No compute method defined on this field definition");
                    }
                }
            }
        }
        // Trigger at most one useStore call per update cycle
        if (this._hasAnyChangeDuringCycle) {
            this.env.store.state.messagingRevNumber++;
            this._hasAnyChangeDuringCycle = false;
        }
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
            // Make environment accessible from Model.
            const Model = generatable.factory(Models);
            Model.env = this.env;
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
                        this._applyModelPatchFields(Model, patch.name, patch.patch);
                        break;
                }
            }
            if (!Object.prototype.hasOwnProperty.call(Model, 'modelName')) {
                throw new Error(`Missing static property "modelName" on Model class "${Model.name}".`);
            }
            if (generatedNames.includes(Model.modelName)) {
                throw new Error(`Duplicate model name "${Model.modelName}" shared on 2 distinct Model classes.`);
            }
            Models[Model.modelName] = Model;
            generatedNames.push(Model.modelName);
            toGenerateNames = toGenerateNames.filter(name => name !== Model.modelName);
        }
        /**
         * Check that declared model fields are correct.
         */
        checkDeclaredModels({ Models, env: this.env });
        /**
         * Process declared model fields definitions, so that these field
         * definitions are much easier to use in the system. For instance, all
         * relational field definitions have an inverse, or fields track all their
         * dependents.
         */
        this._processDeclaredFieldsOnModels(Models);
        /**
         * Check that all model fields are correct, notably one relation
         * should have matching reversed relation.
         */
        checkProcessedFieldsOnModels({ Models, env: this.env });
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
            (field.isMany2X && field.isX2Many) ? ModelField.many2many
            : (field.isMany2X && field.isX2One) ? ModelField.one2many
            : (field.isOne2X && field.isX2Many) ? ModelField.many2one
            : (field.isOne2X && field.isX2One) ? ModelField.one2one
            : undefined;
        if (!relFunc) {
            throw new Error(`Cannot compute inverse Relation of "${Model.modelName}/${field.fieldName}".`);
        }
        const inverseField = new ModelField(Object.assign(
            {},
            relFunc(Model.modelName, { inverse: field.fieldName }).properties,
            {
                env: this.env,
                fieldName: `_inverse_${Model.modelName}/${field.fieldName}`,
                modelManager: this,
            }
        ));
        return inverseField;
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
            Model.inverseRelations = [];
            // Make fields aware of their field name.
            for (const [fieldName, fieldDefinition] of Object.entries(Model.fields)) {
                Model.fields[fieldName] = new ModelField(Object.assign({}, fieldDefinition.properties, {
                    env: this.env,
                    fieldName,
                }));
            }
        }
        /**
         * 2. Auto-generate definitions of undeclared inverse relations.
         */
        for (const Model of Object.values(Models)) {
            for (const field of Object.values(Model.fields)) {
                if (!field.to) {
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
         * 3. Generate dependents and inverse-relates on fields.
         * Field definitions are not yet combined, so registration of `dependents`
         * may have to walk structural hierarchy of models in order to find
         * the appropriate field. Also, while dependencies are defined just with
         * field names, dependents require an additional data called a "hash"
         * (= field id), which is a way to identify dependents in an inverse
         * relation. This is necessary because dependents are a subset of an inverse
         * relation.
         */
        for (const Model of Object.values(Models)) {
            for (const field of Object.values(Model.fields)) {
                for (const dependencyFieldName of field.dependencies) {
                    let TargetModel = Model;
                    let dependencyField = TargetModel.fields[dependencyFieldName];
                    while (!dependencyField) {
                        TargetModel = TargetModel.__proto__;
                        dependencyField = TargetModel.fields[dependencyFieldName];
                    }
                    const dependent = [field.id, field.fieldName].join(DEPENDENT_INNER_SEPARATOR);
                    dependencyField.dependents = [
                        ...new Set(dependencyField.dependents.concat([dependent]))
                    ];
                }
                if (field.related) {
                    const [relationName, relatedFieldName] = field.related.split('.');
                    let TargetModel = Model;
                    let relationField = TargetModel.fields[relationName];
                    while (!relationField) {
                        TargetModel = TargetModel.__proto__;
                        relationField = TargetModel.fields[relationName];
                    }
                    const relationFieldDependent = [
                        field.id,
                        field.fieldName,
                    ].join(DEPENDENT_INNER_SEPARATOR);
                    relationField.dependents = [
                        ...new Set(relationField.dependents.concat([relationFieldDependent]))
                    ];
                    const OtherModel = Models[relationField.to];
                    let OtherTargetModel = OtherModel;
                    let relatedField = OtherTargetModel.fields[relatedFieldName];
                    while (!relatedField) {
                        OtherTargetModel = OtherTargetModel.__proto__;
                        relatedField = OtherTargetModel.fields[relatedFieldName];
                    }
                    const relatedFieldDependent = [
                        field.id,
                        relationField.inverse,
                        field.fieldName,
                    ].join(DEPENDENT_INNER_SEPARATOR);
                    relatedField.dependents = [
                        ...new Set(
                            relatedField.dependents.concat([relatedFieldDependent])
                        )
                    ];
                }
            }
        }
        /**
         * 4. Extend definition of fields of a model with the definition of
         * fields of its parents. Field definitions on self has precedence over
         * parented fields.
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
                    if (field) {
                        Model.__combinedFields[targetField.fieldName] = field.combine(targetField);
                    } else {
                        Model.__combinedFields[targetField.fieldName] = targetField;
                    }
                }
                TargetModel = TargetModel.__proto__;
            }
        }
        /**
         * 5. Register final fields and make field accessors, to redirects field
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
                    get() {
                        return field.get(this); // this is bound to record
                    },
                });
            }
            delete Model.__combinedFields;
        }
    }

    /**
     * Registers compute of dependents for the given field, if applicable.
     *
     * @private
     * @param {mail.model} record
     * @param {ModelField} field
     */
    _registerComputeOfDependents(record, field) {
        const Model = record.constructor;
        for (const dependent of field.dependents) {
            const [hash, fieldName1, fieldName2] = dependent.split(
                this.DEPENDENT_INNER_SEPARATOR
            );
            const field1 = Model.__fieldMap[fieldName1];
            if (fieldName2) {
                // "fieldName1.fieldName2" -> dependent is on another record
                if (field1.isX2Many) {
                    for (const otherRecord of record[fieldName1]) {
                        const OtherModel = otherRecord.constructor;
                        const field2 = OtherModel.__fieldMap[fieldName2];
                        if (field2 && field2.hashes.includes(hash)) {
                            this._registerToComputeField(otherRecord, field2);
                        }
                    }
                } else {
                    const otherRecord = record[fieldName1];
                    if (!otherRecord) {
                        continue;
                    }
                    const OtherModel = otherRecord.constructor;
                    const field2 = OtherModel.__fieldMap[fieldName2];
                    if (field2 && field2.hashes.includes(hash)) {
                        this._registerToComputeField(otherRecord, field2);
                    }
                }
            } else {
                // "fieldName1" only -> dependent is on current record
                if (field1 && field1.hashes.includes(hash)) {
                    this._registerToComputeField(record, field1);
                }
            }
        }
    }

    /**
     * Register a pair record/field for the on change step of the update cycle
     * in progress.
     *
     * @private
     * @param {mail.model} record
     * @param {ModelField} field
     */
    _registerToCallOnChange(record, field) {
        if (!this._toCallOnChange.has(record)) {
            this._toCallOnChange.set(record, new Set());
        }
        this._toCallOnChange.get(record).add(field);
    }

    /**
     * Register a pair record/field for the compute step of the update cycle in
     * progress.
     *
     * @private
     * @param {mail.model} record
     * @param {ModelField} field
     */
    _registerToComputeField(record, field) {
        if (field.isOnChange) {
            // Separate "on change" computes from real ones.
            this._registerToCallOnChange(record, field);
            return;
        }
        if (!this._toComputeFields.has(record)) {
            this._toComputeFields.set(record, new Set());
        }
        this._toComputeFields.get(record).add(field);
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
            if (field.readonly && !allowWriteReadonly) {
                throw new Error(`Can't update "${field.fieldName}" (record: "${record.localId}") because it's readonly.`);
            }
            const newVal = data[fieldName];
            if (!field.parseAndExecuteCommands(record, newVal, options)) {
                continue;
            }
            hasChanged = true;
            // flag all dependent fields for compute
            this._registerComputeOfDependents(record, field);
        }
        if (hasChanged) {
            this._updatedRecords.add(record);
            this._hasAnyChangeDuringCycle = true;
        }
        return hasChanged;
    }

}

export default ModelManager;
