/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Discuss',
    recordMethods: {
        /**
         * @override
         */
        onInputQuickSearch(value) {
            if (!this.sidebarQuickSearchValue) {
                this.categoryLivechat.open();
            }
            return this._super(value);
        },
    },
    fields: {
        /**
         * Discuss sidebar category for `livechat` channel threads.
         */
        categoryLivechat: one('DiscussSidebarCategory', {
            default: {},
            inverse: 'discussAsLivechat',
        }),
    },
});
