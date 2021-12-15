/** @odoo-module **/

import { attr, one2many, one2one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';

registerModel({
    name: 'Guest',
    identifyingFields: ['id'],
    modelMethods: {
        /**
         * @param {Object} param0
         * @param {number} param0.id The id of the guest to rename.
         * @param {string} param0.name The new name to use to rename the guest.
         */
        async performRpcGuestUpdateName({ id, name }) {
            await this.env.services.rpc({
                route: '/mail/guest/update_name',
                params: {
                    guest_id: id,
                    name,
                },
            });
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            return `/web/image/mail.guest/${this.id}/avatar_128?unique=${this.name}`;
        },
    },
    fields: {
        authoredMessages: one2many('Message', {
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
        rtcSessions: one2many('RtcSession', {
            inverse: 'guest',
        }),
        volumeSetting: one2one('VolumeSetting', {
            inverse: 'guest',
        }),
    },
});
