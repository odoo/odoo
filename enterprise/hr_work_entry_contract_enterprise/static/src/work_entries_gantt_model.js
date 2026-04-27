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
        const { globalStart, globalStop } = this._buildMetaData();
        return { start: globalStart, end: globalStop.minus({ millisecond: 1 }) };
    }

    /**
     * @protected
     * @override
     */
    async _fetchData(metaData) {
        const { globalStart } = metaData;
        if (globalStart <= DateTime.local().plus({ months: 1 })) {
            await this.generateWorkEntries();
        }
        return super._fetchData(...arguments);
    }
}
