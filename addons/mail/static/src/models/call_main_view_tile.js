/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'CallMainViewTile',
    fields: {
        callMainViewOwner: one('CallMainView', { identifying: true, inverse: 'mainTiles' }),
        channelMember: one('ChannelMember', { identifying: true }),
        participantCard: one('CallParticipantCard', { default: {}, inverse: 'mainViewTileOwner' }),
    },
});
