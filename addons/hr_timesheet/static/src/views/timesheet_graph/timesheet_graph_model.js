import { GraphModel } from "@web/views/graph/graph_model";
import { user } from "@web/core/user";

const FIELDS = [
    'unit_amount', 'effective_hours', 'allocated_hours', 'remaining_hours', 'total_hours_spent', 'subtask_effective_hours',
    'overtime', 'number_hours', 'difference', 'timesheet_unit_amount'
];

export class hrTimesheetGraphModel extends GraphModel {
    /**
     * @override
     */
    setup(params, services) {
        super.setup(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override processDataPoints to take into account the analytic line uom.
     * @override
     */
    _getProcessedDataPoints() {
        const factor = user.activeCompany.timesheet_uom_factor || 1;
        if (factor !== 1 && FIELDS.includes(this.metaData.measure)) {
            // recalculate the Duration values according to the timesheet_uom_factor
            for (const dataPt of this.dataPoints) {
                dataPt.value *= factor;
            }
        }
        return super._getProcessedDataPoints(...arguments);
    }
}
