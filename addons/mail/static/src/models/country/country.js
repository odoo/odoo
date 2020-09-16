odoo.define('mail/static/src/models/country/country.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Country extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

    }

    Country.fields = {
        __mfield_id: attr(),
        __mfield_name: attr(),
    };

    Country.modelName = 'mail.country';

    return Country;
}

registerNewModel('mail.country', factory);

});
