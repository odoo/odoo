import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
const { DateTime } = luxon;

/**
 * This widget displays a small dropdown allowing users to reschedule the
 * selected activity to certain dates in the near future.
 */

// Version of the widget to use on mail.activity lists
class ActivityListRescheduleDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        ...standardWidgetProps,
    };
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        const today = DateTime.now().startOf("day");
        this.targetDays = {
            today: {
                displayDay: today.weekdayShort,
                actionName: "action_reschedule_today",
            },
            tomorrow: {
                displayDay: today.plus({ days: 1 }).weekdayShort,
                actionName: "action_reschedule_tomorrow",
            },
            nextWeek: {
                displayDay: today.plus({ weeks: 1 }).startOf("week").weekdayShort,
                actionName: "action_reschedule_nextweek",
            },
        };
    }
    static template = "mail.ActivityListRescheduleDropdown";

    async rescheduleActivity(click, actionName) {
        await this.action.doActionButton({
            type: "object",
            name: actionName,
            resModel: this.props.record.resModel,
            resId: this.props.record.resId,
            onClose: async () => {
                await this.props.record.model.root.load();
                this.props.record.model.notify();
            },
        });
        return this.props.record;
    }
}

// Version of the widget to use on lists of records inheriting from mail.activity.mixin
class ActivityMixinListRescheduleDropdown extends ActivityListRescheduleDropdown {
    setup() {
        super.setup();
        this.targetDays.today.actionName = "action_reschedule_my_next_today";
        this.targetDays.tomorrow.actionName = "action_reschedule_my_next_tomorrow";
        this.targetDays.nextWeek.actionName = "action_reschedule_my_next_nextweek";
    }
}

registry.category("view_widgets").add("activity_list_reschedule_dropdown", {
    component: ActivityListRescheduleDropdown,
    extractProps: ({ attrs }) => {
        const { readonly } = attrs;
        return {
            readonly,
        };
    },
});

registry.category("view_widgets").add("activity_mixin_list_reschedule_dropdown", {
    component: ActivityMixinListRescheduleDropdown,
    extractProps: ({ attrs }) => {
        const { readonly } = attrs;
        return {
            readonly,
        };
    },
});
