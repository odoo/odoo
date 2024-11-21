import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { DebugMenu } from "@web/core/debug/debug_menu";
import { localization } from "@web/core/l10n/localization";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { ActionContainer } from "./actions/action_container";
import { NavBar } from "./navbar/navbar";

import { Component, onMounted, onWillStart, useExternalListener, useState } from "@odoo/owl";
import { router, routerBus } from "@web/core/browser/router";
import { browser } from "@web/core/browser/browser";

export class WebClient extends Component {
    static template = "web.WebClient";
    static props = {};
    static components = {
        ActionContainer,
        NavBar,
        MainComponentsContainer,
    };

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.title = useService("title");
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
        this.state = useState({
            fullscreen: false,
        });
        useBus(routerBus, "ROUTE_CHANGE", this.loadRouterState);
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", ({ detail: mode }) => {
            if (mode !== "new") {
                this.state.fullscreen = mode === "fullscreen";
            }
        });
        onMounted(() => {
            this.loadRouterState();
            // the chat window and dialog services listen to 'web_client_ready' event in
            // order to initialize themselves:
            this.env.bus.trigger("WEB_CLIENT_READY");
        });
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
        onWillStart(this.registerServiceWorker);
    }

    async loadRouterState() {
        // ** url-retrocompatibility **
        // the menu_id in the url is only possible if we came from an old url
        let menuId = Number(router.current.menu_id || 0);
        const firstAction = router.current.actionStack?.[0]?.action;
        if (!menuId && firstAction) {
            menuId = this.menuService
                .getAll()
                .find((m) => m.actionID === firstAction || m.actionPath === firstAction)?.appID;
        }
        if (menuId) {
            this.menuService.setCurrentMenu(menuId);
        }
        let stateLoaded = await this.actionService.loadState();

        // ** url-retrocompatibility **
        // when there is only menu_id in url
        if (!stateLoaded && menuId) {
            // Determines the current actionId based on the current menu
            const menu = this.menuService.getAll().find((m) => menuId === m.id);
            const actionId = menu && menu.actionID;
            if (actionId) {
                await this.actionService.doAction(actionId, { clearBreadcrumbs: true });
                stateLoaded = true;
            }
        }

        // Setting the menu based on the action after it was loaded (eg when the action in url is an xmlid)
        if (stateLoaded && !menuId) {
            // Determines the current menu based on the current action
            const currentController = this.actionService.currentController;
            const actionId = currentController && currentController.action.id;
            menuId = this.menuService.getAll().find((m) => m.actionID === actionId)?.appID;
            if (menuId) {
                // Sets the menu according to the current action
                this.menuService.setCurrentMenu(menuId);
            }
        }

        // Scroll to anchor after the state is loaded
        if (stateLoaded) {
            if (browser.location.hash !== "") {
                try {
                    const el = document.querySelector(browser.location.hash);
                    if (el !== null) {
                        el.scrollIntoView(true);
                    }
                } catch {
                    // do nothing if the hash is not a correct selector.
                }
            }
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
            (ev.ctrlKey || ev.metaKey) &&
            !ev.target.isContentEditable &&
            ((ev.target instanceof HTMLAnchorElement && ev.target.href) ||
                (ev.target instanceof HTMLElement && ev.target.closest("a[href]:not([href=''])")))
        ) {
            ev.stopImmediatePropagation();
            return;
        }
    }

    registerServiceWorker() {
        if (navigator.serviceWorker) {
            navigator.serviceWorker
                .register("/web/service-worker.js", { scope: "/odoo" })
                .catch((error) => {
                    console.error("Service worker registration failed, error:", error);
                });
        }
    }
}
