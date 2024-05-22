odoo.define('hr.Many2OneAvatarEmployee', function (require) {
    "use strict";

    // This module defines a variant of the Many2OneAvatarUser field widget,
    // to support many2one fields pointing to 'hr.employee'. It also defines the
    // kanban version of this widget.
    //
    // Usage:
    //   <field name="employee_id" widget="many2one_avatar_employee"/>

    const fieldRegistry = require('web.field_registry');
    const { Many2OneAvatarUser, KanbanMany2OneAvatarUser } = require('mail.Many2OneAvatarUser');

    const { Component } = owl;

    const Many2OneAvatarEmployeeMixin = {
        supportedModels: ['hr.employee', 'hr.employee.public'],

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        async _onAvatarClicked(ev) {
            ev.stopPropagation(); // in list view, prevent from opening the record
            const env = Component.env;
            await env.messaging.openChat({ employeeId: this.value.res_id });
        }
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
