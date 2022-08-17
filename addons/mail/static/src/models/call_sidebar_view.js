/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallSidebarView',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeSidebarTiles() {
            return insertAndReplace(this.callView.filteredChannelMembers.map(channelMember => ({ channelMember })));
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
            isCausal: true,
        }),
    },
});
