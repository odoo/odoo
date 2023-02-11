/** @odoo-module **/

import { ActionContainer } from "./actions/action_container";
import { NavBar } from "./navbar/navbar";
import { useBus, useEffect, useService } from "@web/core/utils/hooks";
import { useTooltip } from "@web/core/tooltip/tooltip_hook";
import { NotUpdatable } from "../core/utils/components";
import { MainComponentsContainer } from "../core/main_components_container";
import { useOwnDebugContext } from "../core/debug/debug_context";
import { registry } from "@web/core/registry";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { localization } from "@web/core/l10n/localization";

const { Component, hooks } = owl;
const { useExternalListener } = hooks;

export class WebClient extends Component {
    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.title = useService("title");
        this.router = useService("router");
        this.user = useService("user");
        useService("legacy_service_provider");
        useOwnDebugContext({ categories: ["default"] });
        if (this.env.debug) {
            registry.category("systray").add(
                "web.debug_mode_menu",
                {
                    Component: DebugMenu,
                },
                { sequence: 100 }
            );
        }
        this.localization = localization;
        this.title.setParts({ zopenerp: "Odoo" }); // zopenerp is easy to grep
        useBus(this.env.bus, "ROUTE_CHANGE", this.loadRouterState);
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            if (mode !== "new") {
                this.el.classList.toggle("o_fullscreen", mode === "fullscreen");
            }
        });
        useEffect(
            () => {
                this.loadRouterState();
            },
            () => []
        );
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
        useTooltip();
    }

    mounted() {
        // the chat window and dialog services listen to 'web_client_ready' event in
        // order to initialize themselves:
        this.env.bus.trigger("WEB_CLIENT_READY");
    }

    async loadRouterState() {
        let stateLoaded = await this.actionService.loadState();
        let menuId = Number(this.router.current.hash.menu_id || 0);

        if (!stateLoaded && menuId) {
            // Determines the current actionId based on the current menu
            const menu = this.menuService.getAll().find((m) => menuId === m.id);
            const actionId = menu && menu.actionID;
            if (actionId) {
                await this.actionService.doAction(actionId, { clearBreadcrumbs: true });
                stateLoaded = true;
            }
        }

        if (stateLoaded && !menuId) {
            // Determines the current menu based on the current action
            const currentController = this.actionService.currentController;
            const actionId = currentController && currentController.action.id;
            const menu = this.menuService.getAll().find((m) => m.actionID === actionId);
            menuId = menu && menu.appID;
        }

        if (menuId) {
            // Sets the menu according to the current action
            this.menuService.setCurrentMenu(menuId);
        }

        if (!stateLoaded) {
            // If no action => falls back to the default app
            await this._loadDefaultApp();
        }
    }

    _loadDefaultApp() {
        // Selects the first root menu if any
        const root = this.menuService.getMenu("root");
        const firstApp = root.children[0];
        if (firstApp) {
            return this.menuService.selectMenu(firstApp);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev) {
        // When a ctrl-click occurs inside an <a href/> element
        // we let the browser do the default behavior and
        // we do not want any other listener to execute.
        if (
            ev.ctrlKey &&
            ((ev.target instanceof HTMLAnchorElement && ev.target.href) ||
                (ev.target instanceof HTMLElement && ev.target.closest("a[href]:not([href=''])")))
        ) {
            ev.stopImmediatePropagation();
            return;
        }
    }
}
WebClient.components = {
    ActionContainer,
    NavBar,
    NotUpdatable,
    MainComponentsContainer,
};
WebClient.template = "web.WebClient";
