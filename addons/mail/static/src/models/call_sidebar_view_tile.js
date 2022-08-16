/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarViewTile',
    fields: {
        callSidebarViewOwner: one('CallSidebarView', {
            identifying: true,
            inverse: 'sidebarTiles',
            readonly: true,
            required: true,
        }),
        channelMember: one('ChannelMember', {
            identifying: true,
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
