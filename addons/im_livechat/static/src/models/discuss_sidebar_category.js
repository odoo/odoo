/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
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

patchFields('DiscussSidebarCategory', {
    categoryItemsOrderedByLastAction: {
        compute() {
            if (this.discussAsLivechat) {
                return this.categoryItems;
            }
            return this._super();
        },
    },
    isServerOpen: {
        compute() {
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
    },
    name: {
        compute() {
            if (this.discussAsLivechat) {
                return this.env._t("Livechat");
            }
            return this._super();
        },
    },
    orderedCategoryItems: {
        compute() {
            if (this.discussAsLivechat) {
                return this.categoryItemsOrderedByLastAction;
            }
            return this._super();
        },
    },
    serverStateKey: {
        compute() {
            if (this.discussAsLivechat) {
                return 'is_discuss_sidebar_category_livechat_open';
            }
            return this._super();
        },
    },
    supportedChannelTypes: {
        compute() {
            if (this.discussAsLivechat) {
                return ['livechat'];
            }
            return this._super();
        },
    },
});
