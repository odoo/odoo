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
         * This function is called during the create cycle, when the record has
         * already been created, but its values have not yet been assigned.
         *
         * It is usually preferable to override @see `_created`.
         *
         * The main use case is to prepare the record for the assignation of its
         * values, for example if a computed field relies on the record to have
         * some purely technical property correctly set.
         *
         * @abstract
         * @private
         */
        _willCreate() {}

        /**
         * This function is called after the record has been created, more
         * precisely at the end of the update cycle (which means all implicit
         * changes such as computes have been applied too).
         *
         * The main use case is to register listeners on the record.
         *
         * @abstract
         * @private
         */
        _created() {}

        /**
         * This function is called when the record is about to be deleted. The
         * record still has all of its fields values accessible, but for all
         * intents and purposes the record should already be considered
         * deleted, which means update shouldn't be called inside this method.
         *
         * The main use case is to unregister listeners on the record.
         *
         * @abstract
         * @private
         */
        _willDelete() {}

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
         * @param {Object|Object[]} [data] data object with initial data, including relations.
         *  If data is an iterable, multiple records will be created.
         * @returns {mail.model|mail.model[]} newly created record(s)
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
         * Gets the unique record that matches the given identifying data, if it
         * exists.
         * @see `_createRecordLocalId` for criteria of identification.
         *
         * @static
         * @param {Object} data
         * @returns {mail.model|undefined}
         */
        static findFromIdentifyingData(data) {
            return this.env.modelManager.findFromIdentifyingData(this, data);
        }

        /**
         * This method returns the record of this model that matches provided
         * local id. Useful to convert a local id to a record. Note that even
         * if there's a record in the system having provided local id, if the
         * resulting record is not an instance of this model, this getter
         * assumes the record does not exist.
         *
         * @static
         * @param {string} localId
         * @param {Object} param1
         * @param {boolean} [param1.isCheckingInheritance]
         * @returns {mail.model|undefined}
         */
        static get(localId, { isCheckingInheritance } = {}) {
            return this.env.modelManager.get(this, localId, { isCheckingInheritance });
        }

        /**
         * This method creates a record or updates one, depending
         * on provided data.
         *
         * @static
         * @param {Object|Object[]} data
         *  If data is an iterable, multiple records will be created/updated.
         * @returns {mail.model|mail.model[]} created or updated record(s).
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
        }

        /**
         * This method deletes this record.
         */
        delete() {
            this.env.modelManager.delete(this);
        }

        /**
         * Returns whether the current record exists.
         *
         * @returns {boolean}
         */
        exists() {
            return this.env.modelManager.exists(this.constructor, this);
        }

        /**
         * Update this record with provided data.
         *
         * @param {Object} [data={}]
         */
        update(data = {}) {
            this.env.modelManager.update(this, data);
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
         * @static
         * @private
         * @param {Object} data
         * @returns {string}
         */
        static _createRecordLocalId(data) {
            return _.uniqueId(`${this.modelName}_`);
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
