/** @odoo-module **/

import { browser } from "../core/browser";
import { serviceRegistry } from "../webclient/service_registry";

const loadMenusUrl = `/web/webclient/load_menus`;

function makeFetchLoadMenus() {
  const cacheHashes = odoo.session_info.cache_hashes;
  let loadMenusHash = cacheHashes.load_menus || new Date().getTime().toString();
  return async function fetchLoadMenus(reload) {
    if (reload) {
      loadMenusHash = new Date().getTime().toString();
    }
    const res = await browser.fetch(`${loadMenusUrl}/${loadMenusHash}`);
    if (!res.ok) {
      throw new Error("Error while fetching menus");
    }
    return res.json();
  };
}

function makeMenus(env, menusData, fetchLoadMenus) {
  let currentAppId;
  return {
    getAll() {
      return Object.values(menusData);
    },
    getApps() {
      return this.getMenu("root").children.map((mid) => this.getMenu(mid));
    },
    getMenu(menuID) {
      return menusData[menuID];
    },
    getCurrentApp() {
      if (!currentAppId) {
        return;
      }
      return this.getMenu(currentAppId);
    },
    getMenuAsTree(menuID) {
      const menu = this.getMenu(menuID);
      if (!menu.childrenTree) {
        menu.childrenTree = menu.children.map((mid) => this.getMenuAsTree(mid));
      }
      return menu;
    },
    async selectMenu(menu) {
      menu = typeof menu === "number" ? this.getMenu(menu) : menu;
      if (!menu.actionID) {
        return;
      }
      await env.services.action.doAction(menu.actionID, { clearBreadcrumbs: true });
      this.setCurrentMenu(menu);
    },
    setCurrentMenu(menu) {
      menu = typeof menu === "number" ? this.getMenu(menu) : menu;
      if (menu && menu.appID !== currentAppId) {
        currentAppId = menu.appID;
        env.bus.trigger("MENUS:APP-CHANGED");
        // FIXME: lock API: maybe do something like
        // pushState({menu_id: ...}, { lock: true}); ?
        env.services.router.pushState({
          "lock menu_id": `${menu.id}`,
        });
      }
    },
    async reload() {
      if (fetchLoadMenus) {
        menusData = await fetchLoadMenus(true);
        env.bus.trigger("MENUS:APP-CHANGED");
      }
    },
  };
}

export const menuService = {
  dependencies: ["action", "router"],
  async deploy(env) {
    const fetchLoadMenus = makeFetchLoadMenus();
    const menusData = await fetchLoadMenus();
    return makeMenus(env, menusData, fetchLoadMenus);
  },
};

serviceRegistry.add("menu", menuService);
