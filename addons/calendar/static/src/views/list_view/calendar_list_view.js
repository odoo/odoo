import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { CaledarListController } from "./calendar_list_controller";

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
        // Apply selected calendar attendees only when the action has no domain.
        if (filters && params.domain && !this.env.searchModel.globalDomain.length) {
            this.selectedPartnerIds ??= this.orm.call(
                "res.users",
                "get_selected_calendars_partner_ids",
                [[user.userId], filters["user"]]
            );
            params = {
                ...params,
                domain: [...params.domain, ["partner_ids", "in", await this.selectedPartnerIds]],
            };
        }
        return super.load(params);
    }
}

export const CalendarListView = {
    ...listView,
    Model: CalendarListModel,
    Controller: CaledarListController,
};

function _mockGetCalendarPartnerIds(params) {
    /* Mock function for when there aren't records to be shown. */
    return [];
}

registry.category("views").add("calendar_list_view", CalendarListView);
registry
    .category("sample_server")
    .add("get_selected_calendars_partner_ids", _mockGetCalendarPartnerIds);
