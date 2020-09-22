odoo.define('mail/static/src/model/model_field_command.js', function (require) {
'use strict';

/**
 * Allows field update to detect if the value it received is a command to
 * execute (in which was it will be an instance of this class) or an actual
 * value to set (in all other cases).
 */
class FieldCommand {
    /**
     * @constructor
     * @param {function} func function to call when executing this command
     */
    constructor(func) {
        this.func = func;
    }

    /**
     * @param {ModelField} field
     * @param {mail.model} record
     * @param {options} [options]
     * @returns {boolean} whether the value changed for the current field
     */
    execute(field, record, options) {
        return this.func(field, record, options);
    }
}

/**
 * Returns a clear command to give to the model manager at create/update.
 */
function clear() {
    return new FieldCommand((field, record, options) =>
        field.clear(record, options)
    );
}

return {
    // class
    FieldCommand,
    // shortcuts
    clear,
};

});
