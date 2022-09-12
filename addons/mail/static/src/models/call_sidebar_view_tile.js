/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarViewTile',
    fields: {
        callSidebarViewOwner: one('CallSidebarView', {
            identifying: true,
            inverse: 'sidebarTiles',
        }),
        channelMember: one('ChannelMember', {
            identifying: true,
        }),
        participantCardView: one('CallParticipantCardView', {
            default: {},
            inverse: 'sidebarViewTileOwner',
        }),
    },
});
