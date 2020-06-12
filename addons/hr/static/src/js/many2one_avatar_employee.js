odoo.define('hr.Many2OneAvatarEmployee', function (require) {
    "use strict";

    // This module defines a variant of the Many2OneAvatarUser field widget,
    // to support many2one fields pointing to 'hr.employee'. It also defines the
    // kanban version of this widget.
    //
    // Usage:
    //   <field name="employee_id" widget="many2one_avatar_employee"/>

    const { _t } = require('web.core');
    const fieldRegistry = require('web.field_registry');
    const { Many2OneAvatarUser, KanbanMany2OneAvatarUser } = require('mail.Many2OneAvatarUser');
    const session = require('web.session');


    const Many2OneAvatarEmployeeMixin = {
        supportedModel: 'hr.employee',

        /**
         * Set the field to read on 'hr.employee' to get the partner id.
         *
         * @override
         */
        init() {
            this._super(...arguments);
            this.partnerField = 'user_partner_id';
        },

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Display a warning if the user clicked on himself, or on an employee
         * not associated with any user.
         *
         * @override
         * @param {number} [partnerId] the id of the clicked partner
         */
        _displayWarning(partnerId) {
            if (partnerId !== session.partner_id) {
                // this is not ourself, so if we get here it means that the
                // employee is not associated with any user
                this.displayNotification({
                    message: _t('You can only chat with employees that have a dedicated user'),
                    type: 'info',
                });
            } else {
                this._super(...arguments);
            }
        },
    };

    const Many2OneAvatarEmployee = Many2OneAvatarUser.extend(Many2OneAvatarEmployeeMixin);
    const KanbanMany2OneAvatarEmployee = KanbanMany2OneAvatarUser.extend(Many2OneAvatarEmployeeMixin);

    fieldRegistry.add('many2one_avatar_employee', Many2OneAvatarEmployee);
    fieldRegistry.add('kanban.many2one_avatar_employee', KanbanMany2OneAvatarEmployee);

    return {
        Many2OneAvatarEmployee,
        KanbanMany2OneAvatarEmployee,
    };
});
