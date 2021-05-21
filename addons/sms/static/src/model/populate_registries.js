/** @odoo-module **/

import { instancePatchMessage } from '@sms/models/message/message';
import { instancePatchNotificationGroup } from '@sms/models/notification_group/notification_group';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    env.modelManager.registerInstancePatch('mail.message', 'sms', instancePatchMessage);
    env.modelManager.registerInstancePatch('mail.notification_group', 'sms', instancePatchNotificationGroup);
}
