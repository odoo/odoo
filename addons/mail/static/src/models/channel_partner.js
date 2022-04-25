/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ChannelPartner',
    identifyingFields: ['channel', ['partner', 'guest']],
    recordMethods: {
        /**
         * Handles click on the avatar of the given member in the member list of
         * this channel.
         */
        onClickAvatar() {
            if (!this.partner) {
                return;
            }
            this.partner.openChat();
        },
        /**
         * Handles click on the name of the given member in the member list of
         * this channel.
         */
        onClickName() {
            if (!this.partner) {
                return;
            }
            this.partner.openProfile();
        },
        _computeId() {
            return this.partner ? this.partner.id : this.guest.id;
        },
        _computeName() {
            return this.partner ? this.partner.nameOrDisplayName : this.guest.name;
        },
    },
    fields: {
        channel: one('Channel', {
            inverse: 'channelPartners',
            required: true,
            readonly: true,
        }),
        guest: one('Guest', {
            inverse: 'channelPartner',
            readonly: true,
        }),
        id: attr({
            compute: '_computeId',
        }),
        name: attr({
            compute: '_computeName',
        }),
        partner: one('Partner', {
            inverse: 'channelPartner',
            readonly: true,
        }),
    },
});
