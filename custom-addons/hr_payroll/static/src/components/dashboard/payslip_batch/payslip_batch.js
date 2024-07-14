/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PayrollDashboardPayslipBatch extends Component {
    setup() {
        this.actionService = useService("action");
    }

    /**
     * Handles clicking on the title
     */
    onClickTitle() {
        this.actionService.doAction('hr_payroll.action_hr_payslip_run_tree');
    }

    getColorFromState(state) {
        const colorMap = {
            'New': 'text-bg-secondary',
            'Confirmed': 'text-bg-success',
            'Done': 'text-bg-primary',
            'Paid': 'text-bg-warning',
        };
        return colorMap[state] || 'text-bg-primary'
    }

    /**
     * Handles clicking on the line
     *
     * @param {number} batchID
     * @param {string} batchNames
     */
    onClickLine(batchID, batchName) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            name: _t('Employee Payslips'),
            res_model: 'hr.payslip.run',
            res_id: batchID,
            views: [[false, 'form']],
        });
    }
}

PayrollDashboardPayslipBatch.template = 'hr_payroll.PayslipBatch';
