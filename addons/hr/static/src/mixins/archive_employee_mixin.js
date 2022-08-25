/** @odoo-module */

export const ArchiveEmployeeMixin = {
    _openArchiveEmployee(id) {
        return {
            type: 'ir.actions.act_window',
            name: this.env._t('Employee Termination'),
            res_model: 'hr.departure.wizard',
            views: [[false, 'form']],
            view_mode: 'form',
            target: 'new',
            context: {
                'active_id': id,
                'toggle_active': true,
            }
        }
    }
};
