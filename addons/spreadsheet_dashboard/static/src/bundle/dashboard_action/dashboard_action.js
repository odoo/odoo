/** @odoo-module */

import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { DashboardLoader, Status } from "./dashboard_loader";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import { DashboardMobileSearchPanel } from "./mobile_search_panel/mobile_search_panel";
import { MobileFigureContainer } from "./mobile_figure_container/mobile_figure_container";
import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { loadSpreadsheetDependencies } from "@spreadsheet/helpers/helpers";
import { useService } from "@web/core/utils/hooks";

const { Spreadsheet } = spreadsheet;
const { Component, onWillStart, useState, useEffect } = owl;

export class SpreadsheetDashboardAction extends Component {
    setup() {
        this.Status = Status;
        this.controlPanelDisplay = {
            "top-left": true,
            "top-right": true,
            "bottom-left": false,
            "bottom-right": false,
        };
        this.orm = useService("orm");
        this.router = useService("router");
        // Use the non-protected orm service (`this.env.services.orm` instead of `useService("orm")`)
        // because spreadsheets models are preserved across multiple components when navigating
        // with the breadcrumb
        // TODO write a test
        /** @type {DashboardLoader}*/
        this.loader = useState(
            new DashboardLoader(this.env, this.env.services.orm, this._fetchDashboardData)
        );
        onWillStart(async () => {
            await loadSpreadsheetDependencies();
            if (this.props.state && this.props.state.dashboardLoader) {
                const { groups, dashboards } = this.props.state.dashboardLoader;
                this.loader.restoreFromState(groups, dashboards);
            } else {
                await this.loader.load();
            }
            const activeDashboardId = this.getInitialActiveDashboard();
            if (activeDashboardId) {
                this.openDashboard(activeDashboardId);
            }
        });
        useEffect(
            () => this.router.pushState({ dashboard_id: this.activeDashboardId }),
            () => [this.activeDashboardId]
        );
        useEffect(
            () => {
                const dashboard = this.state.activeDashboard;
                if (dashboard && dashboard.status === Status.Loaded) {
                    const render = () => this.render(true);
                    dashboard.model.on("update", this, render);
                    return () => dashboard.model.off("update", this, render);
                }
            },
            () => {
                const dashboard = this.state.activeDashboard;
                return [dashboard && dashboard.model, dashboard && dashboard.status];
            }
        );
        useSetupAction({
            getLocalState: () => {
                return {
                    activeDashboardId: this.activeDashboardId,
                    dashboardLoader: this.loader.getState(),
                };
            },
        });
        /** @type {{ activeDashboard: import("./dashboard_loader").Dashboard}} */
        this.state = useState({ activeDashboard: undefined });
    }

    /**
     * @returns {number | undefined}
     */
    get activeDashboardId() {
        return this.state.activeDashboard ? this.state.activeDashboard.id : undefined;
    }

    /**
     * @returns {object[]}
     */
    get filters() {
        const dashboard = this.state.activeDashboard;
        if (!dashboard || dashboard.status !== Status.Loaded) {
            return [];
        }
        return dashboard.model.getters.getGlobalFilters();
    }

    /**
     * @private
     * @returns {number | undefined}
     */
    getInitialActiveDashboard() {
        if (this.props.state && this.props.state.activeDashboardId) {
            return this.props.state.activeDashboardId;
        }
        const params = this.props.action.params || this.props.action.context.params;
        if (params && params.dashboard_id) {
            return params.dashboard_id;
        }
        const [firstSection] = this.getDashboardGroups();
        if (firstSection && firstSection.dashboards.length) {
            return firstSection.dashboards[0].id;
        }
    }

    getDashboardGroups() {
        return this.loader.getDashboardGroups();
    }

    /**
     * @param {number} dashboardId
     */
    openDashboard(dashboardId) {
        this.state.activeDashboard = this.loader.getDashboard(dashboardId);
    }

    /**
     * @private
     * @param {number} dashboardId
     * @returns {Promise<{ data: string, revisions: object[] }>}
     */
    async _fetchDashboardData(dashboardId) {
        const [record] = await this.orm.read("spreadsheet.dashboard", [dashboardId], ["raw"]);
        return { data: record.raw, revisions: [] };
    }
}
SpreadsheetDashboardAction.template = "spreadsheet_dashboard.DashboardAction";
SpreadsheetDashboardAction.components = {
    ControlPanel,
    Spreadsheet,
    FilterValue,
    DashboardMobileSearchPanel,
    MobileFigureContainer,
};

registry
    .category("actions")
    .add("action_spreadsheet_dashboard", SpreadsheetDashboardAction, { force: true });
