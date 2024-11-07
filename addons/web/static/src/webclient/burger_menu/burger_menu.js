import { registry } from "@web/core/registry";
import { Transition } from "@web/core/transition";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { BurgerUserMenu } from "./burger_user_menu/burger_user_menu";
import { MobileSwitchCompanyMenu } from "./mobile_switch_company_menu/mobile_switch_company_menu";

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";

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
        this.company = useService("company");
        this.user = user;
        this.state = useState({
            isBurgerOpened: false,
        });
        this.swipeStartX = null;

        const homeMenuToggledListener = () => {
            this._closeBurger();
        };

        const actionManagerUpdateListener = ({ detail: req }) => {
            if (req.id) {
                this._closeBurger();
            }
        };

        onMounted(() => {
            this.env.bus.addEventListener("HOME-MENU:TOGGLED", homeMenuToggledListener);
            this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", actionManagerUpdateListener);
        });
        onWillUnmount(() => {
            this.env.bus.removeEventListener("HOME-MENU:TOGGLED", homeMenuToggledListener);
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", actionManagerUpdateListener);
        });
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
