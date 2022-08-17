/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { insertAndReplace } from '@mail/model/model_field_command';
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
            default: insertAndReplace(),
            inverse: 'mainViewTileOwner',
            isCausal: true,
        }),
    },
});
