/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'DiscussSidebarView',
    recordMethods: {
        onComponentUpdate() {
            if (this.quickSearchInputRef.el) {
                this.quickSearchInputRef.el.value = this.owner.discuss.sidebarQuickSearchValue;
            }
        },
    },
    fields: {
        owner: one('DiscussView', {
            identifying: true,
            inverse: 'sidebar',
        }),
        /**
         * Reference to the quick search input. Useful to filter channels and
         * chats based on the content of the input.
         */
        quickSearchInputRef: attr(),
    },
});
