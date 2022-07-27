/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarViewTile',
    identifyingFields: ['callSidebarViewOwner', 'channelMember'],
    fields: {
        callSidebarViewOwner: one('CallSidebarView', {
            inverse: 'sidebarTiles',
            readonly: true,
            required: true,
        }),
        channelMember: one('ChannelMember', {
            readonly: true,
            required: true,
        }),
        participantCard: one('CallParticipantCard', {
            default: insertAndReplace(),
            inverse: 'sidebarViewTileOwner',
            isCausal: true,
        }),
    },
});
