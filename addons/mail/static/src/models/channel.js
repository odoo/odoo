/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one, many } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'Channel',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeThread() {
            return insertAndReplace({
                id: this.id,
                model: 'mail.channel',
            });
        },
        _sortMembers() {
            return [
                ['defined-first', 'name'],
                ['case-insensitive-asc', 'name'],
            ];
        },
    },
    fields: {
        channelPartners: many('ChannelPartner', {
            inverse: 'channel',
            isCausal: true,
            sort: '_sortMembers',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        memberCount: attr(),
        thread: one('Thread', {
            compute: '_computeThread',
            inverse: 'channelOwner',
            isCausal: true,
            readonly: true,
            required: true,
        })
    },
});
