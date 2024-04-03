/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerPatch({
    name: 'Messaging',
    recordMethods: {
        async fetchSnailmailCreditsUrl() {
            const snailmail_credits_url = await this.messaging.rpc({
                model: 'iap.account',
                method: 'get_credits_url',
                args: ['snailmail'],
            });
            if (!this.exists()) {
                return;
            }
            this.update({
                snailmail_credits_url,
            });
        },
        async fetchSnailmailCreditsUrlTrial() {
            const snailmail_credits_url_trial = await this.messaging.rpc({
                model: 'iap.account',
                method: 'get_credits_url',
                args: ['snailmail', '', 0, true],
            });
            if (!this.exists()) {
                return;
            }
            this.update({
                snailmail_credits_url_trial,
            });
        },
    },
    fields: {
        snailmail_credits_url: attr(),
        snailmail_credits_url_trial: attr(),
    },
});
