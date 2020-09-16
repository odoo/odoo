odoo.define('hr/static/src/models/partner/partner.js', function (require) {
'use strict';

const {
    registerInstancePatchModel,
    registerFieldPatchModel,
} = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field_utils.js');

registerInstancePatchModel('mail.partner', 'hr/static/src/models/partner/partner.js', {
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Checks whether this partner has a related employee and links them if
     * applicable.
     */
    async checkIsEmployee() {
        await this.async(() => this.env.models['hr.employee'].performRpcSearchRead({
            context: { active_test: false },
            domain: [['user_partner_id', '=', this.__mfield_id(this)]],
            fields: ['user_id', 'user_partner_id'],
        }));
        this.update({ __mfield_hasCheckedEmployee: true });
    },
    /**
     * When a partner is an employee, its employee profile contains more useful
     * information to know who he is than its partner profile.
     *
     * @override
     */
    async openProfile() {
        // limitation of patch, `this._super` becomes unavailable after `await`
        const _super = this._super.bind(this, ...arguments);
        if (!this.__mfield_employee(this) && !this.__mfield_hasCheckedEmployee(this)) {
            await this.async(() => this.checkIsEmployee());
        }
        if (this.__mfield_employee(this)) {
            return this.__mfield_employee(this).openProfile();
        }
        return _super();
    },
});

registerFieldPatchModel('mail.partner', 'hr/static/src/models/partner/partner.js', {
    /**
     * Employee related to this partner. It is computed through
     * the inverse relation and should be considered read-only.
     */
    __mfield_employee: one2one('hr.employee', {
        inverse: '__mfield_partner',
    }),
    /**
     * Whether an attempt was already made to fetch the employee corresponding
     * to this partner. This prevents doing the same RPC multiple times.
     */
    __mfield_hasCheckedEmployee: attr({
        default: false,
    }),
});

});
