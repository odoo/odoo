/** @odoo-module **/

/**
 * Allows field update to detect if the value it received is a command to
 * execute (in which was it will be an instance of this class) or an actual
 * value to set (in all other cases).
 */
class FieldCommand {
    /**
     * @constructor
     * @param {string} name - command name.
     * @param {any} [value] - value(s) used for the command.
     */
    constructor(name, value) {
        this._name = name;
        this._value = value;
    }

    /**
     * @returns {string} name/behavior of the command.
     */
    get name() {
        return this._name;
    }

    /**
     * @returns {any} value used for the command to update the field
     */
    get value() {
        return this._value;
    }
}

/**
 * Returns a clear command to give to the model manager at create/update.
 * `clear` command can be used for attribute fields or relation fields.
 * - Set an attribute field its default value (or undefined if no default value is given);
 * - or unlink the current record(s) and then set the default value for a relation field;
 *
 * @returns {FieldCommand}
 */
function clear() {
    return new FieldCommand('clear');
}

/**
 * Returns a create command to give to the model manager at create/update.
 * `create` command can be used for relation fields.
 * - Create new record(s) from data and then link it for a relation field;
 *
 * @param {Object|Object[]} data - data object or data objects array to create record(s).
 * @returns {FieldCommand}
 */
function create(data) {
    return new FieldCommand('create', data);
}

/**
 * Returns a decrement command to give to the model manager at create/update.
 * `decrement` command can be used for attribute fields (number typed).
 * The field value will be decreased by `amount`.
 *
 * @param {number} [amount=1]
 * @returns {FieldCommand}
 */
function decrement(amount = 1) {
    return new FieldCommand('decrement', amount);
}

/**
 * Returns a increment command to give to the model manager at create/update.
 * `increment` command can be used for attribute fields (number typed).
 * The field value will be increased by `amount`.
 *
 * @param {number} [amount=1]
 * @returns {FieldCommand}
 */
function increment(amount = 1) {
    return new FieldCommand('increment', amount);
}

/**
 * Returns a insert command to give to the model manager at create/update.
 * `insert` command can be used for relation fields.
 * - Create new record(s) from data if the record(s) do not exist;
 * - or update the record(s) if they can be found from identifying data;
 * - and then link record(s) to a relation field.
 *
 * @param {Object|Object[]} data - data object or data objects array to insert record(s).
 * @returns {FieldCommand}
 */
function insert(data) {
    return new FieldCommand('insert', data);
}

/**
 * Returns a insert-and-unlink command to give to the model manager at create/update.
 * `insertAndUnlink` command can be used for relation fields.
 * - Create new record(s) from data if the record(s) do not exist;
 * - or update the record(s) if they can be found from identifying data;
 * - and then unlink the record(s) from the relation field (if they were present).
 *
 * @param {Object|Object[]} [data={}] - data object or data objects array to insert and unlink record(s).
 * @returns {FieldCommand}
 */
export function insertAndUnlink(data = {}) {
    return new FieldCommand('insert-and-unlink', data);
}

/**
 * Returns a link command to give to the model manager at create/update.
 * `link` command can be used for relation fields.
 * - Set the field value `newValue` if current field value differs from `newValue` for an x2one field;
 * - Or add the record(s) given by `newValue` which are not in the currecnt field value
 * to the field value for an x2many field.
 *
 * @param {Record|Record[]} newValue - record or records array to be linked.
 * @returns {FieldCommand}
 */
function link(newValue) {
    return new FieldCommand('link', newValue);
}

/**
 * Returns a set command to give to the model manager at create/update.
 * `set` command can be used for attribute fields.
 * - Write the `newValue` on the field value.
 *
 * @param {any} newValue - value to be written on the field value.
 */
function set(newValue) {
    return new FieldCommand('set', newValue);
}

/**
 * Returns a unlink command to give to the model manager at create/update.
 * `unlink` command can be used for relation fields.
 * - Remove the current value for a x2one field
 * - or remove the record(s) given by `data` which are in the current field value
 *  for a x2many field.
 *
 * @param {Record|Record[]} [data] - record or records array to be unlinked.
 * `data` will be ignored if the field is x2one type.
 * @returns {FieldCommand}
 */
function unlink(data) {
    return new FieldCommand('unlink', data);
}

/**
 * Returns a unlink-all command to give to the model manager at create/update.
 * `unlinkAll` command can be used for relation fields.
 * - remove all record(s) for a relation field
 *
 * @returns {FieldCommand}
 */
function unlinkAll() {
    return new FieldCommand('unlink-all');
}

export {
    FieldCommand,
    clear,
    create,
    decrement,
    increment,
    insert,
    link,
    set,
    unlink,
    unlinkAll,
};
