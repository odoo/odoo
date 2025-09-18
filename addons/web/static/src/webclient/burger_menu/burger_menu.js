// @ts-check

/** @module @web/webclient/burger_menu/burger_menu - Fullscreen mobile menu displaying user menu, company switcher, and current app sub-menus */

import { Component, useState } from "@odoo/owl";
import { Transition } from "@web/components/transition";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { user } from "@web/services/user";

import { BurgerUserMenu } from "./burger_user_menu/burger_user_menu";
import { MobileSwitchCompanyMenu } from "./mobile_switch_company_menu/mobile_switch_company_menu";

/**
 * This file includes the widget Menu in mobile to render the BurgerMenu which
 * opens fullscreen and displays the user menu and the current app submenus.
 */

const SWIPE_ACTIVATION_THRESHOLD = 100;

export class BurgerMenu extends Component {
    static template = "web.BurgerMenu";
    static props = {};
    static components = {
        BurgerUserMenu,
        MobileSwitchCompanyMenu,
        Transition,
    };

    setup() {
        this.user = user;
        this.state = useState({
            isBurgerOpened: false,
        });
        this.swipeStartX = null;
        useBus(this.env.bus, "HOME-MENU:TOGGLED", () => {
            this._closeBurger();
        });
        useBus(
            this.env.bus,
            "ACTION_MANAGER:UPDATE",
            /** @type {any} */ (
                ({ detail: req }) => {
                    if (req.id) {
                        this._closeBurger();
                    }
                }
            ),
        );
    }
    _closeBurger() {
        this.state.isBurgerOpened = false;
    }
    _openBurger() {
        this.state.isBurgerOpened = true;
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

const systrayItem = {
    Component: BurgerMenu,
};

registry.category("systray").add("burger_menu", systrayItem, { sequence: 0 });
