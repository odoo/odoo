/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarView',
    template: 'mail.CallSidebarView',
    fields: {
        callView: one('CallView', { identifying: true, inverse: 'callSidebarView' }),
        sidebarTiles: many('CallSidebarViewTile', { inverse: 'callSidebarViewOwner',
            compute() {
                return this.callView.filteredChannelMembers.map(channelMember => ({ channelMember }));
            },
        }),
    },
});
