odoo.define('snailmail/static/src/models/messaging/messaging.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
    registerFieldPatchModel,
} = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

registerInstancePatchModel('mail.messaging', 'snailmail/static/src/models/messaging/messaging.js', {
    async fetchSnailmailCreditsUrl() {
        const snailmail_credits_url = await this.async(() => this.env.services.rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['snailmail'],
        }));
        this.update({
            snailmail_credits_url,
        });
    },
    async fetchSnailmailCreditsUrlTrial() {
        const snailmail_credits_url_trial = await this.async(() => this.env.services.rpc({
            model: 'iap.account',
            method: 'get_credits_url',
            args: ['snailmail', '', 0, true],
        }));
        this.update({
            snailmail_credits_url_trial,
        });
    },
});

registerFieldPatchModel('mail.messaging', 'snailmail/static/src/models/messaging/messaging.js', {
    snailmail_credits_url: attr(),
    snailmail_credits_url_trial: attr(),
});

});
