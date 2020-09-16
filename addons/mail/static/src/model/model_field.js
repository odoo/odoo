odoo.define('mail/static/src/model/model_field_definition.js', function (require) {
'use strict';

const { FieldCommand } = require('mail/static/src/model/model_field_command.js');

/**
 * Class whose instances represent field on a model.
 * These field definitions are generated from declared fields in static prop
 * `fields` on the model.
 */
class ModelField {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    constructor(env, { definition, record }) {
        this.def = definition;
        this.env = env;
        this.id = _.uniqueId('Field_');
        this.record = record;
        this._rawVal = undefined;

        if (this.def.fieldType === 'relation') {
            if (['one2many', 'many2many'].includes(this.def.relationType)) {
                this._rawVal = new Set();
            }
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Clears the value of this field on the given record. It consists of
     * setting this to its default value. In particular, using `clear` is the
     * only way to write `undefined` on a field, as long as `undefined` is its
     * default value. Relational fields are always unlinked before the default
     * is applied.
     *
     * @param {options} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    clear(options) {
        let hasChanged = false;
        if (this.def.fieldType === 'relation') {
            if (this.parseAndExecuteCommands([['unlink-all']], options)) {
                hasChanged = true;
            }
        }
        if (this.parseAndExecuteCommands(this.def.default, options)) {
            hasChanged = true;
        }
        return hasChanged;
    }

    /**
     * Parses newVal for command(s) and executes them.
     *
     * @param {any} newVal
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    parseAndExecuteCommands(newVal, options) {
        if (newVal instanceof FieldCommand) {
            // single command given
            return newVal.execute(this, options);
        }
        if (typeof newVal instanceof Array && newVal[0] instanceof FieldCommand) {
            // multi command given
            let hasChanged = false;
            for (const command of newVal) {
                if (command.execute(this, options)) {
                    hasChanged = true;
                }
            }
            return hasChanged;
        }
        // not a command
        return this.set(newVal, options);
    }

    /**
     * Get the raw value associated to this field. For relations, this means
     * the local id or list of local ids of records in this relational field.
     *
     * @returns {any}
     */
    read() {
        return this.__rawVal;
    }

    /**
     * Set a value on this field. The format of the value comes from business
     * code.
     *
     * @param {any} newVal
     * @param {Object} [options]
     * @param {boolean} [options.hasToUpdateInverse] whether updating the
     *  current field should also update its inverse field. Only applies to
     *  relational fields. Typically set to false only during the process of
     *  updating the inverse field itself, to avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    set(newVal, options) {
        const currentValue = this.read();
        if (this.def.fieldType === 'attribute') {
            if (currentValue === newVal) {
                return false;
            }
            this.__RawVal = newVal;
            return true;
        }
        if (this.def.fieldType === 'relation') {
            let hasChanged = false;
            for (const val of newVal) {
                switch (val[0]) {
                    case 'create':
                        if (this._setRelationCreate(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert':
                        if (this._setRelationInsert(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'insert-and-replace':
                        if (this._setRelationInsertAndReplace(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'link':
                        if (this._setRelationLink(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'replace':
                        // TODO IMP replace should not unlink-all (task-2270780)
                        if (this._setRelationUnlink(currentValue, options)) {
                            hasChanged = true;
                        }
                        if (this._setRelationLink(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink':
                        if (this._setRelationUnlink(val[1], options)) {
                            hasChanged = true;
                        }
                        break;
                    case 'unlink-all':
                        if (this._setRelationUnlink(currentValue, options)) {
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
     * @param {Object|Object[]} data
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationCreate(data, options) {
        const OtherModel = this.env.models[this.def.to];
        const other = this.env.modelManager._create(OtherModel, data);
        return this._setRelationLink(other, options);
    }

    /**
     * Set on this relational field in 'insert' mode. Basically data provided
     * during set on this relational field contain data to insert records,
     * which themselves must be linked to record of this field by means of
     * this field.
     *
     * @private
     * @param {Object|Object[]} data
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsert(data, options) {
        const OtherModel = this.env.models[this.def.to];
        const other = this.env.modelManager._insert(OtherModel, data);
        return this._setRelationLink(other, options);
    }

    /**
     * Set on this relational field in 'insert-and-repalce' mode. Basically
     * data provided during set on this relational field contain data to insert
     * records, which themselves must replace value on this field.
     *
     * @private
     * @param {Object|Object[]} data
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationInsertAndReplace(data, options) {
        // unlink must be done before insert:
        // because unlink might trigger delete due to causality and new data
        // shouldn't be deleted just after being inserted
        // TODO IMP insert-and-replace should not unlink-all (task-2270780)
        let hasChanged = false;
        if (this._setRelationUnlink(this.read(), options)) {
            hasChanged = true;
        }
        const OtherModel = this.env.models[this.def.to];
        const other = this.env.modelManager._insert(OtherModel, data);
        if (this._setRelationLink(other, options)) {
            hasChanged = true;
        }
        return hasChanged;
    }

    /**
     * Set a 'link' operation on this relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLink(newValue, options) {
        switch (this.def.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationLinkX2Many(newValue, options);
            case 'many2one':
            case 'one2one':
                return this._setRelationLinkX2One(newValue, options);
        }
    }

    /**
     * Handling of a `set` 'link' of a x2many relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [param1={}]
     * @param {boolean} [param1.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2Many(newValue, { hasToUpdateInverse = true } = {}) {
        const recordsToLink = this._convertX2ManyValue(newValue);
        const otherRecords = this.read();

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
                    { [this.def.inverse]: [['link', this.record]] },
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
     * @param {mail.model} recordToLink
     * @param {Object} [param1={}]
     * @param {boolean} [param1.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationLinkX2One(recordToLink, { hasToUpdateInverse = true } = {}) {
        this._verifyRelationalValue(recordToLink);
        const prevOtherRecord = this.read();
        // other record already linked, avoid linking twice
        if (prevOtherRecord === recordToLink) {
            return false;
        }
        // unlink to properly update previous inverse before linking new value
        this._setRelationUnlinkX2One({ hasToUpdateInverse });
        // link other record to current record
        this._rawVal = recordToLink;
        // link current record to other record
        if (hasToUpdateInverse) {
            this.env.modelManager._update(
                recordToLink,
                { [this.def.inverse]: [['link', this.record]] },
                { hasToUpdateInverse: false }
            );
        }
        return true;
    }

    /**
     * Set an 'unlink' operation on this relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlink(newValue, options) {
        switch (this.def.relationType) {
            case 'many2many':
            case 'one2many':
                return this._setRelationUnlinkX2Many(newValue, options);
            case 'many2one':
            case 'one2one':
                return this._setRelationUnlinkX2One(options);
        }
    }

    /**
     * Handling of a `set` 'unlink' of a x2many relational field.
     *
     * @private
     * @param {mail.model|mail.model[]} newValue
     * @param {Object} [param1={}]
     * @param {boolean} [param1.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2Many(newValue, { hasToUpdateInverse = true } = {}) {
        const recordsToUnlink = this._convertX2ManyValue(
            newValue,
            { hasToVerify: false }
        );
        const otherRecords = this.read();

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
                this.env.modelManager._update(
                    recordToUnlink,
                    { [this.def.inverse]: [['unlink', this.record]] },
                    { hasToUpdateInverse: false }
                );
                // apply causality
                if (this.def.isCausal) {
                    this.env.modelManager._delete(recordToUnlink);
                }
            }
        }
        return hasChanged;
    }

    /**
     * Handling of a `set` 'unlink' of a x2one relational field.
     *
     * @private
     * @param {Object} [param0={}]
     * @param {boolean} [param0.hasToUpdateInverse=true] whether updating the
     *  current field should also update its inverse field. Typically set to
     *  false only during the process of updating the inverse field itself, to
     *  avoid unnecessary recursion.
     * @returns {boolean} whether the value changed for the current field
     */
    _setRelationUnlinkX2One({ hasToUpdateInverse = true } = {}) {
        const otherRecord = this.read();
        // other record already unlinked, avoid useless processing
        if (!otherRecord) {
            return false;
        }
        // unlink other record from current record
        this._rawVal = undefined;
        // unlink current record from other record
        if (hasToUpdateInverse) {
            if (!otherRecord.exists()) {
                // This case should never happen ideally, but the current
                // way of handling related relational fields make it so that
                // deleted records are not always reflected immediately in
                // these related fields.
                return;
            }
            this.env.modelManager._update(
                otherRecord,
                { [this.def.inverse]: [['unlink', this.record]] },
                { hasToUpdateInverse: false }
            );
            // apply causality
            if (this.def.isCausal) {
                this.env.modelManager._delete(otherRecord);
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
     * @throws {Error} if record does not satisfy related model
     */
    _verifyRelationalValue(record) {
        const OtherModel = this.env.models[this.def.to];
        if (!OtherModel.get(record.localId, { isCheckingInheritance: true })) {
            throw Error(`Record ${record.localId} is not valid for relational field ${this.def.fieldName}.`);
        }
    }

}

return ModelField;

});
