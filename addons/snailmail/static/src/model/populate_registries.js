/** @odoo-module **/

import { instancePatchMessage } from '@snailmail/models/message/message';
import { fieldPatchMessaging, instancePatchMessaging } from '@snailmail/models/messaging/messaging';
import { instancePatchNotificationGroup } from '@snailmail/models/notification_group/notification_group';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    env.modelManager.registerInstancePatch('mail.message', 'snailmail', instancePatchMessage);
    env.modelManager.registerInstancePatch('mail.messaging', 'snailmail', instancePatchMessaging);
    env.modelManager.registerFieldPatch('mail.messaging', 'snailmail', fieldPatchMessaging);
    env.modelManager.registerInstancePatch('mail.notification_group', 'snailmail', instancePatchNotificationGroup);
}
