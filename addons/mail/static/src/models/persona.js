/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Persona',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeImStatus() {
            if (this.guest) {
                return this.guest.im_status || clear();
            }
            if (this.partner) {
                return this.partner.im_status || clear();
            }
            return clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeName() {
            if (this.guest) {
                return this.guest.name || clear();
            }
            if (this.partner) {
                return this.partner.nameOrDisplayName || clear();
            }
            return clear();
        },
    },
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
            compute: '_computeImStatus',
        }),
        name: attr({
            compute: '_computeName',
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'persona',
        }),
    },
});
