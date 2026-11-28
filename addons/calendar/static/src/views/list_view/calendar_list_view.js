import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { browser } from "@web/core/browser/browser";
import { CaledarListController } from "./calendar_list_controller";

export class CalendarListModel extends listView.Model {
    setup(params) {
        super.setup(...arguments);
        const storedFilters = browser.sessionStorage.getItem("calendar_filters");
        this.calendarFilters =
            params.calendarFilters ?? (storedFilters && JSON.parse(storedFilters));
    }

    /**
     * @override
     * Add the calendar view's selected attendees to the list view's domain.
     */
    async load(params = {}) {
        const filters = this.calendarFilters;
        // Apply selected calendar attendees only when the action has no domain.
        if (filters && params.domain && !this.env.searchModel.globalDomain.length) {
            this.selectedPartnerIds ??= this.orm
                .cache({
                    type: "disk",
                    update: "always",
                    callback: (freshPartnerIds, hasChanged) => {
                        if (hasChanged) {
                            this.selectedPartnerIds = freshPartnerIds;
                            this.env.searchModel.search();
                        }
                    },
                })
                .call("res.users", "get_selected_calendars_partner_ids", [
                    [user.userId],
                    filters["user"],
                ]);
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
