/** @odoo-module **/

import { instancePatchMessagingNoficationHandler } from '@website_livechat/models/messaging_notification_handler/messaging_notification_handler';
import { classPatchThread, fieldPatchThread } from '@website_livechat/models/thread/thread';
import { factoryVisitor } from '@website_livechat/models/visitor/visitor';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    env.modelManager.registerInstancePatch('mail.messaging_notification_handler', 'website_livechat', instancePatchMessagingNoficationHandler);
    env.modelManager.registerClassPatch('mail.thread', 'website_livechat', classPatchThread);
    env.modelManager.registerFieldPatch('mail.thread', 'website_livechat', fieldPatchThread);
    env.modelManager.registerModel('website_livechat.visitor', factoryVisitor);
}
