import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";

export class ProjectCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        footer: "project.ProjectCalendarCommonPopover.footer",
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    async onClickViewTasks() {
        return this.actionService.doAction("project.act_project_project_2_project_task_all", {
            additionalContext: {
                active_id: this.props.record.id,
            },
        });
    }
}
