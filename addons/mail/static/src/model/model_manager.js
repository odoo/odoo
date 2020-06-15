odoo.define('mail/static/src/model/model_manager.js', function (require) {
'use strict';

const { registry } = require('mail/static/src/model/model_core.js');
const ModelField = require('mail/static/src/model/model_field.js');
const { patchClassMethods, patchInstanceMethods } = require('mail/static/src/utils/utils.js');

/**
 * Inner separator used between 2 bits of information in string that is used to
 * identify record and field to be computed during an update cycle.
 */
const COMPUTE_RECORD_FIELD_INNER_SEPARATOR = "--||--||--";
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
         * The messaging env. It is passed on start(), due to the way mocking
         * of OWL env in tests work...
         */
        this.env = undefined;

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
         * Contains all records. key is local id, while value is the record.
         */
        this._records = {};
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
         * List of "update after" on records that have been registered.
         * These are processed after any explicit update and computed/related
         * fields.
         */
        this._toUpdateAfters = [];
    }

    /**
     * Called when all JS modules that register or patch models have been
     * done. This launches generation of models.
     */
    start(env) {
        this.env = env;
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
        const allRecords = Object.values(this._records)
            .filter(e => e instanceof Model);
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
     * @param {Object} [data={}]
     * @returns {mail.model} newly created record
     */
    create(Model, data = {}) {
        const record = new Model({ valid: true });
        Object.defineProperty(record, 'env', { get: () => Model.env });
        record.localId = record._createRecordLocalId(data);

        // Make state, which contain field values of record that have to
        // be observed in store.
        this.env.store.state[record.localId] = {};
        record.__state = this.env.store.state[record.localId];

        // Make proxified record, so that access to field redirects
        // to field getter.
        const proxifiedRecord = this._makeProxifiedRecord(record);
        this._records[record.localId] = proxifiedRecord;
        proxifiedRecord.init();
        this._makeDefaults(proxifiedRecord);

        const data2 = Object.assign({}, data);
        for (const field of Object.values(Model.fields)) {
            if (field.fieldType !== 'relation') {
                continue;
            }
            if (!field.autocreate) {
                continue;
            }
            data2[field.fieldName] = [['create']];
        }

        for (const field of Object.values(Model.fields)) {
            if (field.compute || field.related) {
                // new record should always invoke computed fields.
                this.registerToComputeField(record, field);
            }
        }

        this.update(proxifiedRecord, data2);

        return proxifiedRecord;
    }

    /**
     * Delete the record. After this operation, it's as if this record never
     * existed. Note that relation are removed, which may delete more relations
     * if some of them are causal.
     *
     * @param {mail.model} record
     */
    delete(record) {
        const Model = record.constructor;
        if (!this.get(Model, record)) {
            // Record has already been deleted.
            // (e.g. unlinking one of its reverse relation was causal)
            return;
        }
        const data = {};
        const recordRelations = Object.values(Model.fields)
            .filter(field => field.fieldType === 'relation');
        for (const relation of recordRelations) {
            if (relation.isCausal) {
                switch (relation.relationType) {
                    case 'one2one':
                    case 'many2one':
                        if (record[relation.fieldName]) {
                            record[relation.fieldName].delete();
                        }
                        break;
                    case 'one2many':
                    case 'many2many':
                        for (const relatedRecord of record[relation.fieldName]) {
                            relatedRecord.delete();
                        }
                        break;
                }
            }
            data[relation.fieldName] = [['unlink-all']];
        }
        record.update(data);
        delete this._records[record.localId];
        delete this.env.store.state[record.localId];
    }

    /**
     * Delete all records.
     */
    deleteAll() {
        for (const record of Object.values(this._records)) {
            record.delete();
        }
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
     * record/local id. Useful to convert a local id to a record, and also to
     * determine whether the record is still "alive" (i.e. not deleted). Note
     * that even if there's a record in the system having provided local id, if
     * the resulting record is not an instance of this model, this getter
     * assumes the record does not exist.
     *
     * @param {mail.model} Model class
     * @param {string|mail.model|undefined} recordOrLocalId
     * @returns {mail.model|undefined} record, if exists
     */
    get(Model, recordOrLocalId) {
        if (recordOrLocalId === undefined) {
            return undefined;
        }
        const record = this._records[
            recordOrLocalId instanceof this.env.models['mail.model']
                ? recordOrLocalId.localId
                : recordOrLocalId
        ];
        if (!(record instanceof Model)) {
            return;
        }
        return record;
    }

    /**
     * This method creates a record or updates one of provided Model, based on
     * provided data. This method assumes that records are uniquely identifiable
     * per "unique find" criteria from data on Model.
     *
     * @param {mail.model} Model class
     * @param {Object} data
     * @returns {mail.model} created or updated record.
     */
    insert(Model, data) {
        let record = Model.find(Model._findFunctionFromData(data));
        if (!record) {
            record = Model.create(data);
        } else {
            record.update(data);
        }
        return record;
    }

    /**
     * Process an update on provided record with provided data. Updating
     * a record consists of applying direct updates first (i.e. explicit
     * ones from `data`) and then indirect ones (i.e. compute/related fields
     * and "after updates").
     *
     * @param {mail.model} record
     * @param {Object} data
     */
    update(record, data) {
        if (!this._isInUpdateCycle) {
            this._isInUpdateCycle = true;
            this._updateDirect(record, data);
            while (
                this._toComputeFields.size > 0 ||
                this._toUpdateAfters.length > 0
            ) {
                if (this._toComputeFields.size > 0) {
                    this._updateComputes();
                } else {
                    this._isHandlingToUpdateAfters = true;
                    // process one update after
                    const [recordToUpdate, previous] = this._toUpdateAfters.pop();
                    const RecordToUpdateModel = recordToUpdate.constructor;
                    if (this.get(RecordToUpdateModel, recordToUpdate)) {
                        recordToUpdate._updateAfter(previous);
                    }
                    this._isHandlingToUpdateAfters = false;
                }
            }
            this._toComputeFields.clear();
            this._isInUpdateCycle = false;
        } else {
            this._updateDirect(record, data);
            if (this._isHandlingToUpdateAfters) {
                this._updateComputes();
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
    registerToComputeField(record, field) {
        const entry = [record.localId, field.fieldName].join(COMPUTE_RECORD_FIELD_INNER_SEPARATOR);
        this._toComputeFields.set(entry, true);
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
                            'autocreate',
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
                            'autocreate',
                            'compute',
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
            Object.defineProperty(Model, 'env', { get: () => this.env });
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
            if (!Model.hasOwnProperty('modelName')) {
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
     * Make default values of its fields for newly created record.
     *
     * @private
     * @param {mail.model} record
     */
    _makeDefaults(record) {
        const Model = record.constructor;
        for (const field of Object.values(Model.fields)) {
            if (field.fieldType === 'attribute') {
                field.write(record, field.default, { registerDependents: false });
            }
            if (field.fieldType === 'relation') {
                if (['one2many', 'many2many'].includes(field.relationType)) {
                    // Ensure X2many relations are arrays by defaults.
                    field.write(record, [], { registerDependents: false });
                } else {
                    field.write(record, undefined, { registerDependents: false });
                }
            }
        }
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
                fieldName: `_inverse_${Model.modelName}/${field.fieldName}`,
                modelManager: this,
            }
        ));
        return inverseField;
    }

    /**
     * Wrap record that has just been created in a proxy. Proxy is useful for
     * auto-getting records when accessing relational fields.
     *
     * @private
     * @param {mail.model} record
     * @return {Proxy<mail.model>} proxified record
     */
    _makeProxifiedRecord(record) {
        const proxifiedRecord = new Proxy(record, {
            get: (target, k) => {
                if (k === 'constructor') {
                    return target[k];
                }
                const field = target.constructor.fields[k];
                if (!field) {
                    // No crash, we allow these reads due to patch()
                    // implementation details that read on `this._super` even
                    // if not set before-hand.
                    return target[k];
                }
                return field.get(proxifiedRecord);
            },
            set: (target, k, newVal) => {
                if (target.constructor.fields[k]) {
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
        return proxifiedRecord;
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
            if (!Model.hasOwnProperty('fields')) {
                Model.fields = {};
            }
            Model.inverseRelations = [];
            // Make fields aware of their field name.
            for (const [fieldName, fieldData] of Object.entries(Model.fields)) {
                Model.fields[fieldName] = new ModelField(Object.assign({}, fieldData, {
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
     * Process registered computed fields in the current update cycle.
     *
     * @private
     */
    _updateComputes() {
        while (this._toComputeFields.size > 0) {
            // process one compute field
            const key = this._toComputeFields.keys().next().value;
            const [recordLocalId, fieldName] = key.split(COMPUTE_RECORD_FIELD_INNER_SEPARATOR);
            this._toComputeFields.delete(key);
            const record = this.env.models['mail.model'].get(recordLocalId);
            if (record) {
                const Model = record.constructor;
                const field = Model.fields[fieldName];
                field.doCompute(record);
            }
        }
    }

    /**
     * Process a direct update on given record with provided data.
     *
     * @private
     * @param {mail.model} record
     * @param {Object} data
     */
    _updateDirect(record, data) {
        const existing = this._toUpdateAfters.find(entry => entry[0] === record);
        if (!existing) {
            // queue updateAfter before calling field.set to ensure previous
            // contains the value at the start of update cycle
            this._toUpdateAfters.push([record, record._updateBefore()]);
        }
        for (const [k, v] of Object.entries(data)) {
            const Model = record.constructor;
            const field = Model.fields[k];
            if (!field) {
                throw new Error(`Cannot create/update record with data unrelated to a field. (model: "${Model.modelName}", non-field attempted update: "${k}")`);
            }
            field.set(record, v);
        }
    }

}

return ModelManager;

});
