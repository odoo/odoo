/** @odoo-module **/

import { registerClassPatchModel, registerFieldPatchModel, registerInstancePatchModel, registerNewModel } from '@mail/model/model_core';

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
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerInstancePatchModel('mail.messaging_notification_handler', 'website_livechat', instancePatchMessagingNoficationHandler);
    registerClassPatchModel('mail.thread', 'website_livechat', classPatchThread);
    registerFieldPatchModel('mail.thread', 'website_livechat', fieldPatchThread);
    registerNewModel('website_livechat.visitor', factoryVisitor);
    env.modelManager.modelRegistry.set('website_livechat.visitor', factoryVisitor);
}
