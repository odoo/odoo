/** @odoo-module **/

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
    env.modelManager.registerInstancePatch('mail.chat_window', 'im_livechat', instancePatchChatWindow);
    env.modelManager.registerInstancePatch('mail.messaging_initializer', 'im_livechat', instancePatchMessagingInitializer);
    env.modelManager.registerInstancePatch('mail.messaging_notification_handler', 'im_livechat', instancePatchMessagingNotificationHandler);
    env.modelManager.registerClassPatch('mail.partner', 'im_livechat', classPatchPartner);
    env.modelManager.registerClassPatch('mail.thread', 'im_livechat', classPatchThread);
    env.modelManager.registerInstancePatch('mail.thread', 'im_livechat', instancePatchThread);
}
