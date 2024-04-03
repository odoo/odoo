/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerPatch({
    name: 'Partner',
    recordMethods: {
        /**
         * Checks whether this partner has a related employee and links them if
         * applicable.
         */
        async checkIsEmployee() {
            await this.messaging.models['Employee'].performRpcSearchRead({
                context: { active_test: false },
                domain: [['user_partner_id', '=', this.id]],
                fields: ['user_id', 'user_partner_id'],
            });
            if (!this.exists()) {
                return;
            }
            this.update({ hasCheckedEmployee: true });
        },
        /**
         * When a partner is an employee, its employee profile contains more
         * useful information to know who he is than its partner profile.
         *
         * @override
         */
        async openProfile() {
            // limitation of patch, `this._super` becomes unavailable after `await`
            const _super = this._super.bind(this, ...arguments);
            if (!this.employee && !this.hasCheckedEmployee) {
                await this.checkIsEmployee();
            }
            if (!this.exists()) {
                return;
            }
            if (this.employee) {
                return this.employee.openProfile();
            }
            return _super();
        },
    },
    fields: {
        /**
         * Employee related to this partner. It is computed through
         * the inverse relation and should be considered read-only.
         */
        employee: one('Employee', {
            inverse: 'partner',
        }),
        /**
         * Whether an attempt was already made to fetch the employee
         * corresponding to this partner. This prevents doing the same RPC
         * multiple times.
         */
        hasCheckedEmployee: attr({
            default: false,
        }),
    },
});
