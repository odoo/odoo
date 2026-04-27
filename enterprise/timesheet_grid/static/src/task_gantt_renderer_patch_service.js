import { patch } from "@web/core/utils/patch";
import { TaskGanttRenderer } from "@project_enterprise/views/task_gantt/task_gantt_renderer";
import { useService } from "@web/core/utils/hooks";

patch(TaskGanttRenderer.prototype, {
    setup() {
        super.setup();
        this.timesheetUOMService = useService("timesheet_uom");
    },
    getPopoverProps(pill) {
        const props = super.getPopoverProps(...arguments);
        const ctx = props.context;
        const { record } = pill;
        const formatter = this.timesheetUOMService.formatter;
        ctx.total_hours_spent_formatted = formatter(record.total_hours_spent);
        ctx.progressFormatted = Math.round(record.progress * 100);
        return props;
    },
});
