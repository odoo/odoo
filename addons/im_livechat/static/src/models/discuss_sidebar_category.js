/** @odoo-module **/

import { addFields, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category';

addFields('DiscussSidebarCategory', {
    discussAsLivechat: one('Discuss', {
        inverse: 'categoryLivechat',
        readonly: true,
    }),
});

patchIdentifyingFields('DiscussSidebarCategory', identifyingFields => {
    identifyingFields[0].push('discussAsLivechat');
});

patchRecordMethods('DiscussSidebarCategory', {
    /**
     * @override
     */
    _computeName() {
        if (this.discussAsLivechat) {
            return this.env._t("Livechat");
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeSortComputeMethod() {
        if (this.discussAsLivechat) {
            return 'last_action';
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeSupportedChannelTypes() {
        if (this.discussAsLivechat) {
            return ['livechat'];
        }
        return this._super();
    },
});
