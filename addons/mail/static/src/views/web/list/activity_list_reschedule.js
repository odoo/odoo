import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
const { DateTime } = luxon;


class ActivityListRescheduleDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        ...standardWidgetProps,
    };
    setup() {
        this.orm = useService("orm");
        const today = DateTime.now().startOf("day");
        this.targetDays = {
            today: {
                newDeadline: today,
                displayDay: today.weekdayShort,
            },
            tomorrow: {
                newDeadline: today.plus({days: 1}),
                displayDay: today.plus({days: 1}).weekdayShort,
            },
            nextWeek: {
                newDeadline: today.plus({weeks: 1}).startOf("week"),
                displayDay: today.plus({weeks: 1}).startOf("week").weekdayShort,
            }

        }
    }
    static template = "mail.ActivityListRescheduleDropdown";

    async rescheduleActivity(click, newDeadline) {
        await this.props.record.update({
            ["date_deadline"]: newDeadline,
        }, { save: true });
        return this.props.record;
    }
}

registry.category("view_widgets").add("activity_list_reschedule_dropdown", {
    component: ActivityListRescheduleDropdown,
    extractProps: ({ attrs }) => {
        const { readonly } = attrs;
        return {
            readonly,
        };
    }
});
