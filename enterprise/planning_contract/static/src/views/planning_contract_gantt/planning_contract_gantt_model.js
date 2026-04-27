import { serializeDateTime, deserializeDateTime } from "@web/core/l10n/dates";
import { PlanningGanttModel } from "@planning/views/planning_gantt/planning_gantt_model";
import { patch } from "@web/core/utils/patch";

patch(PlanningGanttModel.prototype, {
    /**
     * @override
     */
    _fetchDataPostProcess(metaData, data) {
        const proms = [super._fetchDataPostProcess(...arguments)];
        if (!this.orm.isSample) {
            proms.push(this._fetchEmployeesWorkingPeriods(metaData, data));
        }
        return Promise.all(proms);
    },
    /**
     * Fetch employees working periods.
     * @param {MetaData} metaData
     * @param {Data} data
     */
    async _fetchEmployeesWorkingPeriods(metaData, data) {
        const enrichedRows = await this.orm.call(
            metaData.resModel,
            "gantt_resource_employees_working_periods",
            [data.rows],
            {
                context: {
                    ...this.searchParams.context,
                    scale: metaData.scale,
                    default_start_datetime: serializeDateTime(metaData.globalStart),
                    default_end_datetime: serializeDateTime(metaData.globalStop),
                },
            }
        );
        this._updateWorkingPeriodsRows(data.rows, enrichedRows);
    },
    /**
     * Update rows with working periods enriched rows.
     *
     * @protected
     * @param {Row[]} original rows in the format of ganttData.rows
     * @param {Row[]} enriched rows as returned by the _fetchEmployeesWorkingPeriods rpc call
     */
    _updateWorkingPeriodsRows(original, enriched) {
        for (let i = 0; i < original.length; i++) {
            const originalI = original[i];
            const enrichedI = enriched[i];
            if (!enrichedI || !originalI) {
                continue;
            }
            if ("working_periods" in enrichedI) {
                originalI.workingPeriods =
                    enrichedI.working_periods.map((period) => {
                        // These are new data from the server, they haven't been parsed yet
                        period.start = deserializeDateTime(period.start);
                        period.end = period.end && deserializeDateTime(period.end);
                        return period;
                    }) || [];
            }
            if (originalI.rows && enrichedI.rows) {
                this._updateWorkingPeriodsRows(originalI.rows, enrichedI.rows);
            }
        }
    },
});
