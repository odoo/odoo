/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'CallSidebarView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeSidebarTiles() {
            return this.callView.filteredChannelMembers.map(channelMember => ({ channelMember }));
        },
    },
    fields: {
        callView: one('CallView', {
            identifying: true,
            inverse: 'callSidebarView',
        }),
        sidebarTiles: many('CallSidebarViewTile', {
            compute: '_computeSidebarTiles',
            inverse: 'callSidebarViewOwner',
        }),
    },
});
