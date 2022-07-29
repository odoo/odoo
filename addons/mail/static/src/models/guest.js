/** @odoo-module **/

import { attr, many, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';

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
            await this.messaging.rpc({
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
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsOnline() {
            return ['online', 'away'].includes(this.im_status);
        },
    },
    fields: {
        authoredMessages: many('Message', {
            inverse: 'guestAuthor',
        }),
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        id: attr({
            required: true,
            readonly: true,
        }),
        im_status: attr(),
        isOnline: attr({
            compute: '_computeIsOnline',
        }),
        name: attr(),
        persona: one('Persona', {
            default: insertAndReplace(),
            inverse: 'guest',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        volumeSetting: one('res.users.settings.volumes', {
            inverse: 'guest_id',
        }),
    },
});
