/** @odoo-module **/

import { registerFieldPatchModel, registerInstancePatchModel } from '@mail/model/model_core';

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
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerInstancePatchModel('mail.message', 'snailmail', instancePatchMessage);
    registerInstancePatchModel('mail.messaging', 'snailmail', instancePatchMessaging);
    registerFieldPatchModel('mail.messaging', 'snailmail', fieldPatchMessaging);
    registerInstancePatchModel('mail.notification_group', 'snailmail', instancePatchNotificationGroup);
}
