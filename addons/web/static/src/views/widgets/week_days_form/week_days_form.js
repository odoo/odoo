import { registry } from "@web/core/registry";
import { WeekDays, weekDays } from "@web/views/widgets/week_days/week_days";
import { useService } from "@web/core/utils/hooks";

export class WeekDaysForm extends WeekDays {
    static template = "web.WeekDaysForm";
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onChange(day) {
        this.props.record.update({ [day]: !this.data[day] });
    }
}

export const weekDaysForm = {
    component: WeekDaysForm,
    fieldDependencies: weekDays.fieldDependencies,
};

registry.category("view_widgets").add("week_days_form", weekDaysForm);
