odoo.define('mail/static/src/models/country/country.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');
const { clear } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {

    class Country extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeFlagUrl() {
            if (!this.code) {
                return clear();
            }
            return `/base/static/img/country_flags/${this.code}.png`;
        }

    }

    Country.fields = {
        code: attr(),
        flagUrl: attr({
            compute: '_computeFlagUrl',
            dependencies: [
                'code',
            ],
        }),
        id: attr(),
        name: attr(),
    };

    Country.modelName = 'mail.country';

    return Country;
}

registerNewModel('mail.country', factory);

});
