/** @odoo-module **/

import { clear, FieldCommand, link, replace, unlink, unlinkAll } from '@mail/model/model_field_command';

/**
 * Class whose instances represent field on a model.
 * These field definitions are generated from declared fields in static prop
 * `fields` on the model.
 */
export class ModelField {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    constructor({
        compute,
        default: def,
        fieldName,
        fieldType,
        inverse,
        isCausal = false,
        readonly = false,
        related,
        relationType,
        required = false,
        to,
    } = {}) {
        /**
         * If set, this field acts as a computed field, and this prop
         * contains the name of the instance method that computes the value
         * for this field. This compute method is called on creation of record
         * and whenever some of its dependencies change.
         */
        this.compute = compute;
        /**
         * Default value for this field. Used on creation of this field, to
         * set a value by default.
         */
        this.default = def;
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
         * Determines whether the field is read only. Read only field
         * can't be updated once the record is created.
         * An exception is made for computed fields (updated when the
         * dependencies are updated) and related fields (updated when the
         * inverse relation changes).
         */
        this.readonly = readonly;
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
         * Determine whether the field is required or not.
         *
         * Empty value is systematically undefined.
         * null or empty string are NOT considered empty value, meaning these values meet the requirement.
        */
        this.required = required;
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
            if (this.parseAndExecuteCommands(record, unlinkAll(), options)) {
                hasChanged = true;
            }
            if (!this.default) {
                return hasChanged;
            }
        }
        if (this.parseAndExecuteCommands(record, this.default, options)) {
            hasChanged = true;
        }
        return hasChanged;
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
                const otherValue = otherRecord[relatedFieldName];
                if (otherValue) {
                    if (otherValue instanceof Array) {
                        for (const v of otherValue) {
                            newVal.push(v);
                        }
                    } else {
                        newVal.push(otherValue);
                    }
                }
            }
            if (this.fieldType === 'relation') {
                return replace(newVal);
            }
            return newVal;
        }
        const otherRecord = record[relationName];
        if (otherRecord) {
            const newVal = otherRecord[relatedFieldName];
            if (newVal === undefined) {
                return clear();
            }
            if (this.fieldType === 'relation') {
                return replace(newVal);
            }
            return newVal;
        }
        return clear();
    }

    /**
     * Converts the given value to a list of FieldCommands
     *
     * @param {*} newVal
     * @returns {FieldCommand[]}
     */
    convertToFieldCommandList(newVal) {
        if (newVal instanceof FieldCommand) {
            return [newVal];
        } else if (newVal instanceof Array && newVal[0] instanceof FieldCommand) {
            return newVal;
        } else if (this.fieldType === 'relation') {
            // Deprecated. Used only to support old syntax: `[...[name, value]]` command
            return newVal.map(([name, value]) => new FieldCommand(name, value));
        } else {
            return [new FieldCommand('set', newVal)];
        }
    }

    /**
     * Decreases the field value by `amount`
     * for an attribute field holding number value,
     *
     * @param {mail.model} record
     * @param {number} amount
     */
    decrement(record, amount) {
        const currentValue = this.read(record);
        return this._setAttribute(record, currentValue - amount);
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
     * Increases the field value by `amount`
     * for an attribute field holding number value.
     *
     * @param {mail.model} record
     * @param {number} amount
     */
    increment(record, amount) {
        const currentValue = this.read(record);
        return this._setAttribute(record, currentValue + amount);
    }

    /**
     * Parses newVal for command(s) and executes them.
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
    parseAndExecuteCommands(record, newVal, options) {
        const commandList = this.convertToFieldCommandList(newVal);
        let hasChanged = false;
        for (const command of commandList) {
            const commandName = command.name;
            const newVal = command.value;
            if (this.fieldType === 'attribute') {
                switch (commandName) {
                    case 'clear':
                        if (this.clear(record, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'decrement':
                        if (this.decrement(record, newVal)) {
                            hasChanged = true;
                        }
                        break;
                    case 'increment':
                        if (this.increment(record, newVal)) {
                            hasChanged = true;
                        }
                        break;
                    case 'set':
                        if (this._setAttribute(record, newVal)) {
                            hasChanged = true;
                        }
                        break;
                    default:
                        throw new Error(`Field "${record.constructor.modelName}/${this.fieldName}"(${this.fieldType} type) does not support command "${commandName}"`);
                }
            } else if (this.fieldType === 'relation') {
                switch (commandName) {
                    case 'clear':
                        if (this.clear(record, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert':
                        if (this._setRelationInsert(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert-and-replace':
                        if (this._setRelationInsertAndReplace(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert-and-unlink':
                        if (this._setRelationInsertAndUnlink(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'link':
                        if (this._setRelationLink(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'replace':
                        if (this._setRelationReplace(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink':
                        if (this._setRelationUnlink(record, newVal, options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink-all':
                        if (this._setRelationUnlink(record, this.read(record), options)) {
                            hasChanged = true;
                        }
                        break;
                    default:
                        throw new Error(`Field "${record.constructor.modelName}/${this.fieldName}"(${this.fieldType} type) does not support command "${commandName}"`);
                }
            }
        }
        return hasChanged;
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
     * @returns {string}
     */
    toString() {
        return `field(${this.fieldName})`;
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
     * Creates or updates and then returns the other record(s) of a relational
     * field based on the given data and the inverse relation value.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     * @returns {mail.model|mail.model[]}
     */
    _insertOtherRecord(record, data) {
        const OtherModel = record.models[this.to];
        const isMulti = typeof data[Symbol.iterator] === 'function';
        const dataList = [];
        for (const recordData of (isMulti ? data : [data])) {
            const recordData2 = { ...recordData };
            if (['one2one', 'one2many'].includes(this.relationType)) {
                recordData2[this.inverse] = replace(record);
            } else {
                recordData2[this.inverse] = link(record);
            }
            dataList.push(recordData2);
        }
        const records = record.modelManager._insert(OtherModel, dataList);
        return isMulti ? records : records[0];
    }

    /**
     *  Set a value for this attribute field
     *
     * @private
     * @param {mail.model} record
     * @param {any} newVal value to be written on the field value.
     * @returns {boolean} whether the value changed for the current field
     */
    _setAttribute(record, newVal) {
        const currentValue = this.read(record);
        if (currentValue === newVal) {
            return false;
        }
        record.__values[this.fieldName] = newVal;
        return true;
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
        const newValue = this._insertOtherRecord(record, data);
        return this._setRelationLink(record, newValue, options);
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
        const newValue = this._insertOtherRecord(record, data);
        return this._setRelationReplace(record, newValue, options);
    }

    /**
     * Set on this relational field in 'insert-and-unlink' mode. Basically
     * data provided during set on this relational field contain data to insert
     * records, which themselves must be unlinked from this field.
     *
     * @private
     * @param {mail.model} record
     * @param {Object|Object[]} data
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsertAndUnlink(record, data, options) {
        const newValue = this._insertOtherRecord(record, data);
        return this._setRelationUnlink(record, newValue, options);
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
                record.modelManager._update(
                    recordToLink,
                    { [this.inverse]: link(record) },
                    { allowWriteReadonly: true, hasToUpdateInverse: false }
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
        this._setRelationUnlinkX2One(record, { hasToUpdateInverse: true });
        // link other record to current record
        record.__values[this.fieldName] = recordToLink;
        // link current record to other record
        if (hasToUpdateInverse) {
            record.modelManager._update(
                recordToLink,
                { [this.inverse]: link(record) },
                { allowWriteReadonly: true, hasToUpdateInverse: false }
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
                    record.modelManager._delete(recordToUnlink);
                } else {
                    record.modelManager._update(
                        recordToUnlink,
                        { [this.inverse]: unlink(record) },
                        { allowWriteReadonly: true, hasToUpdateInverse: false }
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
                record.modelManager._delete(otherRecord);
            } else {
                record.modelManager._update(
                    otherRecord,
                    { [this.inverse]: unlink(record) },
                    { allowWriteReadonly: true, hasToUpdateInverse: false }
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
        if (!record) {
            throw Error(`record is undefined. Did you try to link() or insert() empty value? Considering clear() instead.`);
        }
        if (!record.modelManager) {
            throw Error(`${record} is not a record. Did you try to use link() instead of insert() with data?`);
        }
        const OtherModel = record.modelManager.models[this.to];
        if (!OtherModel.get(record.localId, { isCheckingInheritance: true })) {
            throw Error(`Record ${record.localId} is not valid for relational field ${this.fieldName}.`);
        }
    }

}

export const attr = ModelField.attr;
export const many2many = ModelField.many2many;
export const many2one = ModelField.many2one;
export const one2many = ModelField.one2many;
export const one2one = ModelField.one2one;
