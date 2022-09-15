/** @odoo-module **/

import { addFields, patchFields } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import '@mail/models/channel'; // ensure that the model definition is loaded before the patch

addFields('Channel', {
    anonymous_country: one('Country'),
    anonymous_name: attr(),
});

patchFields('Channel', {
    discussSidebarCategory: {
        compute() {
            if (this.channel_type === 'livechat') {
                return this.messaging.discuss.categoryLivechat;
            }
            return this._super();
        },
    },
    displayName: {
        compute() {
            if (!this.thread) {
                return;
            }
            if (this.channel_type === 'livechat' && this.correspondent) {
                if (!this.correspondent.is_public && this.correspondent.country) {
                    return `${this.thread.getMemberName(this.correspondent.persona)} (${this.correspondent.country.name})`;
                }
                if (this.anonymous_country) {
                    return `${this.thread.getMemberName(this.correspondent.persona)} (${this.anonymous_country.name})`;
                }
                return this.thread.getMemberName(this.correspondent.persona);
            }
            return this._super();
        },
    },
});
