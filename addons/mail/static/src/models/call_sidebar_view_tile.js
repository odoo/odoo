/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'CallSidebarViewTile',
    fields: {
        callSidebarViewOwner: one('CallSidebarView', { identifying: true, inverse: 'sidebarTiles' }),
        channelMember: one('ChannelMember', { identifying: true }),
        participantCard: one('CallParticipantCard', { default: {}, inverse: 'sidebarViewTileOwner' }),
    },
});
