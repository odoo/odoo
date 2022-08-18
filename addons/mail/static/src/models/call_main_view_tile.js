/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallMainViewTile',
    fields: {
        callMainViewOwner: one('CallMainView', {
            identifying: true,
            inverse: 'mainTiles',
        }),
        channelMember: one('ChannelMember', {
            identifying: true,
        }),
        participantCard: one('CallParticipantCard', {
            default: {},
            inverse: 'mainViewTileOwner',
            isCausal: true,
        }),
    },
});
