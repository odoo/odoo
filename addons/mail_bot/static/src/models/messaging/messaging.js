/** @odoo-module **/

import { registerFieldPatchModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerFieldPatchModel('mail.messaging', 'mail_bot/static/src/models/messaging/messaging.js', {
    odoobot_initialized: attr(),
});

