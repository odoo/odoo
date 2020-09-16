odoo.define('mail/static/src/models/canned_response/canned_response.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class CannedResponse extends dependencies['mail.model'] {}

    CannedResponse.fields = {
        __mfield_id: attr(),
        /**
         *  The keyword to use a specific canned response.
         */
        __mfield_source: attr(),
        /**
         * The canned response itself which will replace the keyword previously
         * entered.
         */
        __mfield_substitution: attr(),
    };

    CannedResponse.modelName = 'mail.canned_response';

    return CannedResponse;
}

registerNewModel('mail.canned_response', factory);

});
