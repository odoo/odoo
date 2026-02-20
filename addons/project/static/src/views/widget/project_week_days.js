import { registry } from "@web/core/registry";
import { WeekDays, weekDays } from "@web/views/widgets/week_days/week_days";

export class ProjectWeekDays extends WeekDays {
    static template = "project.WeekDays";
    onChange(day) {
        this.props.record.update({ [day]: !this.data[day] });
    }
};

export const projectWeekDays = {
    component: ProjectWeekDays,
    fieldDependencies: weekDays.fieldDependencies,
};

registry.category("view_widgets").add("project_week_days", projectWeekDays);
