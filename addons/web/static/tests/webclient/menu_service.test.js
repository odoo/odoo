// @ts-check

import "@web/webclient/menus/menu_providers";

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    getService,
    makeMockEnv,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { redirect } from "@web/core/utils/urls";
import { session } from "@web/session";
import { menuStorage } from "@web/webclient/menus/menu_storage";
import { menuUsage } from "@web/webclient/menus/menu_usage";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_utils";

defineActions([
    {
        id: 666,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[false, "kanban"]],
    },
]);

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();

    _records = [
        { id: 1, name: "First record", foo: "yop" },
        { id: 2, name: "Second record", foo: "blip" },
        { id: 3, name: "Third record", foo: "gnap" },
        { id: 4, name: "Fourth record", foo: "plop" },
        { id: 5, name: "Fifth record", foo: "zoup" },
    ];
    _views = {
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `<list><field name="foo"/></list>`,
        form: `
            <form>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>
        `,
        search: `<search><field name="foo" string="Foo"/></search>`,
    };
}
const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels([Partner, ResCompany, ResPartner, ResUsers]);
defineMenus([
    {
        id: 1,
        children: [
            { id: 2, name: "Test1", appID: 1, actionID: 666 },
            { id: 3, name: "Test2", appID: 1, actionID: 666 },
        ],
        name: "App1",
        appID: 1,
        actionID: 666,
    },
]);

test.tags("desktop");
test(`use stored menus, and don't update on load_menus return (if identical)`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", () => def);

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [2, 3], name: "App1", id: 1, actionID: 666 },
        2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
        3: { appID: 1, children: [], name: "Test2", id: 3, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () =>
        expect.step("Don't Update"),
    );
    expect(`.o_menu_brand`).toHaveText("App1");
    expect(browser.sessionStorage.getItem("menu_id")).toBe("1");
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect.verifySteps([]);
});

test.tags("desktop");
test(`send stored hash and keep stored menus on 304 not modified`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", async (request) => {
        expect.step(`hash=${new URL(request.url).searchParams.get("hash")}`);
        await def;
        return new Response(null, { status: 304 });
    });

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus_hash = "abcdef123456";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [2, 3], name: "App1", id: 1, actionID: 666 },
        2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
        3: { appID: 1, children: [], name: "Test2", id: 3, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () =>
        expect.step("Don't Update"),
    );
    expect(`.o_menu_brand`).toHaveText("App1");
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect.verifySteps(["hash=abcdef123456"]);
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect(browser.localStorage.webclient_menus_hash).toBe("abcdef123456");
    expect.verifySteps([]);
});

test.tags("desktop");
test(`update menus and persist new hash on changed payload`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", async (request) => {
        expect.step(`hash=${new URL(request.url).searchParams.get("hash")}`);
        await def;
        return new Response(
            JSON.stringify({
                1: { appID: 1, children: [2], name: "App1", id: 1, actionID: 666 },
                2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
                root: { id: "root", name: "root", appID: "root", children: [1] },
            }),
            { headers: { "X-Menus-Hash": "newhash789" } },
        );
    });

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus_hash = "oldhash123";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [2, 3], name: "App1", id: 1, actionID: 666 },
        2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
        3: { appID: 1, children: [], name: "Test2", id: 3, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () =>
        expect.step("Update Menus"),
    );
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect.verifySteps(["hash=oldhash123"]);
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1");
    expect(browser.localStorage.webclient_menus_hash).toBe("newhash789");
    expect.verifySteps(["Update Menus"]);
});

test.tags("desktop");
test(`use stored menus, and update on load_menus return`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", () => def);

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { id: 1, children: [2], name: "App1", appID: 1, actionID: 666 },
        2: { id: 2, children: [], name: "Test1", appID: 1, actionID: 666 },
        root: { id: "root", children: [1], name: "root", appID: "root" },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () =>
        expect.step("Update Menus"),
    );
    expect(`.o_menu_brand`).toHaveText("App1");
    expect(browser.sessionStorage.getItem("menu_id")).toBe("1");
    expect(".o_menu_sections").toHaveText("Test1");
    expect.verifySteps([]);
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect(menuStorage.parse(browser.localStorage.webclient_menus)).toEqual({
        1: {
            actionID: 666,
            appID: 1,
            children: [2, 3],
            id: 1,
            name: "App1",
        },
        2: {
            actionID: 666,
            appID: 1,
            children: [],
            id: 2,
            name: "Test1",
        },
        3: {
            actionID: 666,
            appID: 1,
            children: [],
            id: 3,
            name: "Test2",
        },
        root: {
            appID: "root",
            children: [1],
            id: "root",
            name: "root",
        },
    });
    expect.verifySteps(["Update Menus"]);
});

test.tags("desktop");
test(`stale background revalidation cannot overwrite a fresher reload()`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", async (request) => {
        if (new URL(request.url).searchParams.get("hash")) {
            await def;
            return new Response(
                JSON.stringify({
                    1: {
                        appID: 1,
                        children: [],
                        name: "StaleApp",
                        id: 1,
                        actionID: 666,
                    },
                    root: { id: "root", name: "root", appID: "root", children: [1] },
                }),
                { headers: { "X-Menus-Hash": "stalehash" } },
            );
        }
        return new Response(
            JSON.stringify({
                1: { appID: 1, children: [], name: "FreshApp", id: 1, actionID: 666 },
                root: { id: "root", name: "root", appID: "root", children: [1] },
            }),
            { headers: { "X-Menus-Hash": "freshhash" } },
        );
    });

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus_hash = "boothash";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "StoredApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });

    await mountWebClient();
    await getService("menu").reload();
    expect(getService("menu").getMenu(1).name).toBe("FreshApp");

    def.resolve();
    await animationFrame();
    expect(getService("menu").getMenu(1).name).toBe("FreshApp");
    expect(browser.localStorage.webclient_menus_hash).toBe("freshhash");
    expect(menuStorage.parse(browser.localStorage.webclient_menus)[1].name).toBe(
        "FreshApp",
    );
});

test.tags("desktop");
test(`total menu fetch failure falls back to an empty root`, async () => {
    const preload = Promise.reject(new Error("preload failed"));
    preload.catch(() => {});
    patchWithCleanup(odoo, /** @type {any} */ ({ loadMenusPromise: preload }));
    onRpc("/web/webclient/load_menus", () => {
        throw new Error("load_menus unavailable");
    });
    await makeMockEnv();
    expect(getService("menu").getApps()).toEqual([]);
    expect(getService("menu").getAll().length).toBe(1);
    expect(getService("menu").getMenu("root").children).toEqual([]);
});

test.tags("desktop");
test(`corrupt stored menus are discarded and refetched (no boot brick)`, async () => {
    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = '{"1": {"appID": 1, TRUNCATED';
    browser.localStorage.webclient_menus_hash = "abcdef123456";

    await makeMockEnv();

    expect(
        getService("menu")
            .getApps()
            .map((app) => app.name),
    ).toEqual(["App1"]);
    const stored = browser.localStorage.getItem("webclient_menus");
    expect(stored).not.toBe('{"1": {"appID": 1, TRUNCATED');
    expect(menuStorage.parse(stored).root.id).toBe("root");
});

test.tags("desktop");
test(`cold boot: a null parse-time preload refetches menus (no blank client)`, async () => {
    patchWithCleanup(
        odoo,
        /** @type {any} */ ({ loadMenusPromise: Promise.resolve(null) }),
    );
    await makeMockEnv();
    expect(
        getService("menu")
            .getApps()
            .map((app) => app.name),
    ).toEqual(["App1"]);
});

test.tags("desktop");
test(`a preload of nothing is an opt-out, not a cache miss`, async () => {
    patchWithCleanup(
        odoo,
        /** @type {any} */ ({ loadMenusPromise: Promise.resolve() }),
    );
    onRpc("/web/webclient/load_menus", () => {
        expect.step("load_menus");
        return { root: { id: "root", name: "root", appID: "root", children: [] } };
    });
    await makeMockEnv();
    expect.verifySteps([]);
    expect(getService("menu").getApps()).toEqual([]);
    expect(getService("menu").getMenu("root").children).toEqual([]);
});

test.tags("desktop");
test(`cold boot: falls back to stored menus when preload is null and refetch fails`, async () => {
    menuStorage.write({
        1: { appID: 1, children: [], name: "StoredApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    browser.localStorage.webclient_menus_version = "stale-version-hash";
    patchWithCleanup(
        odoo,
        /** @type {any} */ ({ loadMenusPromise: Promise.resolve(null) }),
    );
    onRpc("/web/webclient/load_menus", () => {
        throw new Error("load_menus unavailable");
    });
    await makeMockEnv();
    expect(
        getService("menu")
            .getApps()
            .map((app) => app.name),
    ).toEqual(["StoredApp"]);
});

test.tags("desktop");
test(`cold boot: another user's stored menus are never served, even as a last resort`, async () => {
    browser.localStorage.webclient_menus_version = `${CURRENT_REGISTRY_HASH}:99`;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "OtherUserApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    patchWithCleanup(
        odoo,
        /** @type {any} */ ({ loadMenusPromise: Promise.resolve(null) }),
    );
    onRpc("/web/webclient/load_menus", () => {
        throw new Error("load_menus unavailable");
    });
    await makeMockEnv();
    expect(getService("menu").getApps()).toEqual([]);
    expect(getService("menu").getMenu("root").children).toEqual([]);
});

test("getAppIdByAction prefers the given app when several share the action", async () => {
    defineMenus([
        { id: 0 },
        { id: 200, name: "Accounting", appID: 200, children: [201] },
        { id: 201, name: "Customers", appID: 200, actionID: 9001, parent_id: 200 },
        { id: 100, name: "Sale", appID: 100, children: [101] },
        { id: 101, name: "Customers", appID: 100, actionID: 9001, parent_id: 100 },
    ]);
    const env = await makeMockEnv();
    const menuService = env.services.menu;

    expect(menuService.getAppIdByAction(9001, 100)).toBe(100);
    expect(menuService.getAppIdByAction(9001, 200)).toBe(200);
    expect(menuService.getAppIdByAction(9001)).toBe(100);
    expect(menuService.getAppIdByAction(9001, 999)).toBe(100);
    expect(menuService.getAppIdByAction(4242)).toBe(undefined);
});

test("getAppIdByAction matches an action path, not just an id", async () => {
    defineMenus([
        { id: 0 },
        { id: 300, name: "Website", appID: 300, children: [301] },
        {
            id: 301,
            name: "Pages",
            appID: 300,
            actionID: 9002,
            actionPath: "website-pages",
            parent_id: 300,
        },
    ]);
    const env = await makeMockEnv();

    expect(env.services.menu.getAppIdByAction("website-pages")).toBe(300);
    expect(env.services.menu.getAppIdByAction(9002)).toBe(300);
});

test("the action index is rebuilt when the menu tree is reloaded", async () => {
    defineMenus([
        { id: 0 },
        { id: 100, name: "Sale", appID: 100, children: [101] },
        { id: 101, name: "Customers", appID: 100, actionID: 9001, parent_id: 100 },
    ]);
    const env = await makeMockEnv();
    const menuService = env.services.menu;

    expect(menuService.getAppIdByAction(9001)).toBe(100);

    onRpc("/web/webclient/load_menus", () => ({
        root: { id: "root", children: [500], name: "root", appID: "root" },
        500: { id: 500, name: "Inventory", appID: 500, children: [501] },
        501: {
            id: 501,
            name: "Products",
            appID: 500,
            actionID: 9001,
            children: [],
            parent_id: 500,
        },
    }));
    await menuService.reload();

    expect(menuService.getAppIdByAction(9001)).toBe(500);
});

test("the command palette's empty query lists what the user opens first", async () => {
    defineMenus(
        [
            {
                id: 100,
                name: "Sale",
                appID: 100,
                actionID: 9001,
                xmlid: "app.sale",
                children: [
                    {
                        id: 101,
                        name: "Quotations",
                        appID: 100,
                        actionID: 9003,
                        xmlid: "menu.quotations",
                    },
                ],
            },
            { id: 200, name: "Stock", appID: 200, actionID: 9002, xmlid: "app.stock" },
        ],
        { mode: "replace" },
    );
    const env = await makeMockEnv();
    const provider = registry.category("command_provider").get("menu");
    menuUsage.clear();

    let names = (await provider.provide(env, { searchValue: "" })).map((c) => c.name);
    expect(names).toEqual(["Sale", "Stock"]);

    menuUsage.record({ xmlid: "app.stock" });
    menuUsage.record({ xmlid: "menu.quotations" });
    names = (await provider.provide(env, { searchValue: "" })).map((c) => c.name);
    expect(names).toEqual(["Sale / Quotations", "Stock", "Sale"]);

    names = (await provider.provide(env, { searchValue: "sto" })).map((c) => c.name);
    expect(names).toEqual(["Stock"], {
        message: "a query ranks by match, not by use",
    });
    menuUsage.clear();
});

test("the command palette's flattened menu list follows a reload", async () => {
    defineMenus([
        { id: 0 },
        { id: 100, name: "Sale", appID: 100, actionID: 9001, children: [] },
    ]);
    const env = await makeMockEnv();
    const provider = registry.category("command_provider").get("menu");

    let names = (await provider.provide(env, { searchValue: "" })).map((c) => c.name);
    expect(names).toInclude("Sale");
    expect(names).not.toInclude("Inventory");

    onRpc("/web/webclient/load_menus", () => ({
        root: { id: "root", children: [500], name: "root", appID: "root" },
        500: {
            id: 500,
            name: "Inventory",
            appID: 500,
            actionID: 9002,
            children: [],
        },
    }));
    await env.services.menu.reload();

    names = (await provider.provide(env, { searchValue: "" })).map((c) => c.name);
    expect(names).toInclude("Inventory");
    expect(names).not.toInclude("Sale");
});

const CURRENT_REGISTRY_HASH =
    "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0";
const STORED_MENU_VERSION = `${CURRENT_REGISTRY_HASH}:7`;

test.tags("desktop");
test(`a version-mismatched cache is not served, even though it parses`, async () => {
    redirect("/odoo/action-666");
    browser.localStorage.webclient_menus_version = "a-previous-registry-hash";
    browser.localStorage.webclient_menus_hash = "stale-hash-abc";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "StaleApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    onRpc("/web/webclient/load_menus", (request) => {
        expect.step(`hash=${new URL(request.url).searchParams.get("hash")}`);
        return {
            1: { appID: 1, children: [], name: "FreshApp", id: 1, actionID: 666 },
            root: { id: "root", name: "root", appID: "root", children: [1] },
        };
    });

    await mountWebClient();

    expect.verifySteps(["hash=null"]);
    expect(`.o_menu_brand`).toHaveText("FreshApp");
    expect(browser.localStorage.webclient_menus_version).toBe(STORED_MENU_VERSION);
});

test.tags("desktop");
test(`a failed payload write closes the version gate`, async () => {
    redirect("/odoo/action-666");
    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "StaleApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    onRpc("/web/webclient/load_menus", () => ({
        1: { appID: 1, children: [], name: "FreshApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    }));
    patchWithCleanup(browser.localStorage, {
        setItem(key, value) {
            if (key === "webclient_menus") {
                throw new Error("QuotaExceededError");
            }
            return super.setItem(key, value);
        },
    });

    await mountWebClient();
    await animationFrame();

    expect(browser.localStorage.webclient_menus_version).not.toBe(STORED_MENU_VERSION);
});

test.tags("desktop");
test("a cached menu tree with dangling child ids does not crash the consumers", async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", () => def);

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [2, 999], name: "App1", id: 1, actionID: 666 },
        2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1, 998] },
    });

    await mountWebClient();
    const menuService = getService("menu");

    expect(menuService.getApps().every(Boolean)).toBe(true);
    expect(menuService.getApps().map((a) => a.id)).toEqual([1]);

    const app = menuService.getMenuAsTree(1);
    expect(app.childrenTree.every(Boolean)).toBe(true);
    expect(app.childrenTree.map((c) => c.id)).toEqual([2]);
    expect(() =>
        computeAppsAndMenuItems(menuService.getMenuAsTree("root")),
    ).not.toThrow();

    def.resolve();
});

test.tags("desktop");
test("a cached menu payload with no root entry degrades instead of crashing", async () => {
    onRpc("/web/webclient/load_menus", () => {
        throw new Error("offline");
    });

    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "App1", id: 1, actionID: 666 },
    });

    await makeMockEnv();
    const menuService = getService("menu");

    expect(menuService.getApps()).toEqual([]);
    expect(menuService.getMenuAsTree("root")).not.toBe(undefined);
    expect(() =>
        computeAppsAndMenuItems(menuService.getMenuAsTree("root")),
    ).not.toThrow();
});

test.tags("desktop");
test(`menu cache is scoped per user on a shared browser`, async () => {
    browser.localStorage.webclient_menus_version = STORED_MENU_VERSION;
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [], name: "UserSevenApp", id: 1, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    expect(menuStorage.read().menus).not.toBe(null);
    patchWithCleanup(user, { userId: 99 });
    patchWithCleanup(session, {
        menus_cache_version: `${CURRENT_REGISTRY_HASH}:99`,
    });
    const read = menuStorage.read();
    expect(read.menus).toBe(null);
    expect(read.raw).toBe(null, {
        message: "another user's payload must be discarded, not merely not served",
    });
});

test("stale menu fallback is scoped to database and user; legacy caches cannot fall back", () => {
    patchWithCleanup(session, { db: "database_a", menus_cache_version: "a:2" });
    patchWithCleanup(user, { userId: 2 });
    menuStorage.write({ root: { children: [] } }, "hash");
    patchWithCleanup(session, { menus_cache_version: "new:2" });
    expect(menuStorage.read().raw).not.toBe(null);
    patchWithCleanup(session, { db: "database_b" });
    expect(menuStorage.read().raw).toBe(null);
    patchWithCleanup(session, { db: "database_a" });
    patchWithCleanup(user, { userId: 3 });
    expect(menuStorage.read().raw).toBe(null);
    patchWithCleanup(user, { userId: 2 });
    browser.localStorage.webclient_menus = JSON.stringify({ root: { children: [] } });
    expect(menuStorage.read().raw).toBe(null);
});

test("valid JSON with invalid menu structure is discarded", () => {
    for (const raw of [
        "null",
        "[]",
        '{"root":{"children":{}}}',
        '{"root":{"children":[]},"1":null}',
    ]) {
        browser.localStorage.webclient_menus = raw;
        expect(menuStorage.parse(raw)).toBe(null);
        expect(browser.localStorage.getItem("webclient_menus")).toBe(null);
    }
});
