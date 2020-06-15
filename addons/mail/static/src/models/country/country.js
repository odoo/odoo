odoo.define('mail/static/src/models/country/country.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Country extends dependencies['mail.model'] {}

    Country.fields = {
        id: attr(),
        name: attr(),
    };

    Country.modelName = 'mail.country';

    return Country;
}

registerNewModel('mail.country', factory);

});
