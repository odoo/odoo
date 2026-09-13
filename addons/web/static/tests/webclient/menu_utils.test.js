// @ts-check

import { expect, test } from "@odoo/hoot";
import { registry } from "@web/core/registry";
import {
    computeAppsAndMenuItems,
    flattenMenuTree,
    isDefaultHomeMenuConfig,
    menuSearchKey,
    parseHomeMenuConfig,
    reorderApps,
    serializeHomeMenuConfig,
} from "@web/webclient/menus/menu_utils";

/** @param {string[]} xmlids */
function makeApps(xmlids) {
    return xmlids.map((xmlid) => ({ xmlid }));
}

/** @param {{xmlid: string}[]} apps */
function xmlids(apps) {
    return apps.map((a) => a.xmlid);
}

test("reorderApps sorts apps by the given custom order", () => {
    const apps = makeApps(["a", "b", "c"]);
    reorderApps(apps, ["c", "a", "b"]);
    expect(xmlids(apps)).toEqual(["c", "a", "b"]);
});

test("reorderApps keeps the original relative order of apps absent from the order", () => {
    const apps = makeApps(["a", "b", "c", "d"]);
    reorderApps(apps, ["d", "b"]);
    expect(xmlids(apps)).toEqual(["a", "c", "d", "b"]);
});

test("reorderApps: a newly installed app does not scramble the customized order", () => {
    const apps = makeApps(["e1", "e2", "e3", "new"]);
    reorderApps(apps, ["e3", "e1", "e2"]);
    expect(xmlids(apps)).toEqual(["new", "e3", "e1", "e2"]);
});

/** @param {any[]} spec */
function makeTree(spec) {
    /**
     * @param {any} node
     * @param {number | undefined} appID
     * @returns {any}
     */
    const build = (node, appID) => {
        const id = node.id;
        const ownAppID = appID ?? id;
        return {
            id,
            name: node.name,
            xmlid: node.xmlid,
            appID: ownAppID,
            actionID: node.actionID,
            actionPath: node.actionPath,
            webIcon: node.webIcon,
            webIconData: node.webIconData,
            childrenTree: (node.children || []).map((/** @type {any} */ c) =>
                build(c, id === ownAppID && appID === undefined ? id : ownAppID),
            ),
        };
    };
    return {
        id: "root",
        name: "root",
        appID: "root",
        childrenTree: spec.map((app) => build(app, undefined)),
    };
}

test("computeAppsAndMenuItems splits apps from their descendants", () => {
    const tree = makeTree([
        {
            id: 1,
            name: "Sales",
            xmlid: "sale.menu_root",
            actionID: 10,
            webIconData: "data:image/png;base64,AAA",
            children: [
                { id: 2, name: "Orders", actionID: 11 },
                { id: 3, name: "Products", actionID: 12 },
            ],
        },
    ]);
    const { apps, menuItems } = computeAppsAndMenuItems(tree);
    expect(apps.map((a) => a.label)).toEqual(["Sales"]);
    expect(menuItems.map((m) => m.label)).toEqual(["Orders", "Products"]);
    expect(apps[0].webIconData).toBe("data:image/png;base64,AAA");
});

test("computeAppsAndMenuItems records the ancestor path and the owning app", () => {
    const tree = makeTree([
        {
            id: 1,
            name: "Sales",
            actionID: 10,
            children: [
                {
                    id: 2,
                    name: "Configuration",
                    actionID: 11,
                    children: [{ id: 3, name: "Tags", actionID: 12 }],
                },
            ],
        },
    ]);
    const { menuItems } = computeAppsAndMenuItems(tree);
    const tags = menuItems.find((m) => m.label === "Tags");
    expect(tags?.parents).toBe("Sales / Configuration");
    expect(tags?.appID).toBe(1);
});

test("computeAppsAndMenuItems skips nodes without an action", () => {
    const tree = makeTree([
        {
            id: 1,
            name: "Sales",
            actionID: 10,
            children: [{ id: 2, name: "No action" }],
        },
    ]);
    const { apps, menuItems } = computeAppsAndMenuItems(tree);
    expect(apps).toHaveLength(1);
    expect(menuItems).toEqual([]);
});

test("computeAppsAndMenuItems parses webIcon and falls back to the default", () => {
    const tree = makeTree([
        { id: 1, name: "Styled", actionID: 10, webIcon: "fa-cog,#fff,#000" },
        { id: 2, name: "Bare", actionID: 20, webIcon: "fa-cog" },
        { id: 3, name: "None", actionID: 30 },
    ]);
    const { apps } = computeAppsAndMenuItems(tree);
    expect(apps[0].webIcon).toEqual({
        iconClass: "fa-cog",
        color: "#fff",
        backgroundColor: "#000",
    });
    expect(apps[1].webIconData).toBe("/web/static/img/default_icon_app.png");
    expect(apps[2].webIconData).toBe("/web/static/img/default_icon_app.png");
});

test("computeAppsAndMenuItems builds hrefs from the action path when present", () => {
    const tree = makeTree([
        {
            id: 1,
            name: "Sales",
            actionID: 10,
            actionPath: "sales",
            children: [{ id: 2, name: "Orders", actionID: 11 }],
        },
    ]);
    const { apps, menuItems } = computeAppsAndMenuItems(tree);
    expect(apps[0].href).toBe("/odoo/sales");
    expect(menuItems[0].href).toBe("/odoo/action-11");
});

test("computeAppsAndMenuItems handles a subtree that is not rooted at root", () => {
    const app = makeTree([
        {
            id: 1,
            name: "Sales",
            actionID: 10,
            children: [{ id: 2, name: "Orders", actionID: 11 }],
        },
    ]).childrenTree[0];
    const { apps, menuItems } = computeAppsAndMenuItems(app);
    expect(apps.map((a) => a.label)).toEqual(["Sales"]);
    expect(menuItems.map((m) => m.label)).toEqual(["Orders"]);
});

test("parseHomeMenuConfig reads the version-1 bare order list", () => {
    expect(parseHomeMenuConfig('["app.b","app.a"]')).toEqual({
        order: ["app.b", "app.a"],
        pinned: [],
        hidden: [],
    });
    expect(parseHomeMenuConfig(["app.a"])).toEqual({
        order: ["app.a"],
        pinned: [],
        hidden: [],
    });
});

test("parseHomeMenuConfig reads the versioned object and drops what is not an xmlid", () => {
    expect(
        parseHomeMenuConfig(
            '{"version":2,"order":["app.a",3],"pinned":["app.b"],"hidden":null}',
        ),
    ).toEqual({ order: ["app.a"], pinned: ["app.b"], hidden: [] });
});

test("parseHomeMenuConfig treats nothing and garbage as the default layout", () => {
    for (const raw of [undefined, null, "", "null", "{", 42, "[1,2]"]) {
        const config = parseHomeMenuConfig(raw);
        expect(config).toEqual({ order: [], pinned: [], hidden: [] });
        expect(isDefaultHomeMenuConfig(config)).toBe(true);
    }
});

test("serializeHomeMenuConfig round-trips through parseHomeMenuConfig", () => {
    const config = { order: ["app.b", "app.a"], pinned: ["app.a"], hidden: ["app.c"] };
    const raw = serializeHomeMenuConfig(config);
    expect(JSON.parse(raw).version).toBe(2);
    expect(parseHomeMenuConfig(raw)).toEqual(config);
    expect(isDefaultHomeMenuConfig(config)).toBe(false);
});

test("computeAppsAndMenuItems names the addon an app's icon comes from", () => {
    const tree = {
        id: "root",
        name: "root",
        appID: "root",
        childrenTree: [
            {
                id: 1,
                name: "CRM",
                appID: 1,
                actionID: 10,
                webIcon: "crm,static/description/icon.png",
                webIconData: "data:image/png;base64,AAA",
                childrenTree: /** @type {any[]} */ ([]),
            },
            {
                id: 2,
                name: "Studio App",
                appID: 2,
                actionID: 20,
                webIcon: "fa fa-leaf,#fff,#123456",
                childrenTree: /** @type {any[]} */ ([]),
            },
        ],
    };
    const { apps } = computeAppsAndMenuItems(tree);
    expect(apps[0].module).toBe("crm");
    expect(apps[1].module).toBe(undefined);
});

test("computeAppsAndMenuItems lists the models an app's menus open", () => {
    const tree = {
        id: "root",
        name: "root",
        appID: "root",
        childrenTree: [
            {
                id: 1,
                name: "Sales",
                appID: 1,
                actionID: 10,
                actionResModel: "sale.order",
                webIcon: "sale,static/description/icon.png",
                childrenTree: [
                    {
                        id: 2,
                        name: "Customers",
                        appID: 1,
                        actionID: 11,
                        actionResModel: "res.partner",
                        childrenTree: /** @type {any[]} */ ([]),
                    },
                    {
                        id: 3,
                        name: "Reporting",
                        appID: 1,
                        actionID: 12,
                        actionResModel: false,
                        childrenTree: [
                            {
                                id: 4,
                                name: "Sales Analysis",
                                appID: 1,
                                actionID: 13,
                                actionResModel: "sale.order",
                                childrenTree: /** @type {any[]} */ ([]),
                            },
                        ],
                    },
                ],
            },
        ],
    };
    const { apps } = computeAppsAndMenuItems(tree);
    expect(apps[0].models).toEqual(["sale.order", "res.partner"]);
});

test("flattenMenuTree walks a tree once and hands every caller the same result", () => {
    const tree = makeTree([
        {
            id: 1,
            name: "Sales",
            xmlid: "sale.menu_root",
            actionID: 10,
            children: [{ id: 2, name: "Orders", actionID: 11 }],
        },
    ]);
    const first = flattenMenuTree(tree);
    const second = flattenMenuTree(tree);
    expect(second).toBe(first, {
        message: "the home menu and the command palette share one traversal",
    });
    expect(second.apps).toBe(first.apps);
    expect(flattenMenuTree(makeTree([]))).not.toBe(first);
});

test("reordering a flattened tree's apps is the caller's copy, never the shared array", () => {
    const tree = makeTree([
        { id: 1, name: "Sales", xmlid: "a", actionID: 10 },
        { id: 2, name: "Purchase", xmlid: "b", actionID: 11 },
    ]);
    const shared = flattenMenuTree(tree).apps;
    const mine = [...shared];
    reorderApps(mine, ["b", "a"]);
    expect(mine.map((a) => a.xmlid)).toEqual(["b", "a"]);
    expect(shared.map((a) => a.xmlid)).toEqual(["a", "b"], {
        message: "one launcher's layout does not reorder another consumer's apps",
    });
});

test("menuSearchKey puts a menu's own name before its ancestors, normalized", () => {
    const menu = { parents: "Sales / Órders", label: "Quotations" };
    expect(menuSearchKey(menu)).toBe(" quotations/ orders /sales ");
    expect(menuSearchKey(menu)).toBe(menuSearchKey(menu), {
        message: "computed once per entry, so a keystroke re-normalizes nothing",
    });
});

test("a launcher's stored order never reaches the command palette, which shares the flatten", async () => {
    const tree = makeTree([
        { id: 1, name: "Alpha", xmlid: "a", actionID: 10 },
        { id: 2, name: "Beta", xmlid: "b", actionID: 11 },
        { id: 3, name: "Gamma", xmlid: "c", actionID: 12 },
    ]);
    const shared = flattenMenuTree(tree).apps;
    expect(shared.map((a) => a.xmlid)).toEqual(["a", "b", "c"]);

    const mine = [...shared];
    reorderApps(mine, ["c", "b", "a"]);
    expect(mine.map((a) => a.xmlid)).toEqual(["c", "b", "a"]);
    expect(flattenMenuTree(tree).apps.map((a) => a.xmlid)).toEqual(["a", "b", "c"], {
        message: "the shared array is still in menu order",
    });

    const provider = registry.category("command_provider").get("menu");
    const result = await provider.provide(
        { services: { menu: { getMenuAsTree: () => tree } } },
        { searchValue: "" },
    );
    const names = result.filter((r) => r.category === "apps").map((r) => r.name);
    expect(names).toEqual(["Alpha", "Beta", "Gamma"], {
        message: "the palette lists apps in menu order regardless",
    });
});

test("layout normalization deduplicates IDs, rejects unknown versions, and excludes hidden pins", () => {
    expect(
        parseHomeMenuConfig({
            version: 2,
            order: ["a", "a", "", 7],
            pinned: ["a", "b", "b"],
            hidden: ["a", "a"],
        }),
    ).toEqual({ order: ["a"], pinned: ["b"], hidden: ["a"] });
    expect(parseHomeMenuConfig({ version: 99, pinned: ["a"] })).toEqual({
        order: [],
        pinned: [],
        hidden: [],
    });
});

test("app ownership and search terms survive icon customization", () => {
    const app = {
        id: 1,
        appID: 1,
        name: "Inventory",
        actionID: 1,
        xmlid: "stock.menu_stock_root",
        webIcon: "fa fa-cubes,#ffffff,#000000",
        childrenTree: /** @type {any[]} */ ([]),
    };
    const { apps } = computeAppsAndMenuItems({ childrenTree: [app] });
    expect(apps[0].module).toBe("stock");
    expect(apps[0].searchTerms).toInclude("stock");
});

test("rank lookup preserves first duplicate rank and stable unranked order", () => {
    const apps = makeApps(["unknown1", "b", "a", "unknown2"]);
    reorderApps(apps, ["a", "b", "a"]);
    expect(xmlids(apps)).toEqual(["unknown1", "unknown2", "a", "b"]);
});
