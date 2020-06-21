odoo.define('mail/static/src/model/model_field.js', function (require) {
'use strict';

/**
 * Class whose instances represent field on a model.
 * These field definitions are generated from declared fields in static prop
 * `fields` on the model.
 */
class ModelField {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    constructor({
        autocreate = false,
        compute,
        default: def,
        dependencies = [],
        dependents = [],
        fieldName,
        fieldType,
        hashes: extraHashes = [],
        inverse,
        isCausal = false,
        modelManager,
        related,
        relationType,
        to,
    } = {}) {
        const id = _.uniqueId('field_');
        /**
         * This prop only makes sense for fields of type "relation". If set,
         * it automatically creates a new record for this field on creation of
         * record, and auto-links with this record.
         */
        this.autocreate = autocreate;
        /**
         * If set, this field acts as a computed field, and this prop
         * contains the name of the instance method that computes the value
         * for this field. This compute method is called on creation of record
         * and whenever some of its dependencies change. @see dependencies
         */
        this.compute = compute;
        /**
         * Default value for this field. Used on creation of this field, to
         * set a value by default.
         */
        this.default = def;
        /**
         * List of field on current record that this field depends on for its
         * `compute` method. Useful to determine whether this field should be
         * registered for recomputation when some record fields have changed.
         * This list must be declared in model definition, or compute method
         * is only computed once.
         */
        this.dependencies = dependencies;
        /**
         * List of fields that are dependent of this field. They should never
         * be declared, and are automatically generated while processing
         * declared fields. This is populated by compute `dependencies` and
         * `related`.
         */
        this.dependents = dependents;
        /**
         * Name of the field in the definition of fields on model.
         */
        this.fieldName = fieldName;
        /**
         * Type of this field. 2 types of fields are currently supported:
         *
         *   1. 'attribute': fields that store primitive values like integers,
         *                   booleans, strings, objects, array, etc.
         *
         *   2. 'relation': fields that relate to some other records.
         */
        this.fieldType = fieldType;
        /**
         * List of hashes registered on this field definition. Technical
         * prop that is specifically used in processing of dependent
         * fields, useful to clearly identify which fields of a relation are
         * dependents and must be registered for computed. Indeed, not all
         * related records may have a field that depends on changed field,
         * especially when dependency is defined on sub-model on a relation in
         * a super-model.
         *
         * To illustrate the purpose of this hash, suppose following definition
         * of models and fields:
         *
         * - 3 models (A, B, C) and 3 fields (x, y, z)
         * - A.fields: { x: one2one(C, inverse: x') }
         * - B extends A
         * - B.fields: { z: related(x.y) }
         * - C.fields: { y: attribute }
         *
         * Visually:
         *               x'
         *          <-----------
         *        A -----------> C { y }
         *        ^      x
         *        |
         *        | (extends)
         *        |
         *        B { z = x.y }
         *
         * If z has a dependency on x.y, it means y has a dependent on x'.z.
         * Note that field z exists on B but not on all A. To determine which
         * kinds of records in relation x' are dependent on y, y is aware of an
         * hash on this dependent, and any dependents who has this hash in list
         * of hashes are actual dependents.
         */
        this.hashes = extraHashes.concat([id]);
        /**
         * Identification for this field definition. Useful to map a dependent
         * from a dependency. Indeed, declared field definitions use
         * 'dependencies' but technical process need inverse as 'dependents'.
         * Dependencies just need name of fields, but dependents cannot just
         * rely on inverse field names because these dependents are a subset.
         */
        this.id = id;
        /**
         * This prop only makes sense in a relational field. This contains
         * the name of the field name in the inverse relation. This may not
         * be defined in declared field definitions, but processed relational
         * field definitions always have inverses.
         */
        this.inverse = inverse;
        /**
         * This prop only makes sense in a relational field. If set, when this
         * relation is removed, the related record is automatically deleted.
         */
        this.isCausal = isCausal;
        /**
         * Reference to the model manager.
         */
        this.modelManager = modelManager;
        /**
         * If set, this field acts as a related field, and this prop contains
         * a string that references the related field. It should have the
         * following format: '<relationName>.<relatedFieldName>', where
         * <relationName> is a relational field name on this model or a parent
         * model (note: could itself be computed or related), and
         * <relatedFieldName> is the name of field on the records that are
         * related to current record from this relation. When there are more
         * than one record in the relation, it maps all related fields per
         * record in relation.
         *
         * FIXME: currently flatten map due to bug, improvement is planned
         * see Task-id 2261221
         */
        this.related = related;
        /**
         * This prop only makes sense in a relational field. Determine which
         * type of relation there is between current record and other records.
         * 4 types of relation are supported: 'one2one', 'one2many', 'many2one'
         * and 'many2many'.
         */
        this.relationType = relationType;
        /**
         * This prop only makes sense in a relational field. Determine which
         * model name this relation refers to.
         */
        this.to = to;
    }

    /**
     * Define an attribute field.
     *
     * @param {Object} [options]
     * @returns {Object}
     */
    static attr(options) {
        return Object.assign({ fieldType: 'attribute' }, options);
    }

    /**
     * Define a many2many field.
     *
     * @param {string} modelName
     * @param {Object} [options]
     * @returns {Object}
     */
    static many2many(modelName, options) {
        return ModelField._relation(modelName, Object.assign({}, options, { relationType: 'many2many' }));
    }

    /**
     * Define a many2one field.
     *
     * @param {string} modelName
     * @param {Object} [options]
     * @returns {Object}
     */
    static many2one(modelName, options) {
        return ModelField._relation(modelName, Object.assign({}, options, { relationType: 'many2one' }));
    }

    /**
     * Define a one2many field.
     *
     * @param {string} modelName
     * @param {Object} [options]
     * @returns {Object}
     */
    static one2many(modelName, options) {
        return ModelField._relation(modelName, Object.assign({}, options, { relationType: 'one2many' }));
    }

    /**
     * Define a one2one field.
     *
     * @param {string} modelName
     * @param {Object} [options]
     * @returns {Object}
     */
    static one2one(modelName, options) {
        return ModelField._relation(modelName, Object.assign({}, options, { relationType: 'one2one' }));
    }

    /**
     * Combine current field definition with provided field definition and
     * return the combined field definition. Useful to track list of hashes of
     * a given field, which is necessary for the working of dependent fields
     * (computed and related fields).
     *
     * @param {ModelField} field
     * @returns {ModelField}
     */
    combine(field) {
        return new ModelField(Object.assign({}, this, {
            dependencies: this.dependencies.concat(field.dependencies),
            hashes: this.hashes.concat(field.hashes),
        }));
    }

    /**
     * Perform computation of this field, which is either a computed or related
     * field.
     *
     * @param {mail.model} record
     */
    doCompute(record) {
        if (this.compute) {
            this.set(record, record[this.compute]());
            return;
        }
        if (this.related) {
            this.set(record, this._computeRelated(record));
            return;
        }
        throw new Error("No compute method defined on this field definition");
    }

    /**
     * Get the env with messaging.
     *
     * @returns {mail/static/src/env/env.js}
     */
    get env() {
        return this.modelManager.env;
    }

    /**
     * Get the value associated to this field. Relations must convert record
     * local ids to records.
     *
     * @param {mail.model} record
     * @returns {any}
     */
    get(record) {
        if (this.fieldType === 'attribute') {
            return this.read(record);
        }
        if (this.fieldType === 'relation') {
            const OtherModel = this.env.models[this.to];
            if (['one2one', 'many2one'].includes(this.relationType)) {
                return OtherModel.get(this.read(record));
            }
            return this.read(record)
                .map(localId => OtherModel.get(localId))
                /**
                 * FIXME: Stored relation may still contain
                 * outdated records.
                 */
                .filter(record => !!record);
        }
        throw new Error(`cannot get field with unsupported type ${this.fieldType}.`);
    }

    /**
     * Get the raw value associated to this field. For relations, this means
     * the local id or list of local ids of records in this relational field.
     *
     * @param {mail.model} record
     * @returns {any}
     */
    read(record) {
        return record.__state[this.fieldName];
    }

    /**
     * Set a value on this field. The format of the value comes from business
     * code.
     *
     * @param {mail.model} record
     * @param {any} newVal
     */
    set(record, newVal) {
        if (this.fieldType === 'attribute') {
            this.write(record, newVal);
        }
        if (this.fieldType === 'relation') {
            for (const val of newVal) {
                switch (val[0]) {
                    case 'create':
                        this._setRelationCreate(record, val[1]);
                        break;
                    case 'insert':
                        this._setRelationInsert(record, val[1]);
                        break;
                    case 'insert-and-replace':
                        this._setRelationInsertAndReplace(record, val[1]);
                        break;
                    case 'link':
                        this._setRelationLink(record, val[1]);
                        break;
                    case 'replace':
                        // TODO IMP replace should not unlink-all (task-2270780)
                        this._setRelationUnlink(record, null);
                        this._setRelationLink(record, val[1]);
                        break;
                    case 'unlink':
                        this._setRelationUnlink(record, val[1]);
                        break;
                    case 'unlink-all':
                        this._setRelationUnlink(record, null);
                        break;
                }
            }
        }
    }

    /**
     * Set a value in state associated to this field. Value corresponds exactly
     * that what is stored on this field, like local id or list of local ids
     * for a relational field. If the value changes, dependent fields are
     * automatically registered for (re-)computation.
     *
     * @param {mail.model} record
     * @param {any} newVal
     * @param {Object} [param2={}]
     * @param {Object} [param2.registerDependents=true] If set, write
     *   on this field with changed value registers dependent fields for compute.
     *   Of course, we almost always want to register them, so that they reflect
     *   the value with their dependencies. Disabling this feature prevents
     *   useless potentially heavy computation, like when setting default values.
     */
    write(record, newVal, { registerDependents = true } = {}) {
        if (this.read(record) === newVal) {
            return;
        }
        const prevStringified = JSON.stringify(this.read(record));
        record.__state[this.fieldName] = newVal;
        const newStringified = JSON.stringify(this.read(record));
        if (this._containsRecords(newVal)) {
            throw new Error("Forbidden write operation with records in the __state!!");
        }
        if (newStringified === prevStringified) {
            // value unchanged, don't need to compute dependent fields
            return;
        }
        if (!registerDependents) {
            return;
        }

        // flag all dependent fields for compute
        for (const dependent of this.dependents) {
            const [hash, currentFieldName, relatedFieldName] = dependent.split(
                this.modelManager.DEPENDENT_INNER_SEPARATOR
            );
            if (relatedFieldName) {
                const Model = record.constructor;
                const relationField = Model.fields[currentFieldName];
                if (['one2many', 'many2many'].includes(relationField.relationType)) {
                    for (const otherRecord of record[currentFieldName]) {
                        const OtherModel = otherRecord.constructor;
                        const field = OtherModel.fields[relatedFieldName];
                        if (field && field.hashes.includes(hash)) {
                            this.modelManager.registerToComputeField(otherRecord, field);
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
                        this.modelManager.registerToComputeField(otherRecord, field);
                    }
                }
            } else {
                const Model = record.constructor;
                const field = Model.fields[currentFieldName];
                if (field && field.hashes.includes(hash)) {
                    this.modelManager.registerToComputeField(record, field);
                }
            }
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} modelName
     * @param {Object} [options]
     */
    static _relation(modelName, options) {
        return Object.assign({
            fieldType: 'relation',
            to: modelName,
        }, options);
    }

    /**
     * Compute method when this field is related.
     *
     * @private
     * @param {mail.model} record
     */
    _computeRelated(record) {
        const [relationName, relatedFieldName] = this.related.split('.');
        const Model = record.constructor;
        const relationField = Model.fields[relationName];
        if (['one2many', 'many2many'].includes(relationField.relationType)) {
            const newVal = [];
            for (const otherRecord of record[relationName]) {
                const OtherModel = otherRecord.constructor;
                const otherField = OtherModel.fields[relatedFieldName];
                const otherValue = otherField.get(otherRecord);
                if (otherValue) {
                    if (otherValue instanceof Array) {
                        // avoid nested array if otherField is x2many too
                        // TODO IMP task-2261221
                        for (const v of otherValue) {
                            newVal.push(v);
                        }
                    } else {
                        newVal.push(otherValue);
                    }
                }
            }
            if (this.fieldType === 'relation') {
                return [['replace', newVal]];
            }
            return newVal;
        }
        const otherRecord = record[relationName];
        if (otherRecord) {
            const OtherModel = otherRecord.constructor;
            const otherField = OtherModel.fields[relatedFieldName];
            const newVal = otherField.get(otherRecord);
            if (this.fieldType === 'relation') {
                if (newVal) {
                    return [['replace', newVal]];
                } else {
                    return [['unlink-all']];
                }
            }
            return newVal;
        }
        if (this.fieldType === 'relation') {
            return [];
        }
    }

    /**
     * Determines whether the provided value contains some records. Useful to
     * prevent writing records directly in state of this field, which should be
     * treated as buggy design. Indeed, state of field should only contain
     * either a primitive type or a simple datastructure containing itself
     * simple datastructures too.
     *
     * @private
     * @param {any} val
     * @returns {boolean}
     */
    _containsRecords(val) {
        if (!val) {
            return false;
        }
        if (val instanceof this.env.models['mail.model']) {
            return true;
        }
        if (!(val instanceof Array)) {
            return false;
        }
        if (val.length > 0 && val[0] instanceof this.env.models['mail.model']) {
            return true;
        }
        return false;
    }

    /**
     * Converts given value to expected format for x2many processing, which is
     * an array of localId.
     *
     * @private
     * @param {string|mail.model|<mail.model|string>[]} newValue
     * @returns {string[]}
     */
    _setRelationConvertX2ManyValue(newValue) {
        if (newValue instanceof Array) {
            return newValue.map(v => this._setRelationConvertX2OneValue(v));
        }
        return [this._setRelationConvertX2OneValue(newValue)];
    }

    /**
     * Converts given value to expected format for x2one processing, which is
     * a localId.
     *
     * @private
     * @param {string|mail.model} newValue
     * @returns {string}
     */
    _setRelationConvertX2OneValue(newValue) {
        return newValue instanceof this.env.models['mail.model'] ? newValue.localId : newValue;
    }

    /**
     * Set on this relational field in 'create' mode. Basically data provided
     * during set on this relational field contain data to create new records,
     * which themselves must be linked to record of this field by means of
     * this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     */
    _setRelationCreate(record, data) {
        const OtherModel = this.env.models[this.to];
        let other;
        if (['one2one', 'many2one'].includes(this.relationType)) {
            other = OtherModel.create(data);
        } else {
            if (data instanceof Array) {
                other = data.map(d => OtherModel.create(d));
            } else {
                other = OtherModel.create(data);
            }
        }
        this._setRelationLink(record, other);
    }

    /**
     * Set on this relational field in 'insert' mode. Basically data provided
     * during set on this relational field contain data to insert records,
     * which themselves must be linked to record of this field by means of
     * this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     */
    _setRelationInsert(record, data) {
        const OtherModel = this.env.models[this.to];
        let other;
        if (['one2one', 'many2one'].includes(this.relationType)) {
            other = OtherModel.insert(data);
        } else {
            if (data instanceof Array) {
                other = data.map(d => OtherModel.insert(d));
            } else {
                other = OtherModel.insert(data);
            }
        }
        this._setRelationLink(record, other);
    }

    /**
     * Set on this relational field in 'insert-and-repalce' mode. Basically
     * data provided during set on this relational field contain data to insert
     * records, which themselves must replace value on this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     */
    _setRelationInsertAndReplace(record, data) {
        // unlink must be done before insert:
        // because unlink might trigger delete due to causality and new data
        // shouldn't be deleted just after being inserted
        // TODO IMP insert-and-replace should not unlink-all (task-2270780)
        this._setRelationUnlink(record, null);
        const OtherModel = this.env.models[this.to];
        let other;
        if (['one2one', 'many2one'].includes(this.relationType)) {
            other = OtherModel.insert(data);
        } else {
            if (data instanceof Array) {
                other = data.map(d => OtherModel.insert(d));
            } else {
                other = OtherModel.insert(data);
            }
        }
        this._setRelationLink(record, other);
    }

    /**
     * Set a 'link' operation on this relational field.
     *
     * @private
     * @param {string|string[]|mail.model|mail.model[]} newValue
     */
    _setRelationLink(record, newValue) {
        const Model = record.constructor;
        if (!Model.get(record)) {
            // current record may be deleted due to causality
            return;
        }
        switch (this.relationType) {
            case 'many2many':
                this._setRelationLinkMany2Many(record, newValue);
                break;
            case 'many2one':
                this._setRelationLinkMany2One(record, newValue);
                break;
            case 'one2many':
                this._setRelationLinkOne2Many(record, newValue);
                break;
            case 'one2one':
                this._setRelationLinkOne2One(record, newValue);
                break;
        }
    }

    /**
     * Handling of a `set` 'link' of a many2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model|<mail.model|string>[]} newValue
     */
    _setRelationLinkMany2Many(record, newValue) {
        // convert newValue to array of localId
        const newLocalIds = this._setRelationConvertX2ManyValue(newValue);
        const OtherModel = this.env.models[this.to];

        for (const newLocalId of newLocalIds) {
            // read in loop to catch potential changes from previous iteration
            const prevLocalIds = this.read(record);

            // other record already linked, avoid linking twice
            if (prevLocalIds.includes(newLocalId)) {
                continue;
            }

            const newOtherRecord = OtherModel.get(newLocalId);
            // other record may be deleted due to causality, avoid linking
            // deleted records
            if (!newOtherRecord) {
                continue;
            }

            // link other record to current record
            this.write(record, prevLocalIds.concat([newLocalId]));

            // link current record to other record
            newOtherRecord.update({
                [this.inverse]: [['link', record]],
            });
        }
    }

    /**
     * Handling of a `set` 'link' of a many2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model} newValue
     */
    _setRelationLinkMany2One(record, newValue) {
        // convert newValue to localId
        const newLocalId = this._setRelationConvertX2OneValue(newValue);
        const OtherModel = this.env.models[this.to];
        const prevLocalId = this.read(record);

        // other record already linked, avoid linking twice
        if (prevLocalId === newLocalId) {
            return;
        }

        // unlink previous other record from current record
        this.write(record, undefined);

        const prevOtherRecord = OtherModel.get(prevLocalId);
        // there may be no previous other record or the previous other record
        // may be deleted due to causality
        if (prevOtherRecord) {
            // unlink current record from previous other record
            prevOtherRecord.update({
                [this.inverse]: [['unlink', record]],
            });
        }

        const newOtherRecord = OtherModel.get(newLocalId);
        // other record may be deleted due to causality, avoid linking
        // deleted records
        if (!newOtherRecord) {
            return;
        }

        // link other record to current records
        this.write(record, newLocalId);

        // link current record to other record
        newOtherRecord.update({
            [this.inverse]: [['link', record]],
        });
    }

    /**
     * Handling of a `set` 'link' of an one2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model|<string|mail.model>[]} newValue
     */
    _setRelationLinkOne2Many(record, newValue) {
        // convert newValue to array of localId
        const newLocalIds = this._setRelationConvertX2ManyValue(newValue);
        const OtherModel = this.env.models[this.to];

        for (const newLocalId of newLocalIds) {
            // read in loop to catch potential changes from previous iteration
            const prevLocalIds = this.read(record);

            // other record already linked, avoid linking twice
            if (prevLocalIds.includes(newLocalId)) {
                continue;
            }

            const newOtherRecord = OtherModel.get(newLocalId);
            // other record may be deleted due to causality, avoid linking
            // deleted records
            if (!newOtherRecord) {
                continue;
            }

            // link other record to current record
            this.write(record, prevLocalIds.concat([newLocalId]));

            // link current record to other record
            newOtherRecord.update({
                [this.inverse]: [['link', record]],
            });
        }
    }

    /**
     * Handling of a `set` 'link' of an one2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model} value
     */
    _setRelationLinkOne2One(record, newValue) {
        // convert newValue to localId
        const newLocalId = this._setRelationConvertX2OneValue(newValue);
        const prevLocalId = this.read(record);
        const OtherModel = this.env.models[this.to];

        // other record already linked, avoid linking twice
        if (prevLocalId === newLocalId) {
            return;
        }

        // unlink previous other record from current record
        this.write(record, undefined);

        const prevOtherRecord = OtherModel.get(prevLocalId);
        // there may be no previous other record or the previous other record
        // may be deleted due to causality
        if (prevOtherRecord) {
            // unlink current record from previous other record
            prevOtherRecord.update({
                [this.inverse]: [['unlink', record]],
            });
            // apply causality
            if (this.isCausal) {
                prevOtherRecord.delete();
            }
        }

        const newOtherRecord = OtherModel.get(newLocalId);
        // other record may be deleted due to causality, avoid linking deleted
        // records
        if (!newOtherRecord) {
            return;
        }

        // link other record to current record
        this.write(record, newLocalId);

        // link current record to other record
        newOtherRecord.update({
            [this.inverse]: [['link', record]],
        });
    }

    /**
     * Set an 'unlink' operation on this relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|string[]|mail.model|mail.model[]|null} newValue
     */
    _setRelationUnlink(record, newValue) {
        const Model = record.constructor;
        if (!Model.get(record)) {
            // current record may be deleted due to causality
            return;
        }
        switch (this.relationType) {
            case 'many2many':
                this._setRelationUnlinkMany2Many(record, newValue);
                break;
            case 'many2one':
                this._setRelationUnlinkMany2One(record);
                break;
            case 'one2many':
                this._setRelationUnlinkOne2Many(record, newValue);
                break;
            case 'one2one':
                this._setRelationUnlinkOne2One(record);
                break;
        }
    }

    /**
     * Handling of a `set` 'unlink' of a many2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model|<string|mail.model>[]|null} newValue
     */
    _setRelationUnlinkMany2Many(record, newValue) {
        // convert newValue to array of localId, null is considered unlink all
        const otherLocalIds = newValue === null
            ? [...this.read(record)]
            : this._setRelationConvertX2ManyValue(newValue);
        const OtherModel = this.env.models[this.to];

        for (const otherLocalId of otherLocalIds) {
            // read in loop to catch potential changes from previous iteration
            const prevLocalIds = this.read(record);

            // other record already unlinked, avoid useless processing
            if (!prevLocalIds.includes(otherLocalId)) {
                continue;
            }

            // unlink other record from current record
            this.write(record, prevLocalIds.filter(
                localId => localId !== otherLocalId
            ));

            const otherRecord = OtherModel.get(otherLocalId);
            // other record may be deleted due to causality, avoid useless
            // processing
            if (otherRecord) {
                // unlink current record from other record
                otherRecord.update({
                    [this.inverse]: [['unlink', record]],
                });
            }
        }
    }

    /**
     * Handling of a `set` 'unlink' of a many2one relational field.
     *
     * @private
     * @param {mail.model} record
     */
    _setRelationUnlinkMany2One(record) {
        const otherLocalId = this.read(record);
        const OtherModel = this.env.models[this.to];

        // other record already unlinked, avoid useless processing
        if (!otherLocalId) {
            return;
        }

        // unlink other record from current record
        this.write(record, undefined);

        const otherRecord = OtherModel.get(otherLocalId);
        // other record may be deleted due to causality, avoid useless
        // processing
        if (otherRecord) {
            // unlink current record from other record
            otherRecord.update({
                [this.inverse]: [['unlink', record]],
            });
        }
    }

    /**
     * Handling of a `set` 'unlink' of an one2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {string|mail.model|<string|mail.model>[]|null} newValue
     *   if null, unlink all items in the relation of provided record.
     */
    _setRelationUnlinkOne2Many(record, newValue) {
        // convert newValue to array of localId, null is considered unlink all
        const otherLocalIds = newValue === null
            ? [...this.read(record)]
            : this._setRelationConvertX2ManyValue(newValue);
        const OtherModel = this.env.models[this.to];

        for (const otherLocalId of otherLocalIds) {
            // read in loop to catch potential changes from previous iteration
            const prevLocalIds = this.read(record);

            // other record already unlinked, avoid useless processing
            if (!prevLocalIds.includes(otherLocalId)) {
                continue;
            }

            // unlink other record from current record
            this.write(record, prevLocalIds.filter(
                localId => localId !== otherLocalId
            ));

            const otherRecord = OtherModel.get(otherLocalId);
            // other record may be deleted due to causality, avoid useless
            // processing
            if (otherRecord) {
                // unlink current record from other record
                otherRecord.update({
                    [this.inverse]: [['unlink', record]],
                });
            }
        }
    }

    /**
     * Handling of a `set` 'unlink' of an one2one relational field.
     *
     * @private
     * @param {mail.model} record
     */
    _setRelationUnlinkOne2One(record) {
        const otherLocalId = this.read(record);
        const OtherModel = this.env.models[this.to];

        // other record already unlinked, avoid useless processing
        if (!otherLocalId) {
            return;
        }

        // unlink other record from current record
        this.write(record, undefined);

        const otherRecord = OtherModel.get(otherLocalId);
        // other record may be deleted due to causality, avoid useless
        // processing
        if (otherRecord) {
            // unlink current record from other record
            otherRecord.update({
                [this.inverse]: [['unlink', record]],
            });
        }
    }

}

return ModelField;

});
