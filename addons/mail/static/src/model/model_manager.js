odoo.define('mail/static/src/model/model_manager.js', function (require) {
'use strict';

const { registry } = require('mail/static/src/model/model_core.js');
const ModelField = require('mail/static/src/model/model_field.js');
const { patchClassMethods, patchInstanceMethods } = require('mail/static/src/utils/utils.js');

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

    constructor(env) {
        /**
         * Inner separator used inside string to represent dependents.
         * Set as public attribute so that it can be used by model field.
         */
        this.DEPENDENT_INNER_SEPARATOR = DEPENDENT_INNER_SEPARATOR;
        /**
         * The messaging env.
         */
        this.env = env;
        /**
         * Whether this is currently handling an "update after" on a record.
         * Useful to determine if we should process computed/related fields.
         */
        this._isHandlingToUpdateAfters = false;
        /**
         * Determine whether an update cycle is currently in progress.
         * Useful to determine whether an update should initiate an update
         * cycle or not. An update cycle basically prioritizes processing
         * of all direct updates (i.e. explicit from `data`) before
         * processing computes.
         */
        this._isInUpdateCycle = false;
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
         * Map of "update after" on records that have been registered.
         * These are processed after any explicit update and computed/related
         * fields.
         */
        this._toUpdateAfters = new Map();
    }

    /**
     * Called when all JS modules that register or patch models have been
     * done. This launches generation of models.
     */
    start() {
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
        return this._updateCycle(() => {
            const isMulti = typeof data[Symbol.iterator] === 'function';
            const dataList = isMulti ? data : [data];
            const fieldNames = new Set(Object.keys(Model.fields));
            const fields = Object.values(Model.fields);
            const records = [];
            for (const data of dataList) {
                // Make proxified record, so that access to field redirects
                // to field getter.
                const record = new Proxy(new Model({ valid: true }), {
                    get: (target, k) => {
                        if (!(fieldNames.has(k))) {
                            // No crash, we allow these reads due to patch()
                            // implementation details that read on `this._super` even
                            // if not set before-hand.
                            return target[k];
                        }
                        return Model.fields[k].get(target);
                    },
                    set: (target, k, newVal) => {
                        if (fieldNames.has(k)) {
                            throw new Error("Forbidden to write on record field without .update()!!");
                        } else {
                            // No crash, we allow these writes due to following concerns:
                            // - patch() implementation details that write on `this._super`
                            // - record listeners that need setting on this with `.bind(this)`
                            target[k] = newVal;
                        }
                        return true;
                    },
                });
                record.env = this.env;
                record.localId = Model._createRecordLocalId(data);
                if (Model.get(record.localId)) {
                    throw Error(`A record already exists for model "${Model.modelName}" with localId "${record.localId}".`);
                }
                // Contains field values of record.
                record.__values = {};
                // Contains revNumber of record for checking record update in useStore.
                record.__state = 0;

                Model.__records[record.localId] = record;
                record.init();

                // Ensure X2many relations are Set initially (other fields can stay undefined).
                for (const field of fields) {
                    if (field.fieldType === 'relation') {
                        if (['one2many', 'many2many'].includes(field.relationType)) {
                            record.__values[field.fieldName] = new Set();
                        }
                    }
                }

                const data2 = {};
                for (const field of fields) {
                    if (field.fieldName in data) {
                        data2[field.fieldName] = data[field.fieldName];
                    } else {
                        data2[field.fieldName] = field.default;
                    }
                }

                for (const field of fields) {
                    if (field.compute || field.related) {
                        // new record should always invoke computed fields.
                        this._registerToComputeField(record, field);
                    }
                }

                this.update(record, data2);

                records.push(record);
            }
            return isMulti ? records : records[0];
        });
    }

    /**
     * Delete the record. After this operation, it's as if this record never
     * existed. Note that relation are removed, which may delete more relations
     * if some of them are causal.
     *
     * @param {mail.model} record
     */
    delete(record) {
        this._updateCycle(() => {
            const Model = record.constructor;
            if (!record.exists()) {
                throw Error(`Cannot delete already deleted record ${record.localId}.`);
            }
            for (const field of Object.values(Model.fields)) {
                if (field.fieldType === 'relation') {
                    // ensure inverses are properly unlinked
                    field.set(record, [['unlink-all']]);
                }
            }
            this._toComputeFields.delete(record);
            this._toUpdateAfters.delete(record);
            delete Model.__records[record.localId];
        });
    }

    /**
     * Delete all records.
     */
    deleteAll() {
        this._updateCycle(() => {
            for (const Model of Object.values(this.env.models)) {
                for (const record of Object.values(Model.__records)) {
                    record.delete();
                }
            }
        });
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
        return this._updateCycle(() => {
            const isMulti = typeof data[Symbol.iterator] === 'function';
            const dataList = isMulti ? data : [data];
            const records = [];
            for (const data of dataList) {
                const localId = Model._createRecordLocalId(data);
                let record = Model.get(localId);
                if (!record) {
                    record = Model.create(data);
                } else {
                    record.update(data);
                }
                records.push(record);
            }
            return isMulti ? records : records[0];
        });
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
        return this._updateCycle(() => {
            if (!record.exists()) {
                throw Error(`Cannot update already deleted record ${record.localId}.`);
            }
            if (!this._toUpdateAfters.has(record)) {
                // queue updateAfter before calling field.set to ensure previous
                // contains the value at the start of update cycle
                this._toUpdateAfters.set(record, record._updateBefore());
            }
            const Model = record.constructor;
            let hasChanged = false;
            for (const fieldName of Object.keys(data)) {
                const field = Model.fields[fieldName];
                if (!field) {
                    throw new Error(`Cannot create/update record with data unrelated to a field. (model: "${Model.modelName}", non-field attempted update: "${fieldName}")`);
                }
                if (!field.set(record, data[fieldName])) {
                    continue;
                }
                hasChanged = true;
                // flag all dependent fields for compute
                this._registerComputeOfDependents(record, field);
            }
            if (hasChanged) {
                record.__state++;
            }
            return hasChanged;
        });
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
            if (!Model.fields[fieldName]) {
                Model.fields[fieldName] = field;
            } else {
                Object.assign(Model.fields[fieldName].dependencies, field.dependencies);
            }
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
                // 0. Get parented declared fields
                const parentedMatchingFields = [];
                let TargetModel = Model.__proto__;
                while (Models[TargetModel.modelName]) {
                    if (TargetModel.fields) {
                        const matchingField = TargetModel.fields[fieldName];
                        if (matchingField) {
                            parentedMatchingFields.push(matchingField);
                        }
                    }
                    TargetModel = TargetModel.__proto__;
                }
                // 1. Field type is required.
                if (!(['attribute', 'relation'].includes(field.fieldType))) {
                    throw new Error(`Field "${Model.modelName}/${fieldName}" has unsupported type ${field.fieldType}.`);
                }
                // 2. Invalid keys based on field type.
                if (field.fieldType === 'attribute') {
                    const invalidKeys = Object.keys(field).filter(key =>
                        ![
                            'compute',
                            'default',
                            'dependencies',
                            'fieldType',
                            'related',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field "${Model.modelName}/${fieldName}" contains some invalid keys: "${invalidKeys.join(", ")}".`);
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
                            'related',
                            'relationType',
                            'to',
                        ].includes(key)
                    );
                    if (invalidKeys.length > 0) {
                        throw new Error(`Field "${Model.modelName}/${fieldName}" contains some invalid keys: "${invalidKeys.join(", ")}".`);
                    }
                    if (!Models[field.to]) {
                        throw new Error(`Relational field "${Model.modelName}/${fieldName}" targets to unknown model name "${field.to}".`);
                    }
                    if (field.isCausal && !(['one2many', 'one2one'].includes(field.relationType))) {
                        throw new Error(`Relational field "${Model.modelName}/${fieldName}" has "isCausal" true with a relation of type "${field.relationType}" but "isCausal" is only supported for "one2many" and "one2one".`);
                    }
                }
                // 3. Computed field.
                if (field.compute && !(typeof field.compute === 'string')) {
                    throw new Error(`Field "${Model.modelName}/${fieldName}" property "compute" must be a string (instance method name).`);
                }
                if (field.compute && !(Model.prototype[field.compute])) {
                    throw new Error(`Field "${Model.modelName}/${fieldName}" property "compute" does not refer to an instance method of this Model.`);
                }
                if (
                    field.dependencies &&
                    (!field.compute && !parentedMatchingFields.some(field => field.compute))
                ) {
                    throw new Error(`Field "${Model.modelName}/${fieldName} contains dependendencies but no compute method in itself or parented matching fields (dependencies only make sense for compute fields)."`);
                }
                if (
                    (field.compute || parentedMatchingFields.some(field => field.compute)) &&
                    (field.dependencies || parentedMatchingFields.some(field => field.dependencies))
                ) {
                    if (!(field.dependencies instanceof Array)) {
                        throw new Error(`Compute field "${Model.modelName}/${fieldName}" dependencies must be an array of field names.`);
                    }
                    const unknownDependencies = field.dependencies.every(dependency => !(Model.fields[dependency]));
                    if (unknownDependencies.length > 0) {
                        throw new Error(`Compute field "${Model.modelName}/${fieldName}" contains some unknown dependencies: "${unknownDependencies.join(", ")}".`);
                    }
                }
                // 4. Related field.
                if (field.compute && field.related) {
                    throw new Error(`Field "${Model.modelName}/${fieldName}" cannot be a related and compute field at the same time.`);
                }
                if (field.related) {
                    if (!(typeof field.related === 'string')) {
                        throw new Error(`Field "${Model.modelName}/${fieldName}" property "related" has invalid format.`);
                    }
                    const [relationName, relatedFieldName, other] = field.related.split('.');
                    if (!relationName || !relatedFieldName || other) {
                        throw new Error(`Field "${Model.modelName}/${fieldName}" property "related" has invalid format.`);
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
                        throw new Error(`Related field "${Model.modelName}/${fieldName}" relates to unknown relation name "${relationName}".`);
                    }
                    if (relatedRelation.fieldType !== 'relation') {
                        throw new Error(`Related field "${Model.modelName}/${fieldName}" relates to non-relational field "${relationName}".`);
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
                        throw new Error(`Related field "${Model.modelName}/${fieldName}" relates to unknown related model field "${relatedFieldName}".`);
                    }
                    if (relatedField.fieldType !== field.fieldType) {
                        throw new Error(`Related field "${Model.modelName}/${fieldName}" has mismatch type with its related model field.`);
                    }
                    if (
                        relatedField.fieldType === 'relation' &&
                        relatedField.to !== field.to
                    ) {
                        throw new Error(`Related field "${Model.modelName}/${fieldName}" has mismatch target model name with its related model field.`);
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
                    throw new Error(`Field "${Model.modelName}/${fieldName}" has unsupported type ${field.fieldType}.`);
                }
                if (field.compute && field.related) {
                    throw new Error(`Field "${Model.modelName}/${fieldName}" cannot be a related and compute field at the same time.`);
                }
                if (field.fieldType === 'attribute') {
                    continue;
                }
                if (!field.relationType) {
                    throw new Error(
                        `Field "${Model.modelName}/${fieldName}" must define a relation type in "relationType".`
                    );
                }
                if (!(['one2one', 'one2many', 'many2one', 'many2many'].includes(field.relationType))) {
                    throw new Error(
                        `Field "${Model.modelName}/${fieldName}" has invalid relation type "${field.relationType}".`
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
                        `Model name of relation "${Model.modelName}/${fieldName}" does not exist.`
                    );
                }
                const inverseField = RelatedModel.fields[field.inverse];
                if (!inverseField) {
                    throw new Error(
                        `Relation "${
                            Model.modelName
                        }/${
                            fieldName
                        }" has no inverse field "${RelatedModel.modelName}/${field.inverse}".`
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
                        this._applyModelPatchFields(Model, patch.patch);
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
        this._checkDeclaredFieldsOnModels(Models);
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
        this._checkProcessedFieldsOnModels(Models);
        return Models;
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
            throw new Error(`Cannot compute inverse Relation of "${Model.modelName}/${field.fieldName}".`);
        }
        const inverseField = new ModelField(Object.assign(
            {},
            relFunc(Model.modelName, { inverse: field.fieldName }),
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
            if (!Object.prototype.hasOwnProperty.call(Model, 'fields')) {
                Model.fields = {};
            }
            Model.inverseRelations = [];
            // Make fields aware of their field name.
            for (const [fieldName, fieldData] of Object.entries(Model.fields)) {
                Model.fields[fieldName] = new ModelField(Object.assign({}, fieldData, {
                    env: this.env,
                    fieldName,
                    modelManager: this,
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
        for (const Model of Object.values(Models)) {
            Model.fields = Model.__combinedFields;
            delete Model.__combinedFields;
        }
    }

    /**
     * Registers compute of dependents for the given field, if applicable.
     *
     * @param {mail.model} record
     * @param {ModelField} field
     */
    _registerComputeOfDependents(record, field) {
        const Model = record.constructor;
        for (const dependent of field.dependents) {
            const [hash, currentFieldName, relatedFieldName] = dependent.split(
                this.DEPENDENT_INNER_SEPARATOR
            );
            const field = Model.fields[currentFieldName];
            if (relatedFieldName) {
                if (['one2many', 'many2many'].includes(field.relationType)) {
                    for (const otherRecord of record[currentFieldName]) {
                        const OtherModel = otherRecord.constructor;
                        const field = OtherModel.fields[relatedFieldName];
                        if (field && field.hashes.includes(hash)) {
                            this._registerToComputeField(otherRecord, field);
                        }
                    }
                } else {
                    const otherRecord = record[currentFieldName];
                    if (!otherRecord) {
                        continue;
                    }
                    const OtherModel = otherRecord.constructor;
                    const field = OtherModel.fields[relatedFieldName];
                    if (field && field.hashes.includes(hash)) {
                        this._registerToComputeField(otherRecord, field);
                    }
                }
            } else {
                if (field && field.hashes.includes(hash)) {
                    this._registerToComputeField(record, field);
                }
            }
        }
    }

    /**
     * Register a pair record/field for the compute step of the update cycle in
     * progress.
     *
     * @param {mail.model} record
     * @param {ModelField} field
     */
    _registerToComputeField(record, field) {
        if (!this._toComputeFields.has(record)) {
            this._toComputeFields.set(record, new Set());
        }
        this._toComputeFields.get(record).add(field);
    }

    /**
     * Process registered computed fields in the current update cycle.
     *
     * @private
     */
    _updateComputes() {
        while (this._toComputeFields.size > 0) {
            for (const [record, fields] of this._toComputeFields) {
                this._toComputeFields.delete(record);
                if (!record.exists()) {
                    throw Error(`Cannot execute computes for already deleted record ${record.localId}.`);
                }
                while (fields.size > 0) {
                    for (const field of fields) {
                        fields.delete(field);
                        field.doCompute(record);
                    }
                }
            }
        }
    }

    /**
     * Executes the provided function as part of a single update cycle. This
     * allows the execution of computed fields to happen only once, at the end
     * of the last pending update cycle.
     * It makes sense to call this function when the provided function is
     * expected to create/update/delete records, which in turn would lead to
     * potentially triggering computes.
     *
     * @private
     * @param {function} func synchronous function expected to trigger computes
     * @returns {any} the result of the provided function
     */
    _updateCycle(func) {
        let res;
        if (!this._isInUpdateCycle) {
            this._isInUpdateCycle = true;
            res = func();
            this._updateComputes();
            this._isHandlingToUpdateAfters = true;
            while (this._toUpdateAfters.size > 0) {
                for (const [record, previous] of this._toUpdateAfters) {
                    this._toUpdateAfters.delete(record);
                    if (!record.exists()) {
                        throw Error(`Cannot _updateAfter for already deleted record ${record.localId}.`);
                    }
                    record._updateAfter(previous);
                }
            }
            this._isHandlingToUpdateAfters = false;
            this._isInUpdateCycle = false;
            // trigger at most one useStore call per update cycle
            this.env.store.state.messagingRevNumber++;
        } else {
            const wasHandlingToUpdateAfters = this._isHandlingToUpdateAfters;
            this._isHandlingToUpdateAfters = false;
            res = func();
            if (wasHandlingToUpdateAfters) {
                // Special case for computes triggered during an _updateAfter:
                // execute them at the end of the current cycle, instead of at
                // the end of the last pending cycle. This is because
                // _updateAfter is expected to work with the "final" state just
                // like business code, not with a temporary non-computed state.
                this._updateComputes();
                this._isHandlingToUpdateAfters = true;
            }
        }
        return res;
    }

}

return ModelManager;

});
