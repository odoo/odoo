/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";
import { useService } from "@web/core/utils/hooks";
import { BurgerUserMenu } from "./burger_user_menu/burger_user_menu";
import { MobileSwitchCompanyMenu } from "./mobile_switch_company_menu/mobile_switch_company_menu";

import { Component, onMounted, useState } from "@odoo/owl";

/**
 * This file includes the widget Menu in mobile to render the BurgerMenu which
 * opens fullscreen and displays the user menu and the current app submenus.
 */

const SWIPE_ACTIVATION_THRESHOLD = 100;

export class BurgerMenu extends Component {
    setup() {
        this.company = useService("company");
        this.user = useService("user");
        this.menuRepo = useService("menu");
        this.state = useState({
            isUserMenuOpened: false,
            isBurgerOpened: false,
        });
        this.swipeStartX = null;
        onMounted(() => {
            this.env.bus.addEventListener("HOME-MENU:TOGGLED", () => {
                this._closeBurger();
            });
            this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", ({ detail: req }) => {
                if (req.id) {
                    this._closeBurger();
                }
            });
        });
    }
    get currentApp() {
        return this.menuRepo.getCurrentApp();
    }
    get currentAppSections() {
        return (
            (this.currentApp && this.menuRepo.getMenuAsTree(this.currentApp.id).childrenTree) || []
        );
    }
    get isUserMenuUnfolded() {
        return !this.isUserMenuTogglable || this.state.isUserMenuOpened;
    }
    get isUserMenuTogglable() {
        return this.currentApp && this.currentAppSections.length > 0;
    }
    _closeBurger() {
        this.state.isUserMenuOpened = false;
        this.state.isBurgerOpened = false;
    }
    _openBurger() {
        this.state.isBurgerOpened = true;
    }
    _toggleUserMenu() {
        this.state.isUserMenuOpened = !this.state.isUserMenuOpened;
    }
    async _onMenuClicked(menu) {
        await this.menuRepo.selectMenu(menu);
        this._closeBurger();
    }
    _onSwipeStart(ev) {
        this.swipeStartX = ev.changedTouches[0].clientX;
    }
    _onSwipeEnd(ev) {
        if (!this.swipeStartX) {
            return;
        }
        const deltaX = ev.changedTouches[0].clientX - this.swipeStartX;
        if (deltaX < SWIPE_ACTIVATION_THRESHOLD) {
            return;
        }
        this._closeBurger();
        this.swipeStartX = null;
    }
}
BurgerMenu.template = "web.BurgerMenu";
BurgerMenu.components = {
    BurgerUserMenu,
    MobileSwitchCompanyMenu,
    Transition,
};

const systrayItem = {
    Component: BurgerMenu,
};

registry.category("systray").add("burger_menu", systrayItem, { sequence: 0 });
