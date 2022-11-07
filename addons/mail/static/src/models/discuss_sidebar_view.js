/** @odoo-module **/

import { attr, one, Model } from '@mail/model';

Model({
    name: 'DiscussSidebarView',
    template: 'mail.DiscussSidebarView',
    lifecycleHooks: {
        _componentUpdated() {
            if (this.quickSearchInputRef.el) {
                this.quickSearchInputRef.el.value = this.owner.discuss.sidebarQuickSearchValue;
            }
        },
    },
    fields: {
        owner: one('DiscussView', { identifying: true, inverse: 'sidebar' }),
        /**
         * Reference to the quick search input. Useful to filter channels and
         * chats based on the content of the input.
         */
        quickSearchInputRef: attr({ ref: 'quickSearchInput' }),
    },
});
