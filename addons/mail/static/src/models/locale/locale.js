odoo.define('mail/static/src/models/locale/locale.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Locale extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeTextDirection() {
            return this.env._t.database.parameters.direction;
        }

    }

    Locale.fields = {
        textDirection: attr({
            compute: '_computeTextDirection',
        }),
    };

    Locale.modelName = 'mail.locale';

    return Locale;
}

registerNewModel('mail.locale', factory);

});
