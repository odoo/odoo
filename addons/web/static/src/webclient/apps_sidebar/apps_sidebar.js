import { Component, proxy, useListener, usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { render } from "@web/owl2/utils";
import {
    appsSidebarBus,
    getAppsSidebarState,
    toggleAppsSidebarExpanded,
    toggleAppsSidebarPin,
} from "./apps_sidebar_state";

/**
 * Vertical bar displayed on the side of the action manager, allowing to switch
 * from one app to another in a single click, without going through the apps
 * menu. It is hidden by default, and can be toggled from the user menu.
 */
export class AppsSidebar extends Component {
    static template = "web.AppsSidebar";
    static components = { Dropdown, DropdownItem };

    debugMode = usePlugin(DebugModePlugin);

    setup() {
        this.menuService = useService("menu");
        this.ui = proxy(useService("ui"));
        this.state = getAppsSidebarState();
        useListener(appsSidebarBus, "UPDATE", () => render(this));
        useListener(this.env.bus, "MENUS:APP-CHANGED", () => render(this));
    }

    /**
     * The sidebar is useless on small screens, as the whole apps menu is
     * already displayed as a sidebar there.
     */
    get isDisplayed() {
        return this.state.isVisible && !this.ui.isSmall;
    }

    get allApps() {
        return this.menuService.getApps();
    }

    /**
     * The apps to display: the pinned ones, or all of them if none is pinned.
     */
    get apps() {
        const apps = this.allApps;
        if (!this.state.pinnedApps.length) {
            return apps;
        }
        return apps.filter((app) => this.state.pinnedApps.includes(app.xmlid));
    }

    get toggleTitle() {
        return this.state.isExpanded ? _t("Collapse the sidebar") : _t("Expand the sidebar");
    }

    get currentApp() {
        return this.menuService.getCurrentApp();
    }

    getAppIcon(app) {
        const [webIconClass, webIconColor] = (app.webIcon || "").split(",");
        return { webIconClass, webIconColor };
    }

    getMenuItemHref(app) {
        const url = `/odoo/${app.actionPath || "action-" + app.actionID}`;
        const mode = this.debugMode.toString();
        return mode ? `${url}?debug=${mode}` : url;
    }

    isPinned(app) {
        return this.state.pinnedApps.includes(app.xmlid);
    }

    onAppClicked(app) {
        this.menuService.selectMenu(app);
    }

    onPinToggled(app) {
        toggleAppsSidebarPin(app.xmlid);
    }

    onToggleExpanded() {
        toggleAppsSidebarExpanded();
    }
}
