/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

import { instancePatchMessage } from '@sms/models/message/message';
import { instancePatchNotificationGroup } from '@sms/models/notification_group/notification_group';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerInstancePatchModel('mail.message', 'sms', instancePatchMessage);
    registerInstancePatchModel('mail.notification_group', 'sms', instancePatchNotificationGroup);
}
