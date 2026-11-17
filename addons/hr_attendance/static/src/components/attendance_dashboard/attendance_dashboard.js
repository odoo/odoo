import { Component, onWillStart, proxy, t, useOnChange, useProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";

/**
 * Clickable counters in the control panel of the attendance views, each toggling a filter of the
 * search view. A counter is shown when its filter exists in the search view. The counters are
 * those of the action's records (its domain), whatever the search. Not in My Attendances.
 *
 * The lists and kanbans pass their `list`, the other views their `model`: the counters reload
 * when its records change.
 */
export class AttendanceDashboard extends Component {
    static template = "hr_attendance.AttendanceDashboard";

    props = useProps({ list: t.any().optional(), model: t.any().optional() });

    setup() {
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        this.state = proxy({ counts: {}, activeFilterIds: [] });
        useBus(this.env.searchModel, "update", () => this.updateActiveFilters());
        if (this.props.list) {
            // reload when the records change, e.g. when they are reviewed from the list or the kanban
            useOnChange(
                () => [this.props.list, this.props.list.count, this.props.list.records.map((r) => r.data.state).join()],
                () => this.loadCounts(),
                { initialRun: false }
            );
        } else {
            useBus(this.props.model.bus, "update", () => this.loadCounts());
        }
        onWillStart(() => {
            this.updateActiveFilters();
            return this.loadCounts();
        });
    }

    get show() {
        return !this.env.searchModel.context.my_attendances;
    }

    get cards() {
        return [
            { key: "to_review", filter: "state_draft", label: _t("To Review") },
            { key: "at_work", filter: "nocheckout", label: _t("At Work") },
            { key: "late_check_in", filter: "late_check_in", label: _t("Late Clock In") },
            { key: "early_check_out", filter: "early_check_out", label: _t("Early Clock Out") },
            { key: "no_check_out", filter: "auto_check", label: _t("No Check-Out") },
            { key: "overtime", filter: "overtime", label: _t("Overtime") },
            { key: "undertime", filter: "undertime", label: _t("Undertime") },
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
        if (!this.show) {
            return;
        }
        const { searchModel } = this.env;
        const domain = new Domain(searchModel.globalDomain).toList(searchModel.domainEvalContext);
        this.state.counts = await this.keepLast.add(
            this.orm.call("hr.attendance", "get_attendance_dashboard_data", [domain])
        );
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
            // only one counter is active at a time
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
