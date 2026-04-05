/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";
import { router } from "@web/core/browser/router";
import { onWillUnmount } from "@odoo/owl";

import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarInset,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarProvider,
    SidebarSeparator,
    SidebarTrigger,
} from "@odx_owl/components/sidebar/sidebar";
import { Separator } from "@odx_owl/components/separator/separator";
import { Kbd } from "@odx_owl/components/kbd/kbd";
// Company dropdown uses plain state toggle (no DropdownMenu — it conflicts with Odoo's Dropdown inside sidebar)

WebClient.components = {
    ...WebClient.components,
    Kbd,
    Separator,
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarHeader,
    SidebarInset,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarProvider,
    SidebarSeparator,
    SidebarTrigger,
};

patch(WebClient.prototype, {
    setup() {
        super.setup();

        this.menuService = this.env.services.menu;
        this.user = user;

        this.state.currentAppSections = [];
        this.state.expandedMenus = new Set();
        this.state.currentAppId = this.menuService.getCurrentApp()?.id;
        this.state.companyMenuOpen = false;
        this.state.userMenuOpen = false;

        this._updateCurrentAppSections();

        this._menuChangedHandler = this._onMenuChanged.bind(this);
        this.env.bus.addEventListener("MENUS:APP-CHANGED", this._menuChangedHandler);

        onWillUnmount(() => {
            this.env.bus.removeEventListener("MENUS:APP-CHANGED", this._menuChangedHandler);
        });
    },

    get avatarUrl() {
        return `/web/image/res.users/${user.userId}/avatar_128`;
    },

    get companyList() {
        return Object.values(user.allowedCompanies);
    },

    get hasMultipleCompanies() {
        return this.companyList.length > 1;
    },

    toggleCompanyMenu() {
        this.state.companyMenuOpen = !this.state.companyMenuOpen;
        this.state.userMenuOpen = false;
    },

    closeCompanyMenu() {
        this.state.companyMenuOpen = false;
    },

    toggleUserMenu() {
        this.state.userMenuOpen = !this.state.userMenuOpen;
        this.state.companyMenuOpen = false;
    },

    closeUserMenu() {
        this.state.userMenuOpen = false;
    },

    async openPreferences() {
        this.state.userMenuOpen = false;
        try {
            const actionDescription = await this.env.services.orm.call("res.users", "action_get");
            actionDescription.res_id = user.userId;
            this.env.services.action.doAction(actionDescription);
        } catch {
            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: "res.users",
                res_id: user.userId,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },

    openShortcuts() {
        this.state.userMenuOpen = false;
        this.env.services.command.openMainPalette();
    },

    async openOdooAccount() {
        this.state.userMenuOpen = false;
        try {
            const url = await this.env.services.orm.call("ir.http", "session_account_url", []);
            window.open(url || "https://accounts.odoo.com/account", "_blank");
        } catch {
            window.open("https://accounts.odoo.com/account", "_blank");
        }
    },

    openDocumentation() {
        this.state.userMenuOpen = false;
        window.open("https://www.odoo.com/documentation", "_blank");
    },

    openSupport() {
        this.state.userMenuOpen = false;
        const url = this.env.services.session?.support_url || "https://www.odoo.com/help";
        window.open(url, "_blank");
    },

    logout() {
        this.state.userMenuOpen = false;
        window.location.href = "/web/session/logout";
    },

    get activeCompanyIds() {
        return user.activeCompanies.map((c) => c.id);
    },

    isCompanyActive(companyId) {
        return this.activeCompanyIds.includes(companyId);
    },

    toggleCompany(companyId) {
        const currentIds = [...this.activeCompanyIds];
        const idx = currentIds.indexOf(companyId);
        if (idx >= 0 && currentIds.length > 1) {
            // Deselect (but keep at least one)
            currentIds.splice(idx, 1);
        } else if (idx < 0) {
            // Select
            currentIds.push(companyId);
        }
        user.activateCompanies(currentIds, {
            includeChildCompanies: false,
            reload: false,
        });
        router.pushState({}, { reload: true });
    },

    switchToCompany(companyId) {
        user.activateCompanies([companyId], {
            includeChildCompanies: true,
            reload: false,
        });
        router.pushState({}, { reload: true });
    },

    _updateCurrentAppSections() {
        const currentApp = this.menuService.getCurrentApp();
        if (!currentApp) {
            this.state.currentAppSections = [];
            return;
        }
        const tree = this.menuService.getMenuAsTree(currentApp.id);
        this.state.currentAppSections = tree?.childrenTree || [];
    },

    _onMenuChanged() {
        const currentApp = this.menuService.getCurrentApp();
        this.state.currentAppId = currentApp?.id || null;
        this._updateCurrentAppSections();
    },

    _getFirstActionableMenu(menu) {
        if (!menu) return null;
        if (menu.actionID) return menu;
        if (menu.childrenTree?.length) {
            for (const child of menu.childrenTree) {
                const actionable = this._getFirstActionableMenu(child);
                if (actionable) return actionable;
            }
        }
        return null;
    },

    onAppClick(app) {
        if (!app) return;
        const firstActionable = this._getFirstActionableMenu(app);
        if (firstActionable) {
            this.menuService.selectMenu(firstActionable);
        }
    },

    onSectionClick(menu) {
        if (!menu) return;

        if (menu.childrenTree?.length) {
            if (this.state.expandedMenus.has(menu.id)) {
                this.state.expandedMenus.delete(menu.id);
            } else {
                this.state.expandedMenus.add(menu.id);
            }
            const firstActionable = this._getFirstActionableMenu(menu);
            if (firstActionable) {
                this.menuService.selectMenu(firstActionable);
            }
            return;
        }

        if (menu.actionID) {
            this.menuService.selectMenu(menu);
        }
    },

    _getMenuIcon(menu) {
        if (menu.webIconData) return menu.webIconData;
        if (menu.webIcon) return `/web/image/${menu.webIcon}`;
        return "/web/static/img/menu_icon.svg";
    },
});
