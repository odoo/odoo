odoo.define('mail/static/src/models/Model', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { RecordDeletedError } = require('mail/static/src/model/model_errors.js');

/**
 * This function generates a class that represent a model. Instances of such
 * model (or inherited models) represent logical objects used in whole
 * application. They could represent server record (e.g. Thread, Message) or
 * UI elements (e.g. MessagingMenu, ChatWindow). These instances are called
 * "records", while the classes are called "models".
 */
function factory() {

    class Model {

        /**
         * @param {Object} [param0={}]
         * @param {boolean} [param0.valid=false] if set, this constructor is
         *   called by static method `create()`. This should always be the case.
         * @throws {Error} in case constructor is called in an invalid way, i.e.
         *   by instantiating the record manually with `new` instead of from
         *   static method `create()`.
         */
        constructor({ valid = false } = {}) {
            if (!valid) {
                throw new Error("Record must always be instantiated from static method 'create()'");
            }
        }

        /**
         * Called when the record is being created, but not yet processed
         * its create value on the fields. This method is handy to define purely
         * technical property on this record, like handling of timers. This
         * method acts like the constructor, but has a very important difference:
         * the `this` is the proxified record, so evaluation of field values
         * on get/set work correctly.
         */
        init() {}

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Returns all records of this model that match provided criteria.
         *
         * @static
         * @param {function} [filterFunc]
         * @returns {mail.model[]}
         */
        static all(filterFunc) {
            return this.env.modelManager.all(this, filterFunc);
        }

        /**
         * This method is used to create new records of this model
         * with provided data. This is the only way to create them:
         * instantiation must never been done with keyword `new` outside of this
         * function, otherwise the record will not be registered.
         *
         * @static
         * @param {Object} [data] data object with initial data, including relations.
         * @returns {mail.model} newly created record
         */
        static create(data) {
            return this.env.modelManager.create(this, data);
        }

        /**
         * Get the record that has provided criteria, if it exists.
         *
         * @static
         * @param {function} findFunc
         * @returns {mail.model|undefined}
         */
        static find(findFunc) {
            return this.env.modelManager.find(this, findFunc);
        }

        /**
         * This method returns the record of this model that matches provided
         * local id. Useful to convert a local id to a record. Note that even
         * if there's a record in the system having provided local id, if the
         * resulting record is not an instance of this model, this getter
         * assumes the record does not exist.
         *
         * @static
         * @param {string|mail.model|undefined} recordOrLocalId
         * @returns {mail.model|undefined}
         */
        static get(recordOrLocalId) {
            return this.env.modelManager.get(this, recordOrLocalId);
        }

        /**
         * This method creates a record or updates one, depending
         * on provided data.
         *
         * @static
         * @param {Object} data
         * @returns {mail.model} created or updated record.
         */
        static insert(data) {
            return this.env.modelManager.insert(this, data);
        }

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
                    if (this.constructor.get(this)) {
                        resolve(result);
                    } else {
                        reject(new RecordDeletedError(this.localId));
                    }
                }).catch(error => {
                    if (this.constructor.get(this)) {
                        reject(error);
                    } else {
                        reject(new RecordDeletedError(this.localId));
                    }
                });
            });
        }

        /**
         * This method deletes this record.
         */
        delete() {
            this.env.modelManager.delete(this);
        }

        /**
         * Update this record with provided data.
         *
         * @param {Object} [data={}]
         */
        update(data = {}) {
            this.env.modelManager.update(this, data);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @static
         * @private
         * @param {Object} data
         * @param {any} data.id
         * @return {function}
         */
        static _findFunctionFromData(data) {
            return record => record.id === data.id;
        }

        /**
         * This method generates a local id for this record that is
         * being created at the moment.
         *
         * This function helps customizing the local id to ease mapping a local
         * id to its record for the developer that reads the local id. For
         * instance, the local id of a thread cache could combine the thread
         * and stringified domain in its local id, which is much easier to
         * track relations and records in the system instead of arbitrary
         * number to differenciate them.
         *
         * @private
         * @param {Object} data
         * @returns {string}
         */
        _createRecordLocalId(data) {
            return _.uniqueId(`${this.constructor.modelName}_`);
        }

        /**
         * This function is called when this record has been explicitly updated
         * with `.update()` or static method `.create()`, at the end of an
         * record update cycle. This is a backward-compatible behaviour that
         * is deprecated: you should use computed fields instead.
         *
         * @deprecated
         * @abstract
         * @private
         * @param {Object} previous contains data that have been stored by
         *   `_updateBefore()`. Useful to make extra update decisions based on
         *   previous data.
         */
        _updateAfter(previous) {}

        /**
         * This function is called just at the beginning of an explicit update
         * on this function, with `.update()` or static method `.create()`. This
         * is useful to remember previous values of fields in `_updateAfter`.
         * This is a backward-compatible behaviour that is deprecated: you
         * should use computed fields instead.
         *
         * @deprecated
         * @abstract
         * @private
         * @param {Object} data
         * @returns {Object}
         */
        _updateBefore() {
            return {};
        }

    }

    /**
     * Models should define fields in static prop or getter `fields`.
     * It contains an object with name of field as key and value are objects
     * that define the field. There are some helpers to ease the making of these
     * objects, @see `mail/static/src/model/model_field.js`
     *
     * Note: fields of super-class are automatically inherited, therefore a
     * sub-class should (re-)define fields without copying ancestors' fields.
     */
    Model.fields = {};

    /**
     * Name of the model. Important to refer to appropriate model class
     * like in relational fields. Name of model classes must be unique.
     */
    Model.modelName = 'mail.model';

    return Model;
}

registerNewModel('mail.model', factory);

});
