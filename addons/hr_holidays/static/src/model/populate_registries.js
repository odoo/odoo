/** @odoo-module **/

import { classPatchPartner, fieldPatchPartner, instancePatchPartner } from '@hr_holidays/models/partner/partner';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    env.modelManager.registerClassPatch('mail.partner', 'hr_holidays', classPatchPartner);
    env.modelManager.registerFieldPatch('mail.partner', 'hr_holidays', fieldPatchPartner);
    env.modelManager.registerInstancePatch('mail.partner', 'hr_holidays', instancePatchPartner);
}
