odoo.define('mail/static/src/models/canned_response/canned_response.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class CannedResponse extends dependencies['mail.model'] {}

    CannedResponse.fields = {
        description: attr(),
        id: attr(),
        source: attr(),
        substitution: attr(),
    };

    CannedResponse.modelName = 'mail.canned_response';

    return CannedResponse;
}

registerNewModel('mail.canned_response', factory);

});
