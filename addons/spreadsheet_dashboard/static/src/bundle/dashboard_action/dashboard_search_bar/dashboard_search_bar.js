import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService } from "@web/core/utils/hooks";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { QUARTER_OPTIONS } from "@web/search/utils/dates";
import { _t } from "@web/core/l10n/translation";
import { DashboardSearchDialog } from "../dashboard_search_dialog/dashboard_search_dialog";

const { DateTime } = luxon;

export class DashboardSearchBar extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBar";
    static components = {
        DashboardFacet,
    };
    static props = { model: Object };

    setup() {
        this.facets = [];
        this.nameService = useService("name");
        this.dialog = useService("dialog");

        this.searchBarDropdownState = useDropdownState();
        onWillStart(this.computeFacets.bind(this));
        onWillUpdateProps(this.computeFacets.bind(this));
    }

    get filters() {
        return this.props.model.getters.getGlobalFilters();
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

    async computeFacets() {
        const filters = this.filters.filter((filter) =>
            this.props.model.getters.isGlobalFilterActive(filter.id)
        );
        this.facets = await Promise.all(filters.map((filter) => this.getFacetFor(filter)));
    }

    async getFacetFor(filter) {
        const filterValues = this.props.model.getters.getGlobalFilterValue(filter.id);
        let values;
        let separator = _t("or");
        switch (filter.type) {
            case "boolean":
            case "text":
                values = [filterValues];
                break;
            case "date": {
                if (!filterValues) {
                    throw new Error("Should be defined at this point");
                }
                if (filter.rangeType === "from_to") {
                    const from = filterValues.from;
                    const to = filterValues.to;
                    values = [from, to];
                    separator = _t("to");
                    break;
                }
                if (typeof filterValues === "string") {
                    values = [
                        RELATIVE_DATE_RANGE_TYPES.find((type) => type.type === filterValues)
                            .description,
                    ];
                    break;
                }
                if (filterValues?.year === undefined) {
                    values = [""];
                    break;
                }
                const year = String(filterValues.year);
                switch (filterValues.type) {
                    case "year":
                        values = [year];
                        break;
                    case "month": {
                        const month = DateTime.local()
                            .set({ month: filterValues.month })
                            .toFormat("LLLL");
                        values = [`${month} ${year}`];
                        break;
                    }
                    case "quarter": {
                        const quarter = QUARTER_OPTIONS[filterValues.quarter];
                        if (quarter) {
                            values = [`${quarter.description} ${year}`];
                        } else {
                            values = [year];
                        }
                    }
                }
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
