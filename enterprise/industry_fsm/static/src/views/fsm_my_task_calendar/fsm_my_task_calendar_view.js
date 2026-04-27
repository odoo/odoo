import { registry } from "@web/core/registry";
import { fsmTaskCalendarView } from "../fsm_task_calendar/fsm_calendar_view";
import { FsmMyTaskCalendarController } from "./fsm_my_task_calendar_controller";

export const fsmMyTaskCalendarView = {
    ...fsmTaskCalendarView,
    Controller: FsmMyTaskCalendarController,
};

registry.category("views").add("fsm_my_task_calendar", fsmMyTaskCalendarView);
