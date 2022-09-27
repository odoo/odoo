/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerPatch({
    name: 'Channel',
    fields: {
        anonymous_country: one('Country'),
        anonymous_name: attr(),
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
    },
});
