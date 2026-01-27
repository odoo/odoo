import { Component, onWillStart, useState } from "@odoo/owl";
import {
    getDefaultValue,
    getEmptyFilterValue,
    isEmptyFilterValue,
} from "@spreadsheet/global_filters/helpers";
import { useService } from "@web/core/utils/hooks";
import { deepEqual } from "@web/core/utils/objects";
import { DashboardFilterList } from "../dashboard_filter_list/dashboard_filter_list";

/**
 * This component manages the state and behavior of the filter value list
 * in the dashboard search bar.
 */
export class DashboardSearchBarMenu extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBarMenu";
    static components = { DashboardFilterList };

    static props = {
        close: Function,
        model: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            filtersAndValues: this.globalFilters.map((globalFilter) => {
                const value = this.props.model.getters.getGlobalFilterValue(globalFilter.id);
                return {
                    globalFilter,
                    value: value ? { ...value } : getDefaultValue(globalFilter.type),
                };
            }),
        });
        onWillStart(async () => {
            this.searchableParentRelations = await this.fetchSearchableParentRelation();
        });
    }

    get globalFilters() {
        return this.props.model.getters.getGlobalFilters();
    }

    onFilterChange(filterId, value) {
        const node = this.state.filtersAndValues.find((f) => f.globalFilter.id === filterId);
        if (!node) {
            return;
        }
        if (value === undefined && node.value?.operator) {
            const emptyValue = getEmptyFilterValue(node.globalFilter, node.value.operator);
            node.value =
                typeof emptyValue === "object"
                    ? { ...emptyValue, operator: node.value.operator }
                    : emptyValue;
            return;
        }
        node.value = value;
    }

    onConfirm() {
        for (const node of this.state.filtersAndValues) {
            const { globalFilter, value } = node;
            const originalValue = this.props.model.getters.getGlobalFilterValue(globalFilter.id);

            if (deepEqual(originalValue, value)) {
                continue;
            }
            this.props.model.dispatch("SET_GLOBAL_FILTER_VALUE", {
                id: globalFilter.id,
                value: isEmptyFilterValue(globalFilter, value) ? undefined : value,
            });
        }
        this.props.close();
    }

    onDiscard() {
        this.props.close();
    }

    fetchSearchableParentRelation() {
        const models = this.globalFilters
            .filter((filter) => filter.type === "relation")
            .map((filter) => filter.modelName);
        return this.orm
            .cache({ type: "disk" })
            .call("ir.model", "has_searchable_parent_relation", [models]);
    }
}
