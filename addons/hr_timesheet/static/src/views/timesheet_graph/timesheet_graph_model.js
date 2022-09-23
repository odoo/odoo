/** @odoo-module **/

import { GraphModel } from "@web/views/graph/graph_model";

const FIELDS = [
    'unit_amount', 'effective_hours', 'planned_hours', 'remaining_hours', 'total_hours_spent', 'subtask_effective_hours',
    'overtime', 'number_hours', 'difference', 'hours_effective', 'hours_planned', 'timesheet_unit_amount'
];

export class hrTimesheetGraphModel extends GraphModel {
    /**
     * @override
     */
    setup(params, services) {
        super.setup(...arguments);
        this.companyService = services.company;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override processDataPoints to take into account the analytic line uom.
     * @override
     */
    _getProcessedDataPoints() {
        const currentCompany = this.companyService.currentCompany;
        const factor = currentCompany.timesheet_uom_factor || 1;
        if (factor !== 1 && FIELDS.includes(this.metaData.measure)) {
            // recalculate the Duration values according to the timesheet_uom_factor
            for (const dataPt of this.dataPoints) {
                dataPt.value *= factor;
            }
        }
        return super._getProcessedDataPoints(...arguments);
    }
}
hrTimesheetGraphModel.services = [...GraphModel.services, "company"];
