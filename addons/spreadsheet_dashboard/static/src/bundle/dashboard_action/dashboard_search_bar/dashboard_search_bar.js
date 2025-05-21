import { Component, onWillUpdateProps, onWillStart } from "@odoo/owl";
import { DashboardFacet } from "../dashboard_facet/dashboard_facet";
import { useService } from "@web/core/utils/hooks";
import { RELATIVE_DATE_RANGE_TYPES } from "@spreadsheet/helpers/constants";
import { QUARTER_OPTIONS } from "@web/search/utils/dates";
import { _t } from "@web/core/l10n/translation";
import { monthsOptions } from "@spreadsheet/assets_backend/constants";

const { DateTime } = luxon;

export class DashboardSearchBar extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBar";
    static components = {
        DashboardFacet,
    };
    static props = { filters: Object, model: Object, toggleFilterPanel: Function };

    setup() {
        this.facets = [];
        this.nameService = useService("name");

        onWillStart(this.computeFacets.bind(this));
        onWillUpdateProps(this.computeFacets.bind(this));
    }

    clearFilter(id) {
        this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", { id });
    }

    openSidePanel() {
        this.props.toggleFilterPanel();
    }

    async computeFacets() {
        const filters = this.props.filters.filter((filter) =>
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
                if (filterValues.yearOffset === undefined) {
                    values = [""];
                    break;
                }
                const year = String(DateTime.local().year + filterValues.yearOffset);
                const period = QUARTER_OPTIONS[filterValues.period];
                if (period) {
                    values = [
                        _t("%(quarter)s %(year)s", {
                            quarter: period.description,
                            year,
                        }),
                    ];
                } else {
                    values = [
                        _t("%(month)s %(year)s", {
                            month: monthsOptions.find((mo) => mo.id === filterValues.period)
                                .description,
                            year,
                        }),
                    ];
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
