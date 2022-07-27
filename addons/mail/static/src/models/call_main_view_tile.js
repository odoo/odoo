/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallMainViewTile',
    identifyingFields: ['callMainViewOwner', 'channelMember'],
    fields: {
        callMainViewOwner: one('CallMainView', {
            inverse: 'mainTiles',
            readonly: true,
            required: true,
        }),
        channelMember: one('ChannelMember', {
            readonly: true,
            required: true,
        }),
        participantCard: one('CallParticipantCard', {
            default: insertAndReplace(),
            inverse: 'mainViewTileOwner',
            isCausal: true,
        }),
    },
});
