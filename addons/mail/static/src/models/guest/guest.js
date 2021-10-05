/** @odoo-module **/

import { attr, one2many } from '@mail/model/model_field';
import { registerNewModel } from '@mail/model/model_core';

function factory(dependencies) {

    class Guest extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} param0
         * @param {number} param0.id The id of the guest to rename.
         * @param {string} param0.name The new name to use to rename the guest.
         */
        static async performRpcGuestUpdateName({ id, name }) {
            await this.env.services.rpc({
                route: '/mail/guest/update_name',
                params: {
                    guest_id: id,
                    name,
                },
            });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            return `/web/image/mail.guest/${this.id}/avatar_128?unique=${this.name}`;
        }

    }

    Guest.fields = {
        authoredMessages: one2many('mail.message', {
            inverse: 'guestAuthor',
        }),
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
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
