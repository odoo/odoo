import { GanttController } from "@web_gantt/gantt_controller";
import { useWorkEntry } from "@hr_work_entry_contract/views/work_entry_hook";
const { DateTime } = luxon;

export class WorkEntriesGanttController extends GanttController {
    setup() {
        super.setup(...arguments);
        const { onRegenerateWorkEntries } = useWorkEntry({
            getEmployeeIds: () => {
                const { rows } = this.model.data;
                if (rows.length === 1) {
                    const { groupedByField, resId } = rows[0];
                    if (groupedByField === "employee_id" && Boolean(resId)) {
                        return [resId];
                    }
                }
                return [];
            },
            getRange: () => this.model.getRange(),
            onClose: () => this.model.fetchData({}),
        });
        this.onRegenerateWorkEntries = onRegenerateWorkEntries;
    }

    openDialog(props, options = {}) {
        if (!props.resId) {
            // Add a day to the start date unless it is already the same as the stop date
            const startDate = new Date(props['context']['default_date_start']);
            const stopDate = new Date(props['context']['default_date_stop']);
            if (startDate.getDate() !== stopDate.getDate() || startDate.getMonth() !== stopDate.getMonth()) {
                startDate.setDate(startDate.getDate() + 1);
            }
            startDate.setHours(9,0,0);
            props['context']['default_date_start'] = startDate.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
            stopDate.setHours(17,0,0);
            props['context']['default_date_stop'] = stopDate.toISOString().replace(/T|Z/g, ' ').trim().substring(0, 19);
        }

        super.openDialog(...arguments);
    }

    onAddClicked() {
        const { scale, globalStart, globalStop } = this.model.metaData;
        const today = DateTime.local().startOf("day");
        if (scale.unit !== "day" && globalStart <= today.endOf("day") && today <= globalStop.minus({ millisecond: 1 })) {
            let start;
            let stop;
            if (["week", "month"].includes(scale.unit)) {
                start = today.set({ hours: 9, minutes: 0, seconds: 0 });
                stop = today.set({ hours: 17, minutes: 0, seconds: 0 });
            } else {
                start = today.startOf(scale.interval);
                stop = today.endOf(scale.interval);
            }
            const context = this.model.getDialogContext({ start, stop, withDefault: true });
            this.create(context);
            return;
        }
        super.onAddClicked(...arguments);
    }
}
