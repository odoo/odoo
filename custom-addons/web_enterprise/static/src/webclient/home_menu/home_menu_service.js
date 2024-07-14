/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";
import {
    ControllerNotFoundError,
    standardActionServiceProps,
} from "@web/webclient/actions/action_service";
import { HomeMenu } from "./home_menu";

import { Component, onMounted, onWillUnmount, xml } from "@odoo/owl";

export const homeMenuService = {
    dependencies: ["action", "router", "user"],
    start(env, { user }) {
        let hasHomeMenu = false; // true iff the HomeMenu is currently displayed
        let hasBackgroundAction = false; // true iff there is an action behind the HomeMenu
        const mutex = new Mutex(); // used to protect against concurrent toggling requests
        class HomeMenuAction extends Component {
            setup() {
                this.router = useService("router");
                this.menus = useService("menu");
                const user = useService("user");
                const homemenuConfig = JSON.parse(user.settings?.homemenu_config || "null");
                const apps = computeAppsAndMenuItems(this.menus.getMenuAsTree("root")).apps;
                if (homemenuConfig) {
                    reorderApps(apps, homemenuConfig);
                }
                this.homeMenuProps = {
                    apps: apps,
                };
                onMounted(() => this.onMounted());
                onWillUnmount(this.onWillUnmount);
            }
            async onMounted() {
                const { breadcrumbs } = this.env.config;
                hasHomeMenu = true;
                hasBackgroundAction = breadcrumbs.length > 0;
                this.env.bus.trigger("HOME-MENU:TOGGLED");
            }
            onWillUnmount() {
                hasHomeMenu = false;
                hasBackgroundAction = false;
                this.env.bus.trigger("HOME-MENU:TOGGLED");
            }
        }
        HomeMenuAction.components = { HomeMenu };
        HomeMenuAction.target = "current";
        HomeMenuAction.props = { ...standardActionServiceProps };
        HomeMenuAction.template = xml`<HomeMenu t-props="homeMenuProps"/>`;

        registry.category("actions").add("menu", HomeMenuAction);

        env.bus.addEventListener("HOME-MENU:TOGGLED", () => {
            document.body.classList.toggle("o_home_menu_background", hasHomeMenu);
        });

        return {
            get hasHomeMenu() {
                return hasHomeMenu;
            },
            get hasBackgroundAction() {
                return hasBackgroundAction;
            },
            async toggle(show) {
                return mutex.exec(async () => {
                    show = show === undefined ? !hasHomeMenu : Boolean(show);
                    if (show !== hasHomeMenu) {
                        if (show) {
                            await env.services.action.doAction("menu");
                        } else {
                            try {
                                await env.services.action.restore();
                            } catch (err) {
                                if (!(err instanceof ControllerNotFoundError)) {
                                    throw err;
                                }
                            }
                        }
                    }
                    // hack: wait for a tick to ensure that the url has been updated before
                    // switching again
                    return new Promise((r) => setTimeout(r));
                });
            },
        };
    },
};

registry.category("services").add("home_menu", homeMenuService);
