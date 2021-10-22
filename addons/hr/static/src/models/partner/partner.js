/** @odoo-module **/

import { addFields, addRecordMethods, patchRecordMethods } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/partner/partner';

addRecordMethods('mail.partner', {
    /**
     * Checks whether this partner has a related employee and links them if
     * applicable.
     */
    async checkIsEmployee() {
        await this.async(() => this.messaging.models['hr.employee'].performRpcSearchRead({
            context: { active_test: false },
            domain: [['user_partner_id', '=', this.id]],
            fields: ['user_id', 'user_partner_id'],
        }));
        this.update({ hasCheckedEmployee: true });
    },
});

patchRecordMethods('mail.partner', {
    /**
     * When a partner is an employee, its employee profile contains more useful
     * information to know who he is than its partner profile.
     *
     * @override
     */
    async openProfile() {
        // limitation of patch, `this._super` becomes unavailable after `await`
        const _super = this._super.bind(this, ...arguments);
        if (!this.employee && !this.hasCheckedEmployee) {
            await this.async(() => this.checkIsEmployee());
        }
        if (this.employee) {
            return this.employee.openProfile();
        }
        return _super();
    },
});

addFields('mail.partner', {
    /**
     * Employee related to this partner. It is computed through
     * the inverse relation and should be considered read-only.
     */
    employee: one2one('hr.employee', {
        inverse: 'partner',
    }),
    /**
     * Whether an attempt was already made to fetch the employee corresponding
     * to this partner. This prevents doing the same RPC multiple times.
     */
    hasCheckedEmployee: attr({
        default: false,
    }),
});
