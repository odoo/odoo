import { Component, onWillStart, proxy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { deepEqual } from "@web/core/utils/objects";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    getDefaultValue,
    getEmptyFilterValue,
    isEmptyFilterValue,
} from "@spreadsheet/global_filters/helpers";
import { DashboardFilterList } from "../dashboard_filter_list/dashboard_filter_list";
import { DashboardCustomFavoriteItem } from "./dashboard_custom_favorite_item";
import { FACET_ICONS } from "@web/search/utils/misc";

/**
 * This component manages the state and behavior of the filter value list
 * and favorite filters in the dashboard search bar.
 */
export class DashboardSearchBarMenu extends Component {
    static template = "spreadsheet_dashboard.DashboardSearchBarMenu";
    static components = {
        CheckboxItem,
        DashboardCustomFavoriteItem,
        DashboardFilterList,
        DropdownItem,
    };

    static props = {
        close: Function,
        model: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.facet_icons = FACET_ICONS;
        this.actionService = useService("action");
        this.loader = useService("spreadsheet_dashboard_loader");
        this.searchModel = this.loader.getDashboard(this.loader.activeDashboardId).searchModel;
        this.sharedFavoritesExpanded = proxy({ value: false });
        this.state = proxy({
            filtersAndValues: this._computeFilterAndValues(),
        });
        onWillStart(async () => {
            this.searchableParentRelations = await this.fetchSearchableParentRelation();
        });
        // useLayoutEffect(
        //     () => {
        //         this.state.filtersAndValues = this._computeFilterAndValues();
        //     },
        //     () => [this.searchModel.activeFavoriteId]
        // );
    }

    _computeFilterAndValues() {
        return this.globalFilters.map((filter) => {
            const value =
                this.props.model.getters.getGlobalFilterValue(filter.id) ??
                getDefaultValue(filter.type);
            return {
                globalFilter: filter,
                value,
            };
        });
    }

    get globalFilters() {
        return this.props.model.getters.getGlobalFilters();
    }

    get favorites() {
        return this.searchModel.getFavoriteList((item) => item.userIds.length === 1);
    }

    get sharedFavorites() {
        const sharedFavorites = this.searchModel.getFavoriteList(
            (item) => item.userIds.length !== 1
        );

        if (sharedFavorites.length <= 4 || this.sharedFavoritesExpanded.value) {
            this.sharedFavoritesExpanded.value = true;
        } else {
            sharedFavorites.length = 3;
        }
        return sharedFavorites;
    }

    onFavoriteSelected(itemId) {
        this.searchModel.toggleFavorite(itemId);
    }

    editFavorite(itemId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "spreadsheet.dashboard.favorite.filters",
            views: [[false, "form"]],
            context: {
                form_view_ref:
                    "spreadsheet_dashboard.spreadsheet_dashboard_favorite_filters_view_edit_form",
            },
            res_id: itemId,
        });
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
        const filters = [];
        for (const node of this.state.filtersAndValues) {
            const { globalFilter, value } = node;
            const originalValue = this.props.model.getters.getGlobalFilterValue(globalFilter.id);
            const currentValue = isEmptyFilterValue(globalFilter, value) ? undefined : value;

            if (deepEqual(originalValue, currentValue)) {
                continue;
            }
            filters.push({
                filterId: globalFilter.id,
                value: currentValue,
            });
        }
        if (filters.length) {
            this.props.model.dispatch("SET_MANY_GLOBAL_FILTER_VALUE", { filters });
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
