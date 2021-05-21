/** @odoo-module **/

import { registerClassPatchModel, registerInstancePatchModel } from '@mail/model/model_core';

import { instancePatchChatWindow } from '@im_livechat/models/chat_window/chat_window';
import { instancePatchMessagingInitializer } from '@im_livechat/models/messaging_initializer/messaging_initializer';
import { instancePatchMessagingNotificationHandler } from '@im_livechat/models/messaging_notification_handler/messaging_notification_handler';
import { classPatchPartner } from '@im_livechat/models/partner/partner';
import { classPatchThread, instancePatchThread } from '@im_livechat/models/thread/thread';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerInstancePatchModel('mail.chat_window', 'im_livechat', instancePatchChatWindow);
    registerInstancePatchModel('mail.messaging_initializer', 'im_livechat', instancePatchMessagingInitializer);
    registerInstancePatchModel('mail.messaging_notification_handler', 'im_livechat', instancePatchMessagingNotificationHandler);
    registerClassPatchModel('mail.partner', 'im_livechat', classPatchPartner);
    registerClassPatchModel('mail.thread', 'im_livechat', classPatchThread);
    registerInstancePatchModel('mail.thread', 'im_livechat', instancePatchThread);
}
