/** @odoo-module **/

import { deserializeDateTime, serializeDateTime } from "@web/core/l10n/dates";
import { GanttModel } from "@web_gantt/gantt_model";
import { formatPercentage } from "@web/views/fields/formatters";

export class MRPWorkorderGanttModel extends GanttModel {

    /**
     * @override
     */
    _fetchDataPostProcess(metaData, data) {
        const previous_displayUnavailability = metaData.displayUnavailability;
        if (!metaData.groupedBy.includes("workcenter_id")) {
            metaData.displayUnavailability = false;
        }
        const proms = [super._fetchDataPostProcess(...arguments)];
        if (!metaData.groupedBy.includes("workcenter_id")) {
            metaData.displayUnavailability = previous_displayUnavailability;
            if (data.records.length && !this.orm.isSample) {
                proms.push(this._fetchWorkcentersUnavailabilities(metaData, data));
            }
        }
        return Promise.all(proms);
    }
    async _fetchWorkcentersUnavailabilities(metaData, data) {
        const workcenters = Array.from(new Set(data.records.map(record => record.workcenter_id[0])));
        const result = await this.orm.call(
            metaData.resModel,
            "gantt_unavailability",
            [
                serializeDateTime(metaData.startDate),
                serializeDateTime(metaData.stopDate),
                metaData.scale.id,
                ["workcenter_id"],
                workcenters.map((workcenter) => ({
                    groupedBy: ["workcenter_id"],
                    resId: workcenter,
                    rows: [],
                }))
            ],
            {
                context: this.searchParams.context,
            }
        );
        this.workcentersUnavailabilities = {};
        result.forEach((r) => {
            this.workcentersUnavailabilities[r.resId] = r.unavailabilities.map((u) => {
                return [deserializeDateTime(u.start), deserializeDateTime(u.stop)];
            });
        });
    }

    /**
     * @override
     */
    _addProgressBarInfo(_, rows) {
        super._addProgressBarInfo(...arguments);
        for (const row of rows) {
            if (row.progressBar) {
                row.progressBar.ratio_formatted = formatPercentage(row.progressBar.ratio / 100);
            }
        }
    }
}
