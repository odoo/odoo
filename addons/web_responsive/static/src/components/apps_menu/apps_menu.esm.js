/* global document, location, window */

/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {AppMenuItem} from "@web_responsive/components/apps_menu_item/apps_menu_item.esm";
import {AppsMenuSearchBar} from "@web_responsive/components/menu_searchbar/searchbar.esm";
import {NavBar} from "@web/webclient/navbar/navbar";
import {WebClient} from "@web/webclient/webclient";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";
import {router} from "@web/core/browser/router";
import {session} from "@web/session";
import {useHotkey} from "@web/core/hotkeys/hotkey_hook";
import {user} from "@web/core/user";
import {BurgerMenu} from "@web/webclient/burger_menu/burger_menu";

// Patch WebClient to show AppsMenu instead of default app
patch(WebClient.prototype, {
    setup() {
        super.setup();
        useBus(this.env.bus, "APPS_MENU:STATE_CHANGED", ({detail: state}) => {
            document.body.classList.toggle("o_apps_menu_opened", state);
        });
        this.user = user;
        onWillStart(async () => {
            const is_redirect_home = await this.orm.searchRead(
                "res.users",
                [["id", "=", this.user.userId]],
                ["is_redirect_home"]
            );
            user.updateContext({
                is_redirect_to_home: is_redirect_home[0]?.is_redirect_home,
            });
        });
        this.redirect = false;
    },
    _loadDefaultApp() {
        if (user.context.is_redirect_to_home) {
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", true);
        } else {
            super._loadDefaultApp();
        }
    },
});

export class AppsMenu extends Component {
    setup() {
        super.setup();
        this.state = useState({open: false});
        this.theme = session.apps_menu.theme || "milk";
        this.menuService = useService("menu");
        browser.localStorage.setItem("redirect_menuId", "");
        if (user.context.is_redirect_to_home) {
            this.router = router;
            const menuId = Number(this.router.current.menu_id || 0);
            this.state = useState({open: menuId === 0});
        }
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            this.setOpenState(false);
        });
        this._setupKeyNavigation();
    }

    setOpenState(open_state) {
        this.state.open = open_state;
        this.env.bus.trigger("APPS_MENU:STATE_CHANGED", open_state);
    }

    /**
     * Setup navigation among app menus
     */
    _setupKeyNavigation() {
        const repeatable = {
            allowRepeat: true,
        };
        useHotkey(
            "ArrowRight",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowLeft",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey(
            "ArrowDown",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowUp",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey("Escape", () => {
            this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
        });
    }

    _onWindowKeydown(direction) {
        const focusableInputElements = document.querySelectorAll(".o-app-menu-item");
        if (focusableInputElements.length) {
            const focusable = [...focusableInputElements];
            const index = focusable.indexOf(document.activeElement);
            let nextIndex = 0;
            if (direction === "prev" && index >= 0) {
                if (index > 0) {
                    nextIndex = index - 1;
                } else {
                    nextIndex = focusable.length - 1;
                }
            } else if (direction === "next") {
                if (index + 1 < focusable.length) {
                    nextIndex = index + 1;
                } else {
                    nextIndex = 0;
                }
            }
            focusableInputElements[nextIndex].focus();
        }
    }

    onMenuClick() {
        if (!user.context.is_redirect_to_home) {
            this.setOpenState(!this.state.open);
        } else {
            const redirect_menuId =
                browser.localStorage.getItem("redirect_menuId") || "";
            if (!redirect_menuId) {
                this.setOpenState(true);
            } else {
                this.setOpenState(!this.state.open);
            }
            const {href, hash} = location;
            const menuId = this.router.current.menu_id;
            if (menuId && menuId !== redirect_menuId) {
                browser.localStorage.setItem(
                    "redirect_menuId",
                    this.router.current.menu_id
                );
            }

            if (href.includes(hash)) {
                window.history.replaceState(null, "", href.replace(hash, ""));
            }
        }
    }
}

// Add this patch after the WebClient patch
patch(NavBar.prototype, {
    setup() {
        super.setup();

        useBus(this.env.bus, "APP_MENU:TOGGLE_SIDEBAR", () => {
            this._openAppMenuSidebar();
        });
    },

    openAppMenu() {
        this.env.bus.trigger("APP_MENU:OPEN_APP_MENU");
        this._closeAppMenuSidebar();
    },
});

Object.assign(AppsMenu, {
    template: "web_responsive.AppsMenu",
    props: {
        slots: {
            type: Object,
            optional: true,
        },
    },
});

Object.assign(NavBar.components, {AppsMenu, AppMenuItem, AppsMenuSearchBar});

// Add this patch after the WebClient patch
patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
    },

    _openAppMenuSidebarMobile() {
        this.env.bus.trigger("APP_MENU:TOGGLE_SIDEBAR");
    },
});
