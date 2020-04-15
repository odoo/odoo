odoo.define('mail.messaging.entity.Locale', function (require) {
'use strict';

const {
    fields: {
        one2one,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function LocaleFactory({ Entity }) {

    class Locale extends Entity {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @returns {string}
         */
        get textDirection() {
            return this.env._t.database.parameters.direction;
        }

    }

    Locale.fields = {};

    return Locale;
}

registerNewEntity('Locale', LocaleFactory);

});
