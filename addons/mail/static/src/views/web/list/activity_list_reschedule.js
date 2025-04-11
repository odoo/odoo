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
    }
    static template = "mail.ActivityListRescheduleDropdown";

    async rescheduleActivity(click, newDate) {
        const today = DateTime.now().startOf("day");
        let newDeadline;
        switch (newDate) {
            case "today":
                newDeadline = today;
                break;
            case "tomorrow":
                newDeadline = today.plus({days: 1});
                break;
            default:
                newDeadline = today.plus({weeks: 1}).startOf("week")
        }
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
