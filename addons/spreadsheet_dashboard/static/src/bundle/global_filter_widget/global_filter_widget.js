import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { checkFilterValueIsValid } from "@spreadsheet/global_filters/helpers";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import {
    deserializeFavoriteFilters,
    serializeFavoriteFilters,
} from "../dashboard_action/dashboard_search_model";
import { DashboardFilterList } from "../dashboard_action/dashboard_filter_list/dashboard_filter_list";

export class GlobalFilterWidget extends Component {
    static template = "spreadsheet.GlobalFilterWidget";
    static components = { DashboardFilterList };
    static props = {
        ...standardFieldProps,
        dashboard: { type: String, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.loader = useService("spreadsheet_dashboard_loader");
        this.state = useState({
            model: null,
            filtersAndValues: [],
            searchableParentRelations: {},
            isLoading: false,
        });
        this.lastDashboardId = null;

        useRecordObserver(async (record) => {
            const dashboardId = record.data[this.props.dashboard]?.id;
            const globalFilters = record.data.global_filters || {};
            if (!dashboardId) {
                this._resetState();
                return;
            }
            if (dashboardId !== this.lastDashboardId) {
                this.lastDashboardId = dashboardId;
                await this._onDashboardChanged(dashboardId, globalFilters);
                return;
            }
            this._updateGlobalFilter(globalFilters);
        });
    }

    _resetState() {
        this.lastDashboardId = null;
        this.state.model = null;
        this.state.filtersAndValues = [];
        this.state.searchableParentRelations = {};
    }

    async _onDashboardChanged(dashboardId, globalFilters) {
        this.state.isLoading = true;
        const dashboard = this.loader.getDashboard(dashboardId);
        if (dashboard.promise) {
            await dashboard.promise;
        }

        this.state.model = dashboard.model;
        this.state.searchableParentRelations = this.fetchSearchableParentRelation();
        await this._updateGlobalFilter(globalFilters);
        this.state.isLoading = false;
    }

    async _updateGlobalFilter(globalFilters) {
        if (!this.state.model) {
            return;
        }

        this.state.filtersAndValues = deserializeFavoriteFilters(
            this.state.model.getters,
            globalFilters
        );
    }

    onFilterChange(filterId, value) {
        const node = this.state.filtersAndValues.find((f) => f.globalFilter.id === filterId);
        if (!node) {
            return;
        }
        node.value = value;
        if (!value || checkFilterValueIsValid(node.globalFilter, node.value)) {
            const global_filters = serializeFavoriteFilters(this.state.filtersAndValues);
            this.props.record.update({ global_filters });
        }
    }

    fetchSearchableParentRelation() {
        const models = this.state.model.getters
            .getGlobalFilters()
            .filter((f) => f.type === "relation")
            .map((f) => f.modelName);
        return this.orm
            .cache({ type: "disk" })
            .call("ir.model", "has_searchable_parent_relation", [models]);
    }
}
