import { patch } from "@web/core/utils/patch";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

export function patchCommonRenderer(CommonRenderer) {
    patch(CommonRenderer.prototype, {
        eventClassNames(info) {
            const classesToAdd = super.eventClassNames(info);
            const { event } = info;
            const record = this.props.model.records[event.id];
            if (record) {
                const { state, is_closed } = record.rawRecord;
                const isTaskClosed = is_closed !== undefined ? is_closed : ['1_done', '1_canceled'].includes(state);
                if (isTaskClosed) {
                    classesToAdd.push("o_past_event");
                }
            }
            return classesToAdd;
        },
    });
}

export class ProjectTaskCalendarCommonRenderer extends CalendarCommonRenderer {
    static template = "project.ProjectTaskCalendarCommonRenderer";
}
patchCommonRenderer(ProjectTaskCalendarCommonRenderer);
