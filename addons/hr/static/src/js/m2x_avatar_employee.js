/** @odoo-module alias=hr.Many2OneAvatarEmployee **/

import fieldRegistry from 'web.field_registry';

import { Many2OneAvatarUser, KanbanMany2OneAvatarUser, KanbanMany2ManyAvatarUser, ListMany2ManyAvatarUser } from '@mail/js/m2x_avatar_user';
import { Many2ManyAvatarUser } from '@mail/js/m2x_avatar_user';
import { KanbanMany2ManyTagsAvatar, ListMany2ManyTagsAvatar } from 'web.relational_fields';


// This module defines variants of the Many2OneAvatarUser and Many2ManyAvatarUser
// field widgets, to support fields pointing to 'hr.employee'. It also defines the
// kanban version of the Many2OneAvatarEmployee widget.
//
// Usage:
//   <field name="employee_id" widget="many2one_avatar_employee"/>

const M2XAvatarEmployeeMixin = {
    supportedModels: ['hr.employee', 'hr.employee.public'],

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    _getEmployeeID() {
        return this.value.res_id;
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @override
     */
    _onAvatarClicked(ev) {
        ev.stopPropagation(); // in list view, prevent from opening the record
        const employeeId = this._getEmployeeID(ev);
        this._openChat({ employeeId: employeeId });
    }
};

export const Many2OneAvatarEmployee = Many2OneAvatarUser.extend(M2XAvatarEmployeeMixin);
export const KanbanMany2OneAvatarEmployee = KanbanMany2OneAvatarUser.extend(M2XAvatarEmployeeMixin);

fieldRegistry.add('many2one_avatar_employee', Many2OneAvatarEmployee);
fieldRegistry.add('kanban.many2one_avatar_employee', KanbanMany2OneAvatarEmployee);

const M2MAvatarEmployeeMixin = Object.assign(M2XAvatarEmployeeMixin, {
    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    _getEmployeeID(ev) {
        return parseInt(ev.target.getAttribute('data-id'), 10);
    },
});

export const Many2ManyAvatarEmployee = Many2ManyAvatarUser.extend(M2MAvatarEmployeeMixin, {});

export const KanbanMany2ManyAvatarEmployee = KanbanMany2ManyAvatarUser.extend(M2MAvatarEmployeeMixin, {});

export const ListMany2ManyAvatarEmployee = ListMany2ManyAvatarUser.extend(M2MAvatarEmployeeMixin, {});

fieldRegistry.add('many2many_avatar_employee', Many2ManyAvatarEmployee);
fieldRegistry.add('kanban.many2many_avatar_employee', KanbanMany2ManyAvatarEmployee);
fieldRegistry.add('list.many2many_avatar_employee', ListMany2ManyAvatarEmployee);

export default {
    Many2OneAvatarEmployee,
};
