/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/channel';

addFields('Channel', {
    livechatCorrespondent: one('Partner'),
});

patchRecordMethods('Channel', {
    /**
     * @override
     */
    _computeCorrespondent() {
        if (this.channel_type === 'livechat') {
            return this.livechatCorrespondent || clear();
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeDiscussSidebarCategory() {
        if (this.channel_type === 'livechat') {
            return this.messaging.discuss.categoryLivechat;
        }
        return this._super();
    },
    /**
     * @override
     */
    _computeDisplayName() {
        if (this.channel_type === 'livechat' && this.correspondent) {
            if (this.correspondent.country) {
                return `${this.correspondent.nameOrDisplayName} (${this.correspondent.country.name})`;
            }
            return this.correspondent.nameOrDisplayName;
        }
        return this._super();
    },
});
