/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Persona',
    identifyingMode: 'xor',
    fields: {
        channelMembers: many('ChannelMember', {
            inverse: 'persona',
            isCausal: true,
        }),
        guest: one('Guest', {
            identifying: true,
            inverse: 'persona',
        }),
        im_status: attr({
            compute() {
                if (this.guest) {
                    return this.guest.im_status || clear();
                }
                if (this.partner) {
                    return this.partner.im_status || clear();
                }
                return clear();
            },
        }),
        messagingAsAnyPersona: one('Messaging', {
            default: {},
            inverse: 'allPersonas',
        }),

        name: attr({
            compute() {
                if (this.guest) {
                    return this.guest.name || clear();
                }
                if (this.partner) {
                    return this.partner.nameOrDisplayName || clear();
                }
                return clear();
            },
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'persona',
        }),
        volumeSetting: one('res.users.settings.volumes', {
            compute() {
                if (this.guest) {
                    return this.guest.volumeSetting || clear();
                }
                if (this.partner) {
                    return this.partner.volumeSetting || clear();
                }
                return clear();
            },
        }),
    },
});
