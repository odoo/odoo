/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss';

patchRecordMethods('Discuss', {
    /**
     * @override
     */
    onInputQuickSearch(value) {
        if (!this.sidebarQuickSearchValue) {
            this.categoryLivechat.open();
        }
        return this._super(value);
    },
});

addFields('Discuss', {
    /**
     * Discuss sidebar category for `livechat` channel threads.
     */
    categoryLivechat: one('DiscussSidebarCategory', {
        default: {},
        inverse: 'discussAsLivechat',
        isCausal: true,
    }),
});
