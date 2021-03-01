/** @odoo-module **/

import { ActionContainer } from "../actions/action_service";
import { NavBar } from "./navbar/navbar";
import { useService } from "../core/hooks";

const { Component, hooks } = owl;

export class WebClient extends Component {
  constructor(...args) {
    super(...args);
    this.menus = useService("menus");
    this.actionService = useService("action");
    this.title = useService("title");
    this.router = useService("router");
    this.user = useService("user");
    this.Components = odoo.mainComponentRegistry.getEntries();
    this.title.setParts({ zopenerp: "Odoo" }); // zopenerp is easy to grep
    hooks.onMounted(() => {
      this.env.bus.on("ROUTE_CHANGE", this, this.loadRouterState);
      this.env.bus.on("ACTION_MANAGER:UI-UPDATED", this, (mode) => {
        if (mode !== "new") {
          this.el.classList.toggle("o_fullscreen", mode === "fullscreen");
          this.replaceRouterState();
        }
      });
      this.loadRouterState();
    });
  }

  mounted() {
    // the chat window and dialog services listen to 'web_client_ready' event in
    // order to initialize themselves:
    this.env.bus.trigger("WEB_CLIENT_READY");
  }

  async loadRouterState() {
    const options = {
      clearBreadcrumbs: true,
    };
    const state = this.router.current.hash;
    let action = state.action;
    if (action && !Number.isNaN(action)) {
      action = parseInt(action, 10);
    }
    let menuId = state.menu_id ? parseInt(state.menu_id, 10) : undefined;
    const actionManagerHandles = await this.actionService.loadState(state, options);
    if (!actionManagerHandles) {
      if (!action && menuId) {
        // determine action from menu_id key
        const menu = this.menus.getAll().find((m) => menuId === m.id);
        action = menu && menu.actionID;
      }
      if (action) {
        await this.actionService.doAction(action, options);
      }
    }
    // Determine the app we are in
    if (!menuId && typeof action === "number") {
      const menu = this.menus.getAll().find((m) => m.actionID === action);
      menuId = menu && menu.appID;
    }
    if (menuId) {
      this.menus.setCurrentMenu(menuId);
    }
    if (!actionManagerHandles && !action) {
      return this._loadDefaultApp();
    }
  }

  async _loadDefaultApp() {
    const action = this.user.home_action_id;
    if (action) {
      // Don't know what to do here: should we set the menu
      // even if it's a guess ?
      return this.actionService.doAction(action, { clearBreadcrumbs: true });
    }
    const root = this.menus.getMenu("root");
    const firstApp = root.children[0];
    if (firstApp) {
      return this.menus.selectMenu(firstApp);
    }
  }

  replaceRouterState() {
    const currentApp = this.menus.getCurrentApp();
    const persistentHash = {
      menu_id: currentApp && `${currentApp.id}`,
    };
    const allowedCompanyIds = this.user.context.allowed_company_ids;
    if (allowedCompanyIds) {
      persistentHash.cids = allowedCompanyIds.join(",");
    }
    this.router.pushState(persistentHash);
  }
}
WebClient.components = { ActionContainer, NavBar };
WebClient.template = "wowl.WebClient";
