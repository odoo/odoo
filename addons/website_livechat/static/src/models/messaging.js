/** @odoo-module **/

import { addFields } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/messaging';

addFields('Messaging', {
    publicLivechatServerUrlChatbot: attr(),
});
