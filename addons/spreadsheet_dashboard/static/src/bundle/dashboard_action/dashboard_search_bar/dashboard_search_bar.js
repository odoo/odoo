import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { DashboardSearchDialog } from "../dashboard_search_dialog/dashboard_search_dialog";
import { dateFilterValueToString } from "@spreadsheet/global_filters/helpers";
import { DashboardDateFilter } from "../dashboard_date_filter/dashboard_date_filter";

export class DashboardSearchBar extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBar";
    static components = {
        DashboardFacet,
        DashboardDateFilter,
    };
    static props = { model: Object };

    setup() {
        this.facets = [];
        this.firstDateFilter = undefined;
        this.nameService = useService("name");
        this.dialog = useService("dialog");

        this.searchBarDropdownState = useDropdownState();
        onWillStart(this.computeState.bind(this));
        onWillUpdateProps(this.computeState.bind(this));
    }

    openDialog() {
        this.dialog.add(DashboardSearchDialog, {
            model: this.props.model,
        });
    }

    clearFilter(id) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id });
    }

    onFacetClick() {
        this.searchBarDropdownState.open();
    }

    updateFirstDateFilter(value) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id: this.firstDateFilter.id,
            value,
        });
    }

    get firstDateFilterValue() {
        if (!this.firstDateFilter) {
            return undefined;
        }
        return this.props.model.getters.getGlobalFilterValue(this.firstDateFilter.id);
    }

    async computeState() {
        const filters = this.props.model.getters.getGlobalFilters();
        const firstDateFilterIndex = filters.findIndex((filter) => filter.type === "date");
        if (firstDateFilterIndex !== -1) {
            this.firstDateFilter = filters.splice(firstDateFilterIndex, 1)[0];
        }
        this.facets = await Promise.all(
            filters
                .filter((filter) => this.props.model.getters.isGlobalFilterActive(filter.id))
                .map((filter) => this.getFacetFor(filter))
        );
    }

    async getFacetFor(filter) {
        const filterValues = this.props.model.getters.getGlobalFilterValue(filter.id);
        let values;
        const separator = _t("or");
        switch (filter.type) {
            case "boolean":
            case "text":
                values = [filterValues];
                break;
            case "date": {
                if (!filterValues) {
                    throw new Error("Should be defined at this point");
                }
                values = [dateFilterValueToString(filterValues)];
                break;
            }
            case "relation":
                values = await this.nameService.loadDisplayNames(filter.modelName, filterValues);
                values = Object.values(values);
                break;
        }
        return {
            title: filter.label,
            values,
            id: filter.id,
            separator,
        };
    }
}
