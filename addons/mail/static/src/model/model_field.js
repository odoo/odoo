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
        compute,
        default: def,
        dependencies = [],
        dependents = [],
        env,
        fieldName,
        fieldType,
        hashes: extraHashes = [],
        inverse,
        isCausal = false,
        related,
        relationType,
        to,
    } = {}) {
        const id = _.uniqueId('field_');
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
         * The messaging env.
         */
        this.env = env;
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

        if (!this.default && this.fieldType === 'relation') {
            // default value for relational fields is the empty command
            this.default = [];
        }
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
     * @returns {boolean} whether the value changed for the current field
     */
    doCompute(record) {
        if (this.compute) {
            return record.update({ [this.fieldName]: record[this.compute]() });
        }
        if (this.related) {
            return record.update({ [this.fieldName]: this._computeRelated(record) });
        }
        throw new Error("No compute method defined on this field definition");
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
            if (['one2one', 'many2one'].includes(this.relationType)) {
                return this.read(record);
            }
            return [...this.read(record)];
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
        return record.__values[this.fieldName];
    }

    /**
     * Set a value on this field. The format of the value comes from business
     * code.
     *
     * @param {mail.model} record
     * @param {any} newVal
     * @returns {boolean} whether the value changed for the current field
     */
    set(record, newVal) {
        const currentValue = this.read(record);
        if (this.fieldType === 'attribute') {
            if (currentValue === newVal) {
                return false;
            }
            record.__values[this.fieldName] = newVal;
            return true;
        }
        if (this.fieldType === 'relation') {
            let hasChanged = false;
            for (const val of newVal) {
                switch (val[0]) {
                    case 'create':
                        if (this._setRelationCreate(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert':
                        if (this._setRelationInsert(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert-and-replace':
                        if (this._setRelationInsertAndReplace(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'link':
                        if (this._setRelationLink(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'replace':
                        // TODO IMP replace should not unlink-all (task-2270780)
                        if (this._setRelationUnlink(record, currentValue)) {
                            hasChanged = true;
                        }
                        if (this._setRelationLink(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink':
                        if (this._setRelationUnlink(record, val[1])) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink-all':
                        if (this._setRelationUnlink(record, currentValue)) {
                            hasChanged = true;
                        }
                        break;
                }
            }
            return hasChanged;
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
     * Converts given value to expected format for x2many processing, which is
     * an iterable of records.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @returns {mail.model[]}
     */
    _setRelationConvertX2ManyValue(newValue) {
        if (typeof newValue[Symbol.iterator] === 'function') {
            for (const value of newValue) {
                this._verifyRelationalValue(value);
            }
            return newValue;
        }
        this._verifyRelationalValue(newValue);
        return [newValue];
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
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationCreate(record, data) {
        const OtherModel = this.env.models[this.to];
        const other = OtherModel.create(data);
        return this._setRelationLink(record, other);
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
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsert(record, data) {
        const OtherModel = this.env.models[this.to];
        const other = OtherModel.insert(data);
        return this._setRelationLink(record, other);
    }

    /**
     * Set on this relational field in 'insert-and-repalce' mode. Basically
     * data provided during set on this relational field contain data to insert
     * records, which themselves must replace value on this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsertAndReplace(record, data) {
        // unlink must be done before insert:
        // because unlink might trigger delete due to causality and new data
        // shouldn't be deleted just after being inserted
        // TODO IMP insert-and-replace should not unlink-all (task-2270780)
        let hasChanged = false;
        if (this._setRelationUnlink(record, this.read(record))) {
            hasChanged = true;
        }
        const OtherModel = this.env.models[this.to];
        const other = OtherModel.insert(data);
        if (this._setRelationLink(record, other)) {
            hasChanged = true;
        }
        return hasChanged;
    }

    /**
     * Set a 'link' operation on this relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLink(record, newValue) {
        switch (this.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationLinkX2Many(record, newValue);
            case 'many2one':
            case 'one2one':
                return this._setRelationLinkX2One(record, newValue);
        }
    }

    /**
     * Handling of a `set` 'link' of a x2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2Many(record, newValue) {
        const toAddOtherRecords = this._setRelationConvertX2ManyValue(newValue);
        const otherRecords = this.read(record);

        let isAdding = false;
        for (const toAddOtherRecord of toAddOtherRecords) {
            // other record already linked, avoid linking twice
            if (otherRecords.has(toAddOtherRecord)) {
                continue;
            }
            isAdding = true;
            // link other records to current record
            otherRecords.add(toAddOtherRecord);
            // link current record to other records
            toAddOtherRecord.update({
                [this.inverse]: [['link', record]],
            });
        }
        return isAdding;
    }

    /**
     * Handling of a `set` 'link' of an x2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model} toAddOtherRecord
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2One(record, toAddOtherRecord) {
        this._verifyRelationalValue(toAddOtherRecord);
        const prevOtherRecord = this.read(record);
        // other record already linked, avoid linking twice
        if (prevOtherRecord === toAddOtherRecord) {
            return false;
        }
        // unlink to properly update previous inverse before linking new value
        this._setRelationUnlinkX2One(record);
        // link other record to current record
        record.__values[this.fieldName] = toAddOtherRecord;
        // link current record to other record
        toAddOtherRecord.update({
            [this.inverse]: [['link', record]],
        });
        return true;
    }

    /**
     * Set an 'unlink' operation on this relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlink(record, newValue) {
        switch (this.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationUnlinkX2Many(record, newValue);
            case 'many2one':
            case 'one2one':
                return this._setRelationUnlinkX2One(record);
        }
    }

    /**
     * Handling of a `set` 'unlink' of a x2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2Many(record, newValue) {
        const toDeleteOtherRecords = this._setRelationConvertX2ManyValue(newValue);
        const otherRecords = this.read(record);

        let isDeleting = false;
        for (const toDeleteOtherRecord of toDeleteOtherRecords) {
            // unlink other record from current record
            const wasDeleted = otherRecords.delete(toDeleteOtherRecord);
            if (!wasDeleted) {
                continue;
            }
            isDeleting = true;
            // unlink current record from other records
            toDeleteOtherRecord.update({
                [this.inverse]: [['unlink', record]],
            });
            // apply causality
            if (this.isCausal) {
                toDeleteOtherRecord.delete();
            }
        }
        return isDeleting;
    }

    /**
     * Handling of a `set` 'unlink' of a x2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2One(record) {
        const toDeleteOtherRecord = this.read(record);
        // other record already unlinked, avoid useless processing
        if (!toDeleteOtherRecord) {
            return false;
        }
        // unlink other record from current record
        record.__values[this.fieldName] = undefined;
        // unlink current record from other record
        toDeleteOtherRecord.update({
            [this.inverse]: [['unlink', record]],
        });
        // apply causality
        if (this.isCausal) {
            toDeleteOtherRecord.delete();
        }
        return true;
    }

    /**
     * Verifies the given relational value makes sense for the current field.
     * In particular the given value must be a record, it must be non-deleted,
     * and it must originates from relational `to` model (or its subclasses).
     *
     * @private
     * @param {mail.model} record
     * @throws {Error} if record does not satisfy related model
     */
    _verifyRelationalValue(record) {
        const OtherModel = this.env.models[this.to];
        if (!OtherModel.get(record.localId, { isCheckingInheritance: true })) {
            throw Error(`Record ${record.localId} is not valid for relational field ${this.fieldName}.`);
        }
    }

}

return ModelField;

});
