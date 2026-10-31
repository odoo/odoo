import { Registry } from "@odoo/o-spreadsheet";
import {
    Component,
    computed,
    onWillStart,
    proxy,
    signal,
    useEffect,
    useListener,
    useProps,
} from "@odoo/owl";
import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetShareButton } from "@spreadsheet/components/share_button/share_button";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { render } from "@web/owl2/utils";
import { useSetupAction } from "@web/search/action_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { Status } from "./dashboard_loader_service";
import { DashboardSearchBar } from "./dashboard_search_bar/dashboard_search_bar";
import { MobileFigureContainer } from "./mobile_figure_container/mobile_figure_container";
import { DashboardMobileSearchPanel } from "./mobile_search_panel/mobile_search_panel";

const GRID_SCROLLBAR_SELECTOR = ".o-dashboard-grid > .o-scrollbar.vertical";

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
    static displayName = _t("Dashboards");

    props = useProps(standardActionServiceProps);

    rendererRef = signal.ref();

    activeDashboardId = computed(() => this.loader.activeDashboardId);
    dashboard = computed(() => {
        const id = this.activeDashboardId();
        return id ? this.loader.getDashboard(id) : undefined;
    });

    setup() {
        this.Status = Status;
        this.controlPanelDisplay = {};
        this.orm = useService("orm");
        this.uiService = useService("ui");
        this.actionService = useService("action");
        this.loader = useService("spreadsheet_dashboard_loader");
        /** @type {{ sidebarExpanded: boolean, isScrolled: boolean}} */
        this.state = proxy({ sidebarExpanded: true, isScrolled: false });
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
        useEffect(() => {
            const dashboard = this.dashboard();
            if (dashboard && dashboard.status === Status.Loaded) {
                const onUpdate = () => render(this, true);
                dashboard.model.on("update", this, onUpdate);
                return () => dashboard.model.off("update", this, onUpdate);
            }
        });
        useEffect(() => {
            const renderer = this.rendererRef();
            if (!renderer) {
                return;
            }
            const observer = new ResizeObserver(() => this.scheduleIsScrolledUpdate());
            observer.observe(renderer);
            return () => {
                observer.disconnect();
                this.cancelIsScrolledUpdate();
            };
        });
        useListener(this.rendererRef, "scroll", this.onGridScroll.bind(this), { capture: true });
        useListener(window, "afterprint", this.logExport.bind(this));

        useSetupAction({
            getLocalState: () => ({
                dashboardLoader: this.loader.getState(),
            }),
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    get dashboardButton() {
        return dashboardActionRegistry.getAll()[0];
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
        this.props.updateActionState({ dashboard_id: dashboardId });
        this.cancelIsScrolledUpdate();
        this.state.isScrolled = false;
    }

    scheduleIsScrolledUpdate() {
        if (this.isScrolledFrame) {
            return;
        }
        this.isScrolledFrame = requestAnimationFrame(() => {
            this.isScrolledFrame = undefined;
            this.updateIsScrolled();
        });
    }

    cancelIsScrolledUpdate() {
        if (this.isScrolledFrame) {
            cancelAnimationFrame(this.isScrolledFrame);
            this.isScrolledFrame = undefined;
        }
    }

    updateIsScrolled() {
        const scrollbar = this.rendererRef()?.querySelector(GRID_SCROLLBAR_SELECTOR);
        this.state.isScrolled = !!scrollbar && scrollbar.scrollTop > 0;
    }

    /**
     * @param {Event} ev
     */
    onGridScroll(ev) {
        if (ev.target.matches?.(GRID_SCROLLBAR_SELECTOR)) {
            this.scheduleIsScrolledUpdate();
        }
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
                dashboard_id: this.activeDashboardId(),
                spreadsheet_data: JSON.stringify(data),
                excel_files: excelExport.files,
            },
        ]);
        return url;
    }

    async toggleFavorite() {
        const dashboard = this.dashboard();
        if (!dashboard) {
            return;
        }
        const { id, is_favorite } = dashboard.data;
        await this.orm.call("spreadsheet.dashboard", "action_toggle_favorite", [id]);
        dashboard.data.is_favorite = !is_favorite;
    }

    toggleSidebar() {
        this.state.sidebarExpanded = !this.state.sidebarExpanded;
    }

    get activeDashboardGroupName() {
        return this.getDashboardGroups().find(
            (group) =>
                group.id !== "favorites" && // Skip the FAVORITES group
                group.dashboards.some(({ data }) => data.id === this.activeDashboardId())
        )?.name;
    }

    logExport() {
        const dashboard = this.loader.getActiveDashboard();
        if (!dashboard || dashboard.status !== Status.Loaded) {
            return;
        }
        dashboard.model.dispatch("LOG_DATASOURCE_EXPORT", { action: "print" });
    }
}

registry
    .category("actions")
    .add("action_spreadsheet_dashboard", SpreadsheetDashboardAction, { force: true });
