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
            this._write(data);
        }

    }

    Object.assign(MailFailure, {
        relations: Object.assign({}, Entity.relations, {}),
    });

    return MailFailure;
}

registerNewEntity('MailFailure', MailFailureFactory);

});
