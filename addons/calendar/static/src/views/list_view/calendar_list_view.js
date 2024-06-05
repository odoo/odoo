import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class CalendarListModel extends listView.Model {
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        super.setup(...arguments);
    }

    /**
    * @override
    * Add the calendar view's selected attendees to the list view's domain.
    */
    async load(params = {}) {
        const filters = params?.context?.calendar_filters;
        const emptyDomain = Array.isArray(params?.domain) && params.domain.length == 0;
        if (filters && emptyDomain) {
            const selectedPartnerIds = await this.orm.call(
                "res.users",
                "get_selected_calendars_partner_ids",
                [[user.userId], filters["user"]]
            );
            // Filter attendees to be shown if 'everybody' filter isn't active.
            if (!filters["all"])
                params.domain.push(["partner_ids", "in", selectedPartnerIds]);
        }
        return super.load(params);
    }
}

export const CalendarListView = {
    ...listView,
    Model: CalendarListModel,
};

function _mockGetCalendarPartnerIds(params) {
    /* Mock function for when there aren't records to be shown. */
    return [];
}

registry.category("views").add("calendar_list_view", CalendarListView);
registry.category("sample_server").add("get_selected_calendars_partner_ids", _mockGetCalendarPartnerIds);
