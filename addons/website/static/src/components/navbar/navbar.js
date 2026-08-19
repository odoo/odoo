import { render } from "@web/owl2/utils";
import { NavBar } from "@web/webclient/navbar/navbar";
import { useService, useBus } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { usePlugin } from "@odoo/owl";
import { DebugModePlugin } from "@web/core/debug_mode_plugin";

const websiteSystrayRegistry = registry.category("website_systray");
websiteSystrayRegistry.add("UserMenu", { Component: UserMenu }, { sequence: 14 });

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.websiteService = useService("website");
        this.websiteCustomMenus = useService("website_custom_menus");

        // The navbar is rerendered with an event, as it can not naturally be
        // with props/state (the WebsitePreview client action and the navbar
        // are not related).
        useBus(websiteSystrayRegistry, "EDIT-WEBSITE", () => render(this, true));

        const debugMode = usePlugin(DebugModePlugin);
        if (debugMode.isActive() && !websiteSystrayRegistry.contains("web.debug_mode_menu")) {
            websiteSystrayRegistry.add(
                "web.debug_mode_menu",
                registry.category("systray").get("web.debug_mode_menu"),
                { sequence: 100 }
            );
        }
        useBus(websiteSystrayRegistry, "CONTENT-UPDATED", () => render(this, true));
    },

    get shouldDisplayWebsiteSystray() {
        return this.websiteService.currentWebsite && this.websiteService.isRestrictedEditor;
    },

    // Somehow a setter is needed in `patch()` to avoid an owl error.
    set shouldDisplayWebsiteSystray(_) {},

    /**
     * @override
     */
    get systrayItems() {
        if (this.websiteService.currentWebsite) {
            const websiteItems = websiteSystrayRegistry
                .getEntries()
                .map(([key, value], index) => ({ key, ...value, index }))
                .filter((item) => ("isDisplayed" in item ? item.isDisplayed(this.env) : true))
                .reverse();
            // Do not override the regular Odoo navbar if the only visible
            // elements are the debug items.
            if (
                !websiteItems.every((item) =>
                    ["burger_menu", "web.debug_mode_menu"].includes(item.key)
                )
            ) {
                return websiteItems;
            }
        }
        return super.systrayItems;
    },

    /**
     * @override
     */
    get currentAppSections() {
        const currentAppSections = super.currentAppSections;
        if (this.currentApp && this.currentApp.xmlid === "website.menu_website_configuration") {
            return this.websiteCustomMenus
                .addCustomMenus(currentAppSections)
                .filter((section) => section.childrenTree.length);
        }
        return currentAppSections;
    },

    /**
     * @override
     */
    async onNavBarDropdownItemSelection(menu) {
        const websiteMenu = this.websiteCustomMenus.get(menu.xmlid);
        if (websiteMenu) {
            return this.websiteCustomMenus.open(menu);
        }
        return super.onNavBarDropdownItemSelection(menu);
    },
});
