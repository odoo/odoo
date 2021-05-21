/** @odoo-module **/

import { registerInstancePatchModel } from '@mail/model/model_core';

import { instancePatchMessagingInitializer } from '@mail_bot/models/messaging_initializer/messaging_initializer';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerInstancePatchModel('mail.messaging_initializer', 'mail_bot', instancePatchMessagingInitializer);
}
