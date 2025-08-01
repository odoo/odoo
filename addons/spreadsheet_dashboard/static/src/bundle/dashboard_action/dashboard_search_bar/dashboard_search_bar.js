import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DashboardDateFilter } from "../dashboard_date_filter/dashboard_date_filter";
import { FilterValuesList } from "@spreadsheet/global_filters/components/filter_values_list/filter_values_list";
import { getFacetInfo } from "@spreadsheet/global_filters/helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class DashboardSearchBar extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBar";
    static components = {
        DashboardFacet,
        DashboardDateFilter,
        FilterValuesList,
        Dropdown,
    };
    static props = { model: Object };

    setup() {
        this.facets = [];
        this.firstDateFilter = undefined;
        this.nameService = useService("name");

        this.filtersValuesDropdown = useDropdownState();
        onWillStart(this.computeState.bind(this));
        onWillUpdateProps(this.computeState.bind(this));
    }

    openFilterValueDropdown() {
        this.filtersValuesDropdown.open();
    }

    closeFilterValueDropdown() {
        this.filtersValuesDropdown.close();
    }

    toggleFilterValueDropdown() {
        this.filtersValuesDropdown.isOpen
            ? this.filtersValuesDropdown.close()
            : this.filtersValuesDropdown.open();
    }

    clearFilter(id) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id });
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
