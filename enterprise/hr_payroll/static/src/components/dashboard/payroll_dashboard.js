/** @odoo-module **/

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";

import { PayrollDashboardActionBox } from '@hr_payroll/components/dashboard/action_box/action_box';
import { PayrollDashboardPayslipBatch } from '@hr_payroll/components/dashboard/payslip_batch/payslip_batch';
import { PayrollDashboardTodo } from '@hr_payroll/components/dashboard/todo_list/todo_list';
import { PayrollDashboardStats } from '@hr_payroll/components/dashboard/payroll_stats/payroll_stats';
import { Component, onWillStart } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

class PayrollDashboardComponent extends Component {
    static template = "hr_payroll.Dashboard";
    static components = {
        PayrollDashboardActionBox,
        PayrollDashboardPayslipBatch,
        PayrollDashboardTodo,
        PayrollDashboardStats,
    };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService('orm');
        onWillStart(async () => {
            this.dashboardData = await this.orm.call('hr.payslip', 'get_payroll_dashboard_data', []);
        });
    }

    /**
     * Updates the note in database and reload notes data right after.
     */
    async updateNoteMemo(id, memo) {
        await this.orm.write('hr.payroll.note', [id], { memo });
        this.reloadNotes();
    }

    /**
     * Call to reload note data.
     */
    async reloadNotes() {
        const kwargs = { sections: ['notes'] };
        const newData = await this.orm.call('hr.payslip', 'get_payroll_dashboard_data', [], kwargs);
        this.dashboardData.notes = newData.notes;
        this.render();
    }
}

registry.category('actions').add('hr_payroll_dashboard', PayrollDashboardComponent);

export default PayrollDashboardComponent;
