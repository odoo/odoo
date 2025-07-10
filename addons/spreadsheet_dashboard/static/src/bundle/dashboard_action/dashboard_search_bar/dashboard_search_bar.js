import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DashboardDateFilter } from "../dashboard_date_filter/dashboard_date_filter";
import { FiltersSearchDialog } from "@spreadsheet/global_filters/components/filters_search_dialog/filters_search_dialog";
import { getFacetInfo } from "@spreadsheet/global_filters/helpers";

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
        this.dialog.add(FiltersSearchDialog, {
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
        const filterValue = this.props.model.getters.getGlobalFilterValue(filter.id);
        return getFacetInfo(this.env, filter, filterValue);
    }
}
