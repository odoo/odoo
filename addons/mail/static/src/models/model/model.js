/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { RecordDeletedError } from '@mail/model/model_errors';
import { many2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

/**
 * The object below defines a model. Instances of such model (or inherited
 * models) represent logical objects used in whole application. They could
 * represent server record (e.g. Thread, Message) or UI elements (e.g.
 * MessagingMenu, ChatWindow). These instances are called "records".
 */
registerModel({
    /**
     * Name of the model. Important to refer to appropriate model like in
     * relational fields. Name of models must be unique.
     */
    name: 'Model',
     /**
     * Determines which fields are identifying fields for this model. Must be
     * overwritten in actual models. This should be a list of either field name
     * or sub-list of field name. Each top level element will be parsed as "and"
     * and each element of the same sub-list will be parsed as "or". If there
     * is no identifying fields, this model generates a singleton.
     */
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        /**
         * This function is called during the create cycle, when the record has
         * already been created, but its values have not yet been assigned.
         *
         * It is usually preferable to use @see `_created`.
         *
         * The main use case is to prepare the record for the assignation of its
         * values, for example if a computed field relies on the record to have
         * some purely technical property correctly set.
         *
         * @private
         */
        _willCreate() {},
        /**
         * This function is called after the record has been created, more
         * precisely at the end of the update cycle (which means all implicit
         * changes such as computes have been applied too).
         *
         * The main use case is to register listeners on the record.
         *
         * @private
         */
        _created() {},
        /**
         * This function is called when the record is about to be deleted. The
         * record still has all of its fields values accessible, but for all
         * intents and purposes the record should already be considered
         * deleted, which means update shouldn't be called inside this method.
         *
         * The main use case is to unregister listeners on the record.
         *
         * @private
         */
        _willDelete() {},
    },
    modelMethods: {
        /**
         * Returns all records of this model that match provided criteria.
         *
         * @param {function} [filterFunc]
         * @returns {Model[]}
         */
        all(filterFunc) {
            return this.modelManager.all(this, filterFunc);
        },
        /**
         * @deprecated use insert instead
         */
        create(data) {
            return this.modelManager.create(this, data);
        },
        /**
         * Get the record that has provided criteria, if it exists.
         *
         * @param {function} findFunc
         * @returns {Model|undefined}
         */
        find(findFunc) {
            return this.modelManager.find(this, findFunc);
        },
        /**
         * Gets the unique record that matches the given identifying data, if it
         * exists.
         *
         * @param {Object} data
         * @returns {Model|undefined}
         */
        findFromIdentifyingData(data) {
            return this.modelManager.findFromIdentifyingData(this, data);
        },
        /**
         * This method returns the record of this model that matches provided
         * local id. Useful to convert a local id to a record. Note that even
         * if there's a record in the system having provided local id, if the
         * resulting record is not an instance of this model, this getter
         * assumes the record does not exist.
         *
         * @param {string} localId
         * @param {Object} param1
         * @param {boolean} [param1.isCheckingInheritance]
         * @returns {Model|undefined}
         */
        get(localId, { isCheckingInheritance } = {}) {
            return this.modelManager.get(this, localId, { isCheckingInheritance });
        },
        /**
         * This method creates a record or updates one, depending on provided
         * data. This is the only way to create a record: instantiation must
         * never been done with keyword `new` outside of this function,
         * otherwise the record will not be registered correctly.
         *
         * @param {Object|Object[]} [data={}]
         *  If data is an iterable, multiple records will be created/updated.
         * @returns {Model|Model[]} created or updated record(s).
         */
        insert(data = {}) {
            return this.modelManager.insert(this, data);
        },
        /**
         * Returns a string representation of this model.
         *
         * @returns {string}
         */
        toString() {
            return `model(${this.name})`;
        },
    },
    modelGetters: {
        /**
         * Returns the current env.
         *
         * @returns {Object}
         */
        env() {
            return this.modelManager.env;
        },
        /**
         * Returns the messaging singleton.
         *
         * @returns {Messaging}
         */
        messaging() {
            return this.modelManager.messaging;
        },
        /**
         * Returns all existing models.
         *
         * @returns {Object} keys are model name, values are model class.
         */
        models() {
            return this.modelManager.models;
        },
    },
    recordMethods: {
        /**
         * Perform an async function and wait until it is done. If the record
         * is deleted, it raises a RecordDeletedError.
         *
         * @param {function} func an async function
         * @throws {RecordDeletedError} in case the current record is not alive
         *   at the end of async function call, whether it's resolved or
         *   rejected.
         * @throws {any} forwards any error in case the current record is still
         *   alive at the end of rejected async function call.
         * @returns {any} result of resolved async function.
         */
        async async(func) {
            return new Promise((resolve, reject) => {
                Promise.resolve(func()).then(result => {
                    if (this.exists()) {
                        resolve(result);
                    } else {
                        reject(new RecordDeletedError(this.localId));
                    }
                }).catch(error => {
                    if (this.exists()) {
                        reject(error);
                    } else {
                        reject(new RecordDeletedError(this.localId));
                    }
                });
            });
        },
        /**
         * This method deletes this record.
         */
        delete() {
            this.modelManager.delete(this);
        },
        /**
         * Returns whether the current record exists.
         *
         * @returns {boolean}
         */
        exists() {
            return this.modelManager.exists(this.constructor, this);
        },
        /**
         * Returns a string representation of this record.
         */
        toString() {
            return `record(${this.localId})`;
        },
        /**
         * Update this record with provided data.
         *
         * @param {Object} [data={}]
         */
        update(data = {}) {
            this.modelManager.update(this, data);
        },
    },
    recordGetters: {
        /**
         * Returns the current env.
         *
         * @returns {Object}
         */
        env() {
            return this.modelManager.env;
        },
        /**
         * Returns the model manager.
         *
         * @returns {ModelManager}
         */
        modelManager() {
            return this.constructor.modelManager;
        },
        /**
         * Returns all existing models.
         *
         * @returns {Object} keys are model name, values are model class.
         */
        models() {
            return this.modelManager.models;
        },
    },
    /**
     * Models should define fields in static prop or getter `fields`.
     * It contains an object with name of field as key and value are objects
     * that define the field. There are some helpers to ease the making of these
     * objects, @see `mail/static/src/model/model_field.js`
     *
     * Note: fields of super-class are automatically inherited, therefore a
     * sub-class should (re-)define fields without copying ancestors' fields.
     */
    fields: {
        /**
         * States the messaging singleton. Automatically assigned by the model
         * manager at creation.
         */
        messaging: many2one('Messaging', {
            default: insertAndReplace(),
            inverse: 'allRecords',
            readonly: true,
            required: true,
        }),
    },
});
