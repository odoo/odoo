/** @odoo-module **/

import { registerFieldPatchModel, registerInstancePatchModel, registerNewModel } from '@mail/model/model_core';

import { factoryEmployee } from '@hr/models/employee/employee';
import { instancePatchMessaging } from '@hr/models/messaging/messaging';
import { fieldPatchPartner, instancePatchPartner } from '@hr/models/partner/partner';
import { fieldPatchUser } from '@hr/models/user/user';

/**
 * Populate registries with models, fields, and properties expected by the app.
 *
 * @param {Object} param0
 * @param {Object} param0.env
 */
export function populateRegistries({ env }) {
    // TODO SEB convert those to modelManager stuff, add them in tests
    registerNewModel('hr.employee', factoryEmployee);
    env.modelManager.modelRegistry.set('hr.employee', factoryEmployee);
    registerInstancePatchModel('mail.messaging', 'hr', instancePatchMessaging);
    registerFieldPatchModel('mail.partner', 'hr', fieldPatchPartner);
    registerInstancePatchModel('mail.partner', 'hr', instancePatchPartner);
    registerFieldPatchModel('mail.user', 'hr', fieldPatchUser);
}
