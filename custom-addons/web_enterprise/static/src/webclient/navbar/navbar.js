/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useEffect, useRef } from "@odoo/owl";

export class EnterpriseNavBar extends NavBar {
    setup() {
        super.setup();
        this.hm = useService("home_menu");
        this.menuAppsRef = useRef("menuApps");
        this.navRef = useRef("nav");
        this._busToggledCallback = () => this._updateMenuAppsIcon();
        useBus(this.env.bus, "HOME-MENU:TOGGLED", this._busToggledCallback);
        useEffect(() => this._updateMenuAppsIcon());
    }
    get hasBackgroundAction() {
        return this.hm.hasBackgroundAction;
    }
    get isInApp() {
        return !this.hm.hasHomeMenu;
    }
    _updateMenuAppsIcon() {
        const menuAppsEl = this.menuAppsRef.el;
        menuAppsEl.classList.toggle("o_hidden", !this.isInApp && !this.hasBackgroundAction);
        menuAppsEl.classList.toggle(
            "o_menu_toggle_back",
            !this.isInApp && this.hasBackgroundAction
        );
        const title =
            !this.isInApp && this.hasBackgroundAction ? _t("Previous view") : _t("Home menu");
        menuAppsEl.title = title;
        menuAppsEl.ariaLabel = title;

        const menuBrand = this.navRef.el.querySelector(".o_menu_brand");
        if (menuBrand) {
            menuBrand.classList.toggle("o_hidden", !this.isInApp);
        }

        const menuBrandIcon = this.navRef.el.querySelector(".o_menu_brand_icon");
        if (menuBrandIcon) {
            menuBrandIcon.classList.toggle("o_hidden", !this.isInApp);
        }

        const appSubMenus = this.appSubMenus.el;
        if (appSubMenus) {
            appSubMenus.classList.toggle("o_hidden", !this.isInApp);
        }
    }
}
EnterpriseNavBar.template = "web_enterprise.EnterpriseNavBar";
