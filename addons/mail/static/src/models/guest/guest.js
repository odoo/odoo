/** @odoo-module **/

import { attr, one2many } from '@mail/model/model_field';
import { registerNewModel } from '@mail/model/model_core';

function factory(dependencies) {

    class Guest extends dependencies['mail.model'] {

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            return `/web/image/mail.guest/${this.id}/avatar_128`;
        }

    }

    Guest.fields = {
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        authoredMessages: one2many('mail.message', {
            inverse: 'guestAuthor',
        }),
        id: attr({
            required: true,
            readonly: true,
        }),
        name: attr(),
    };
    Guest.identifyingFields = ['id'];
    Guest.modelName = 'mail.guest';

    return Guest;
}

registerNewModel('mail.guest', factory);
