import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { Status } from "./dashboard_loader_service";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { useSetupAction } from "@web/search/action_hook";
import { DashboardMobileSearchPanel } from "./mobile_search_panel/mobile_search_panel";
import { MobileFigureContainer } from "./mobile_figure_container/mobile_figure_container";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { SpreadsheetShareButton } from "@spreadsheet/components/share_button/share_button";
import { useSpreadsheetPrint } from "@spreadsheet/hooks";
import { Registry } from "@odoo/o-spreadsheet";
import { router } from "@web/core/browser/router";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";

import { Component, onWillStart, useState, useEffect } from "@odoo/owl";
import { DashboardSearchBar } from "./dashboard_search_bar/dashboard_search_bar";

export const dashboardActionRegistry = new Registry();

export class SpreadsheetDashboardAction extends Component {
    static template = "spreadsheet_dashboard.DashboardAction";
    static path = "dashboards";
    static components = {
        ControlPanel,
        SpreadsheetComponent,
        DashboardMobileSearchPanel,
        MobileFigureContainer,
        SpreadsheetShareButton,
        DashboardSearchBar,
    };
    static props = { ...standardActionServiceProps };
    static displayName = _t("Dashboards");

    setup() {
        this.Status = Status;
        this.controlPanelDisplay = {};
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.loader = useService("spreadsheet_dashboard_loader");
        onWillStart(async () => {
            if (this.props.state && this.props.state.dashboardLoader) {
                const state = this.props.state.dashboardLoader;
                this.loader.restoreFromState(state);
            } else {
                await this.loader.load();
            }
            const activeDashboardId = this.getInitialActiveDashboard();
            if (activeDashboardId) {
                this.openDashboard(activeDashboardId);
            }
        });
        useEffect(
            () => router.pushState({ dashboard_id: this.activeDashboardId }),
            () => [this.activeDashboardId]
        );
        useEffect(
            () => {
                const dashboard = this.loader.getActiveDashboard();
                if (dashboard && dashboard.status === Status.Loaded) {
                    const render = () => this.render(true);
                    dashboard.model.on("update", this, render);
                    return () => dashboard.model.off("update", this, render);
                }
            },
            () => {
                const dashboard = this.loader.getActiveDashboard();
                return [dashboard?.model, dashboard?.status];
            }
        );
        useSetupAction({
            getLocalState: () => ({
                dashboardLoader: this.loader.getState(),
            }),
        });
        useSpreadsheetPrint(() => this.loader.getActiveDashboard()?.model);
        /** @type {{ sidebarExpanded: boolean}} */
        this.state = useState({ sidebarExpanded: true });
        this.searchBarToggler = useSearchBarToggler();
    }

    get dashboardButton() {
        return dashboardActionRegistry.getAll()[0];
    }

    /**
     * @returns {number | undefined}
     */
    get activeDashboardId() {
        return this.loader.getActiveDashboard()
            ? this.loader.getActiveDashboard().data.id
            : undefined;
    }

    /**
     * @returns {object[]}
     */
    get filters() {
        const dashboard = this.loader.getActiveDashboard();
        if (!dashboard || dashboard.status !== Status.Loaded) {
            return [];
        }
        return dashboard.model.getters.getGlobalFilters();
    }

    setGlobalFilterValue(id, value, displayNames) {
        this.loader.getActiveDashboard().model.dispatch("SET_GLOBAL_FILTER_VALUE", {
            id,
            value,
            displayNames,
        });
    }

    /**
     * @private
     * @returns {number | undefined}
     */
    getInitialActiveDashboard() {
        const activeDashboardId = this.props.state?.dashboardLoader?.activeDashboardId;
        if (activeDashboardId) {
            return activeDashboardId;
        }
        const params = this.props.action.params;
        if (params && params.dashboard_id) {
            return params.dashboard_id;
        }
        const [firstSection] = this.getDashboardGroups();
        if (firstSection && firstSection.dashboards.length) {
            return firstSection.dashboards[0].data.id;
        }
    }

    getDashboardGroups() {
        return this.loader.getDashboardGroups();
    }

    /**
     * @param {number} dashboardId
     */
    openDashboard(dashboardId) {
        this.loader.activateDashboard(dashboardId);
    }

    /**
     * @param {number} id - The ID of the dashboard to be edited.
     * @returns {Promise<void>}
     */
    async editDashboard(id) {
        const action = await this.env.services.orm.call(
            "spreadsheet.dashboard",
            "action_edit_dashboard",
            [id]
        );
        this.actionService.doAction(action);
    }

    async shareSpreadsheet(data, excelExport) {
        const url = await this.orm.call("spreadsheet.dashboard.share", "action_get_share_url", [
            {
                dashboard_id: this.activeDashboardId,
                spreadsheet_data: JSON.stringify(data),
                excel_files: excelExport.files,
            },
        ]);
        return url;
    }

    async toggleFavorite() {
        if (!this.loader.getActiveDashboard()) {
            return;
        }
        const { id, is_favorite } = this.loader.getActiveDashboard().data;
        await this.orm.call("spreadsheet.dashboard", "action_toggle_favorite", [id]);
        this.loader.getActiveDashboard().data.is_favorite = !is_favorite;
    }

    toggleSidebar() {
        this.state.sidebarExpanded = !this.state.sidebarExpanded;
    }

    get activeDashboardGroupName() {
        return this.getDashboardGroups().find(
            (group) =>
                group.id !== "favorites" && // Skip the FAVORITES group
                group.dashboards.some(({ data }) => data.id === this.activeDashboardId)
        )?.name;
    }
}

registry
    .category("actions")
    .add("action_spreadsheet_dashboard", SpreadsheetDashboardAction, { force: true });
