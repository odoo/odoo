/* @odoo-module */

import { GanttModel } from "@web_gantt/gantt_model";
import { useWorkEntry } from "@hr_work_entry_contract/views/work_entry_hook";

const { DateTime } = luxon;

export class WorkEntriesGanttModel extends GanttModel {
    /**
     * @override
     */
    setup() {
        super.setup(...arguments);
        const { generateWorkEntries } = useWorkEntry({ getRange: () => this.getRange() });
        this.generateWorkEntries = generateWorkEntries;
    }

    getRange() {
        const { startDate, stopDate } = this._buildMetaData();
        return { start: startDate, end: stopDate };
    }

    /**
     * @protected
     * @override
     */
    async _fetchData(metaData) {
        const { startDate } = metaData;
        if (startDate <= DateTime.local().plus({ months: 1 })) {
            await this.generateWorkEntries();
        }
        return super._fetchData(...arguments);
    }
}
