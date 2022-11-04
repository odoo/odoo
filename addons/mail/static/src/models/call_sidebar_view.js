/** @odoo-module **/

import { many, one, registerModel } from '@mail/model';

registerModel({
    name: 'CallSidebarView',
    template: 'mail.CallSidebarView',
    templateGetter: 'callSidebarView',
    fields: {
        callView: one('CallView', { identifying: true, inverse: 'callSidebarView' }),
        sidebarTiles: many('CallSidebarViewTile', { inverse: 'callSidebarViewOwner',
            compute() {
                return this.callView.filteredChannelMembers.map(channelMember => ({ channelMember }));
            },
        }),
    },
});
