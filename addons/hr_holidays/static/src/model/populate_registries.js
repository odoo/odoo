/** @odoo-module **/

import { registerClassPatchModel, registerFieldPatchModel, registerInstancePatchModel } from '@mail/model/model_core';

import { classPatchPartner, fieldPatchPartner, instancePatchPartner } from '@hr_holidays/models/partner/partner';


/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerClassPatchModel('mail.partner', 'hr_holidays', classPatchPartner);
    registerFieldPatchModel('mail.partner', 'hr_holidays', fieldPatchPartner);
    registerInstancePatchModel('mail.partner', 'hr_holidays', instancePatchPartner);
}
