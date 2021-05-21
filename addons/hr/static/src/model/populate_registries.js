/** @odoo-module **/

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
    env.modelManager.registerModel('hr.employee', factoryEmployee);
    env.modelManager.registerInstancePatch('mail.messaging', 'hr', instancePatchMessaging);
    env.modelManager.registerFieldPatch('mail.partner', 'hr', fieldPatchPartner);
    env.modelManager.registerInstancePatch('mail.partner', 'hr', instancePatchPartner);
    env.modelManager.registerFieldPatch('mail.user', 'hr', fieldPatchUser);
}
