import { listView } from "@web/views/list/list_view";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { SearchModel } from "@web/search/search_model";
import { CaledarListController } from "./calendar_list_controller";

export class CalendarListSearchModel extends SearchModel {
    /**
     * @override
     * Applies Calendar's active attendees as a filter
     */
    async load(config = {}) {
        const filters = user.context.calendar_filters;
        this.calendarAttendeeQueryElement = null;
        await super.load(config);

        if (filters && !filters["all"]) {
            const selectedPartners = await this.orm.call(
                "res.users",
                "get_selected_calendars_partners",
                [[user.userId], filters["user"]]
            );
            const selectedPartnerIds = selectedPartners.map((partner) => partner.id);
            if (selectedPartnerIds.length) {
                const searchItem = Object.values(this.searchItems).find(
                    (item) => item.fieldName === "partner_ids"
                );
                if (searchItem) {
                    this.addAutoCompletionValues(searchItem.id, {
                        label: selectedPartners
                            .map((partner) => partner.display_name)
                            .join(` ${_t("or")} `),
                        operator: "in",
                        value: selectedPartnerIds,
                    });
                    this.calendarAttendeeQueryElement = this.query.find(
                        (queryElement) =>
                            queryElement.searchItemId === searchItem.id &&
                            queryElement.autocompleteValue?.value === selectedPartnerIds
                    );
                    if (this.calendarAttendeeQueryElement) {
                        this.query = [
                            this.calendarAttendeeQueryElement,
                            ...this.query.filter(
                                (queryElement) => queryElement !== this.calendarAttendeeQueryElement
                            ),
                        ];
                    }
                }
            }
        }
    }

    /**
     * @override
     * Do not transfer the Calendar attendee filter to another view.
     */
    exportState() {
        const state = super.exportState();
        if (this.calendarAttendeeQueryElement) {
            state.query = state.query.filter(
                (queryElement) => queryElement !== this.calendarAttendeeQueryElement
            );
        }
        return state;
    }
}

export const CalendarListView = {
    ...listView,
    SearchModel: CalendarListSearchModel,
    Controller: CaledarListController,
};

registry.category("views").add("calendar_list_view", CalendarListView);
