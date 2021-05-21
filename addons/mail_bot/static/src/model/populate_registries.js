/** @odoo-module **/

import { instancePatchMessagingInitializer } from '@mail_bot/models/messaging_initializer/messaging_initializer';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    env.modelManager.registerInstancePatch('mail.messaging_initializer', 'mail_bot', instancePatchMessagingInitializer);
}
