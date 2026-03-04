import { user } from "@web/core/user";
import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { appMenuService } from "@muk_web_appsbar/webclient/menus/app_menu_service";

function makeMenuTree(apps) {
    return {
        id: null,
        actionID: null,
        childrenTree: apps.map((app) => ({
            id: app.id,
            appID: app.id,
            name: app.name,
            xmlid: app.xmlid,
            actionID: app.actionID,
            actionPath: `action-${app.actionID}`,
            childrenTree: [],
        })),
    };
}

test.tags("muk_web_appsbar");
test("app_menu service reorders apps based on user settings", async () => {
    const realSettings = user.settings;
    patchWithCleanup(
        user, 
        {
            get settings() {
                return {
                    ...realSettings,
                    homemenu_config: JSON.stringify(["app.gamma", "app.alpha", "app.beta"]),
                };
            },
        }
    );
    const tree = makeMenuTree([
        { id: 1, name: "Alpha", xmlid: "app.alpha", actionID: 11 },
        { id: 2, name: "Beta", xmlid: "app.beta", actionID: 12 },
        { id: 3, name: "Gamma", xmlid: "app.gamma", actionID: 13 },
    ]);
    const service = await appMenuService.start({}, {
        menu: {
            getCurrentApp: () => null,
            getMenuAsTree: () => tree,
            selectMenu: () => {},
        },
    });
    const apps = service.getAppsMenuItems();
    expect(apps.map((a) => a.xmlid)).toEqual([
        "app.gamma", "app.alpha", "app.beta"
    ]);
});

test.tags("muk_web_appsbar");
test("app_menu service selectApp calls menu.selectMenu", async () => {
    const tree = makeMenuTree([{ 
        id: 1, 
        name: "Alpha", 
        xmlid: "app.alpha", 
        actionID: 11 
    }]);
    const menuCalls = [];
    const service = await appMenuService.start({}, {
        menu: {
            getCurrentApp: () => null,
            getMenuAsTree: () => tree,
            selectMenu: (app) => menuCalls.push(app),
        },
    });
    const [app] = service.getAppsMenuItems();
    service.selectApp(app);
    expect(menuCalls).toHaveLength(1);
    expect(menuCalls[0].xmlid).toBe("app.alpha");
});
