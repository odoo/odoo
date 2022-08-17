/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/discuss_sidebar_category';

addFields('DiscussSidebarCategory', {
    discussAsLivechat: one('Discuss', {
        identifying: true,
        inverse: 'categoryLivechat',
    }),
});

patchRecordMethods('DiscussSidebarCategory', {
    /**
     * @override
     * @private
     * @returns {boolean|FieldCommand}
     */
    _computeIsServerOpen() {
        // there is no server state for non-users (guests)
        if (!this.messaging.currentUser) {
            return clear();
        }
        if (!this.messaging.currentUser.res_users_settings_id) {
            return clear();
        }
        if (this.discussAsLivechat) {
            return this.messaging.currentUser.res_users_settings_id.is_discuss_sidebar_category_livechat_open;
        }
        return this._super();
    },
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
     * @private
     * @returns {string|FieldCommand}
     */
    _computeServerStateKey() {
        if (this.discussAsLivechat) {
            return 'is_discuss_sidebar_category_livechat_open';
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
