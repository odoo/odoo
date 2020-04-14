odoo.define('mail.messaging.entity.MailFailure', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function MailFailureFactory({ Entity }) {

    class MailFailure extends Entity {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            Object.assign(this, data);
        }

    }

    Object.assign(MailFailure, {
        fields: Object.assign({}, Entity.fields, {}),
    });

    return MailFailure;
}

registerNewEntity('MailFailure', MailFailureFactory);

});
