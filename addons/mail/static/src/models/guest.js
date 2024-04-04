/** @odoo-module **/

import { attr, many, one } from '@mail/model/model_field';
import { registerModel } from '@mail/model/model_core';

registerModel({
    name: 'Guest',
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
    fields: {
        authoredMessages: many('Message', {
            inverse: 'guestAuthor',
        }),
        avatarUrl: attr({
            compute() {
                return `/web/image/mail.guest/${this.id}/avatar_128?unique=${this.name}`;
            },
        }),
        id: attr({
            identifying: true,
        }),
        im_status: attr(),
        isOnline: attr({
            compute() {
                return ['online', 'away'].includes(this.im_status);
            },
        }),
        name: attr(),
        persona: one('Persona', {
            default: {},
            inverse: 'guest',
            readonly: true,
            required: true,
        }),
        volumeSetting: one('res.users.settings.volumes', {
            inverse: 'guest_id',
        }),
    },
});
