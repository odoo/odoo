import { _t } from "@web/core/l10n/translation";
import { HrGanttRenderer } from "@hr_gantt/hr_gantt_renderer";
import { hrGanttView } from "@hr_gantt/hr_gantt_view";
import { registry } from "@web/core/registry";
import { GanttController } from "@web_gantt/gantt_controller";

export class HrHolidaysGanttRenderer extends HrGanttRenderer {
    static components = {
        ...HrGanttRenderer.components,
    };
    static pillTemplate = "hr_holidays_gantt.GanttRenderer.Pill";
}

export class HrHolidaysGanttController extends GanttController {
     /**
      * @override
      */
     openDialog(props, options) {
        super.openDialog({
            ...props,
            title: _t("Time Off Request"),
            size: "md",
        }, options);
    }
}

export const hrHolidaysGanttView = {
    ...hrGanttView,
    Renderer: HrHolidaysGanttRenderer,
    Controller: HrHolidaysGanttController,
};

registry.category("views").add("hr_holidays_gantt", hrHolidaysGanttView);
