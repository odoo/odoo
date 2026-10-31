import { Component, onWillStart, proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";

/**
 * Clickable counters above the attendance lists and kanbans, each toggling a filter of the
 * search view. A counter is shown when its filter exists in the search view.
 */
export class AttendanceDashboard extends Component {
    static template = "hr_attendance.AttendanceDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ counts: {}, activeFilterIds: [] });
        useBus(this.env.searchModel, "update", () => {
            this.updateActiveFilters();
            this.loadCounts();
        });
        onWillStart(() => {
            this.updateActiveFilters();
            return this.loadCounts();
        });
    }

    get cards() {
        return [
            { key: "to_review", filter: "state_draft", label: _t("To Review") },
            { key: "at_work", filter: "nocheckout", label: _t("At Work") },
            { key: "late_check_in", filter: "late_check_in", label: _t("Late Clock In") },
            { key: "early_check_out", filter: "early_check_out", label: _t("Early Clock Out") },
            { key: "overtime", filter: "overtime", label: _t("Overtime") },
        ]
            .map((card) => ({
                ...card,
                searchItem: this.env.searchModel.getSearchItems(
                    (item) => item.type === "filter" && item.name === card.filter
                )[0],
            }))
            .filter((card) => card.searchItem);
    }

    async loadCounts() {
        this.state.counts = await this.orm.call("hr.attendance", "get_attendance_dashboard_data");
    }

    updateActiveFilters() {
        this.state.activeFilterIds = this.env.searchModel
            .getSearchItems((item) => item.isActive)
            .map((item) => item.id);
    }

    isActive(card) {
        return this.state.activeFilterIds.includes(card.searchItem.id);
    }

    onCardClick(card) {
        const { searchModel } = this.env;
        if (!this.isActive(card)) {
            // one counter at a time: drop the filters of the other counters
            const cardItemIds = new Set(this.cards.map((c) => c.searchItem.id));
            for (let index = searchModel.query.length - 1; index >= 0; index--) {
                if (cardItemIds.has(searchModel.query[index].searchItemId)) {
                    searchModel.query.splice(index, 1);
                }
            }
        }
        searchModel.toggleSearchItem(card.searchItem.id);
    }
}
