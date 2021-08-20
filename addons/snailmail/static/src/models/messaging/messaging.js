odoo.define('snailmail/static/src/models/messaging/messaging.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
    registerFieldPatchModel,
} = require('@mail/model/model_core');
const { attr } = require('@mail/model/model_field');

registerInstancePatchModel('mail.messaging', 'snailmail/static/src/models/messaging/messaging.js', {
    async fetchSnailmailCreditsUrl() {
        const snailmail_credits_url = await this.env.services.orm.call('iap.account', 'get_credits_url', [], {
            service_name: 'snailmail',
        });
        if (!this.exists()) {
            return;
        }
        this.update({ snailmail_credits_url });
    },
    async fetchSnailmailCreditsUrlTrial() {
        const snailmail_credits_url_trial = await this.env.services.orm.call('iap.account', 'get_credits_url', [], {
            service_name: 'snailmail',
            trial: true,
        });
        if (!this.exists()) {
            return;
        }
        this.update({ snailmail_credits_url_trial });
    },
});

registerFieldPatchModel('mail.messaging', 'snailmail/static/src/models/messaging/messaging.js', {
    snailmail_credits_url: attr(),
    snailmail_credits_url_trial: attr(),
});

});
