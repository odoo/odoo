odoo.define('mail/static/src/model/model_field.js', function (require) {
'use strict';

const { clear, FieldCommand } = require('mail/static/src/model/model_field_command.js');

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
     * Clears the value of this field on the given record. It consists of
     * setting this to its default value. In particular, using `clear` is the
     * only way to write `undefined` on a field, as long as `undefined` is its
     * default value. Relational fields are always unlinked before the default
     * is applied.
     *
     * @param {mail.model} record
     * @param {options} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    clear(record, options) {
        let hasChanged = false;
        if (this.fieldType === 'relation') {
            if (this.parseAndExecuteCommands(record, [['unlink-all']], options)) {
                hasChanged = true;
            }
        }
        if (this.parseAndExecuteCommands(record, this.default, options)) {
            hasChanged = true;
        }
        return hasChanged;
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
     * Compute method when this field is related.
     *
     * @private
     * @param {mail.model} record
     */
    computeRelated(record) {
        const [relationName, relatedFieldName] = this.related.split('.');
        const Model = record.constructor;
        const relationField = Model.__fieldMap[relationName];
        if (['one2many', 'many2many'].includes(relationField.relationType)) {
            const newVal = [];
            for (const otherRecord of record[relationName]) {
                const OtherModel = otherRecord.constructor;
                const otherField = OtherModel.__fieldMap[relatedFieldName];
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
            const otherField = OtherModel.__fieldMap[relatedFieldName];
            const newVal = otherField.get(otherRecord);
            if (newVal === undefined) {
                return clear();
            }
            if (this.fieldType === 'relation') {
                return [['replace', newVal]];
            }
            return newVal;
        }
        return clear();
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
     * Parses newVal for command(s) and executes them.
     *
     * @param {mail.model} record
     * @param {any} newVal
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    parseAndExecuteCommands(record, newVal, options) {
        if (newVal instanceof FieldCommand) {
            // single command given
            return newVal.execute(this, record, options);
        }
        if (newVal instanceof Array && newVal[0] instanceof FieldCommand) {
            // multi command given
            let hasChanged = false;
            for (const command of newVal) {
                if (command.execute(this, record, options)) {
                    hasChanged = true;
                }
            }
            return hasChanged;
        }
        // not a command
        return this.set(record, newVal, options);
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
     * @param {Object} [options]
     * @param {boolean} [options.hasToUpdateInverse] whether updating the
     *  current field should also update its inverse field. Only applies to
     *  relational fields. Typically set to false only during the process of
     *  updating the inverse field itself, to avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    set(record, newVal, options) {
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
                        if (this._setRelationCreate(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert':
                        if (this._setRelationInsert(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert-and-replace':
                        if (this._setRelationInsertAndReplace(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'link':
                        if (this._setRelationLink(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'replace':
                        if (this._setRelationReplace(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink':
                        if (this._setRelationUnlink(record, val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink-all':
                        if (this._setRelationUnlink(record, currentValue, options)) {
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
     * Converts given value to expected format for x2many processing, which is
     * an iterable of records.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [param1={}]
     * @param {boolean} [param1.hasToVerify=true] whether the value has to be
     *  verified @see `_verifyRelationalValue`
     * @returns {mail.model[]}
     */
    _convertX2ManyValue(newValue, { hasToVerify = true } = {}) {
        if (typeof newValue[Symbol.iterator] === 'function') {
            if (hasToVerify) {
                for (const value of newValue) {
                    this._verifyRelationalValue(value);
                }
            }
            return newValue;
        }
        if (hasToVerify) {
            this._verifyRelationalValue(newValue);
        }
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
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationCreate(record, data, options) {
        const OtherModel = this.env.models[this.to];
        const other = this.env.modelManager._create(OtherModel, data);
        return this._setRelationLink(record, other, options);
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
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsert(record, data, options) {
        const OtherModel = this.env.models[this.to];
        const other = this.env.modelManager._insert(OtherModel, data);
        return this._setRelationLink(record, other, options);
    }

    /**
     * Set on this relational field in 'insert-and-repalce' mode. Basically
     * data provided during set on this relational field contain data to insert
     * records, which themselves must replace value on this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsertAndReplace(record, data, options) {
        const OtherModel = this.env.models[this.to];
        const newValue = this.env.modelManager._insert(OtherModel, data);
        return this._setRelationReplace(record, newValue, options);
    }

    /**
     * Set a 'link' operation on this relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLink(record, newValue, options) {
        switch (this.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationLinkX2Many(record, newValue, options);
            case 'many2one':
            case 'one2one':
                return this._setRelationLinkX2One(record, newValue, options);
        }
    }

    /**
     * Handling of a `set` 'link' of a x2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [param2={}]
     * @param {boolean} [param2.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2Many(record, newValue, { hasToUpdateInverse = true } = {}) {
        const recordsToLink = this._convertX2ManyValue(newValue);
        const otherRecords = this.read(record);

        let hasChanged = false;
        for (const recordToLink of recordsToLink) {
            // other record already linked, avoid linking twice
            if (otherRecords.has(recordToLink)) {
                continue;
            }
            hasChanged = true;
            // link other records to current record
            otherRecords.add(recordToLink);
            // link current record to other records
            if (hasToUpdateInverse) {
                this.env.modelManager._update(
                    recordToLink,
                    { [this.inverse]: [['link', record]] },
                    { hasToUpdateInverse: false }
                );
            }
        }
        return hasChanged;
    }

    /**
     * Handling of a `set` 'link' of an x2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model} recordToLink
     * @param {Object} [param2={}]
     * @param {boolean} [param2.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2One(record, recordToLink, { hasToUpdateInverse = true } = {}) {
        this._verifyRelationalValue(recordToLink);
        const prevOtherRecord = this.read(record);
        // other record already linked, avoid linking twice
        if (prevOtherRecord === recordToLink) {
            return false;
        }
        // unlink to properly update previous inverse before linking new value
        this._setRelationUnlinkX2One(record, { hasToUpdateInverse });
        // link other record to current record
        record.__values[this.fieldName] = recordToLink;
        // link current record to other record
        if (hasToUpdateInverse) {
            this.env.modelManager._update(
                recordToLink,
                { [this.inverse]: [['link', record]] },
                { hasToUpdateInverse: false }
            );
        }
        return true;
    }

    /**
     * Set a 'replace' operation on this relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationReplace(record, newValue, options) {
        if (['one2one', 'many2one'].includes(this.relationType)) {
            // for x2one replace is just link
            return this._setRelationLinkX2One(record, newValue, options);
        }

        // for x2many: smart process to avoid unnecessary unlink/link
        let hasChanged = false;
        let hasToReorder = false;
        const otherRecordsSet = this.read(record);
        const otherRecordsList = [...otherRecordsSet];
        const recordsToReplaceList = [...this._convertX2ManyValue(newValue)];
        const recordsToReplaceSet = new Set(recordsToReplaceList);

        // records to link
        const recordsToLink = [];
        for (let i = 0; i < recordsToReplaceList.length; i++) {
            const recordToReplace = recordsToReplaceList[i];
            if (!otherRecordsSet.has(recordToReplace)) {
                recordsToLink.push(recordToReplace);
            }
            if (otherRecordsList[i] !== recordToReplace) {
                hasToReorder = true;
            }
        }
        if (this._setRelationLinkX2Many(record, recordsToLink, options)) {
            hasChanged = true;
        }

        // records to unlink
        const recordsToUnlink = [];
        for (let i = 0; i < otherRecordsList.length; i++) {
            const otherRecord = otherRecordsList[i];
            if (!recordsToReplaceSet.has(otherRecord)) {
                recordsToUnlink.push(otherRecord);
            }
            if (recordsToReplaceList[i] !== otherRecord) {
                hasToReorder = true;
            }
        }
        if (this._setRelationUnlinkX2Many(record, recordsToUnlink, options)) {
            hasChanged = true;
        }

        // reorder result
        if (hasToReorder) {
            otherRecordsSet.clear();
            for (const record of recordsToReplaceList) {
                otherRecordsSet.add(record);
            }
            hasChanged = true;
        }
        return hasChanged;
    }

    /**
     * Set an 'unlink' operation on this relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlink(record, newValue, options) {
        switch (this.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationUnlinkX2Many(record, newValue, options);
            case 'many2one':
            case 'one2one':
                return this._setRelationUnlinkX2One(record, options);
        }
    }

    /**
     * Handling of a `set` 'unlink' of a x2many relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [param2={}]
     * @param {boolean} [param2.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2Many(record, newValue, { hasToUpdateInverse = true } = {}) {
        const recordsToUnlink = this._convertX2ManyValue(
            newValue,
            { hasToVerify: false }
        );
        const otherRecords = this.read(record);

        let hasChanged = false;
        for (const recordToUnlink of recordsToUnlink) {
            // unlink other record from current record
            const wasLinked = otherRecords.delete(recordToUnlink);
            if (!wasLinked) {
                continue;
            }
            hasChanged = true;
            // unlink current record from other records
            if (hasToUpdateInverse) {
                if (!recordToUnlink.exists()) {
                    // This case should never happen ideally, but the current
                    // way of handling related relational fields make it so that
                    // deleted records are not always reflected immediately in
                    // these related fields.
                    continue;
                }
                // apply causality
                if (this.isCausal) {
                    this.env.modelManager._delete(recordToUnlink);
                } else {
                    this.env.modelManager._update(
                        recordToUnlink,
                        { [this.inverse]: [['unlink', record]] },
                        { hasToUpdateInverse: false }
                    );
                }
            }
        }
        return hasChanged;
    }

    /**
     * Handling of a `set` 'unlink' of a x2one relational field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object} [param1={}]
     * @param {boolean} [param1.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2One(record, { hasToUpdateInverse = true } = {}) {
        const otherRecord = this.read(record);
        // other record already unlinked, avoid useless processing
        if (!otherRecord) {
            return false;
        }
        // unlink other record from current record
        record.__values[this.fieldName] = undefined;
        // unlink current record from other record
        if (hasToUpdateInverse) {
            if (!otherRecord.exists()) {
                // This case should never happen ideally, but the current
                // way of handling related relational fields make it so that
                // deleted records are not always reflected immediately in
                // these related fields.
                return;
            }
            // apply causality
            if (this.isCausal) {
                this.env.modelManager._delete(otherRecord);
            } else {
                this.env.modelManager._update(
                    otherRecord,
                    { [this.inverse]: [['unlink', record]] },
                    { hasToUpdateInverse: false }
                );
            }
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
