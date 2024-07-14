/** @odoo-module **/

import { StudioNavbar } from "@web_studio/client_action/navbar/navbar";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { click, getFixture, mount, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { registerStudioDependencies, openStudio, leaveStudio } from "./helpers";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { getActionManagerServerData, loadState } from "@web/../tests/webclient/helpers";
import { companyService } from "@web/webclient/company_service";
import { AppMenuEditor } from "@web_studio/client_action/editor/app_menu_editor/app_menu_editor";
import { NewModelItem } from "@web_studio/client_action/editor/new_model_item/new_model_item";

const serviceRegistry = registry.category("services");
let target;

QUnit.module("Studio > Navbar", (hooks) => {
    let baseConfig;
    hooks.beforeEach(() => {
        target = getFixture();
        registerStudioDependencies();
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("menu", menuService);
        serviceRegistry.add("hotkey", hotkeyService);
        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => {},
        });
        const menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: { id: 1, children: [10, 11, 12], name: "App0", appID: 1 },
            10: { id: 10, children: [], name: "Section 10", appID: 1 },
            11: { id: 11, children: [], name: "Section 11", appID: 1 },
            12: { id: 12, children: [120, 121, 122], name: "Section 12", appID: 1 },
            120: { id: 120, children: [], name: "Section 120", appID: 1 },
            121: { id: 121, children: [], name: "Section 121", appID: 1 },
            122: { id: 122, children: [], name: "Section 122", appID: 1 },
        };
        const serverData = { menus };
        baseConfig = { serverData };
    });

    QUnit.test("menu buttons will not be placed under 'more' menu", async (assert) => {
        assert.expect(12);

        const menuButtonsRegistry = registry.category("studio_navbar_menubuttons");
        // Force Navbar to contain those elements
        registerCleanup(() => {
            menuButtonsRegistry.remove("app_menu_editor");
            menuButtonsRegistry.remove("new_model_item");
        });

        class MyStudioNavbar extends StudioNavbar {
            async adapt() {
                const prom = super.adapt();
                const sectionsCount = this.currentAppSections.length;
                const hiddenSectionsCount = this.currentAppSectionsExtra.length;
                assert.step(`adapt -> hide ${hiddenSectionsCount}/${sectionsCount} sections`);
                return prom;
            }
        }

        const env = await makeTestEnv(baseConfig);
        patchWithCleanup(env.services.studio, {
            get mode() {
                // Will force the the navbar in the studio editor state
                return "editor";
            },
        });
        menuButtonsRegistry.add(
            "app_menu_editor",
            {
                Component: AppMenuEditor,
                props: { env },
            },
            { force: true }
        );
        menuButtonsRegistry.add("new_model_item", { Component: NewModelItem, props: { env } }, { force: true });
        // Force the parent width, to make this test independent of screen size
        target.style.width = "100%";

        // Set menu and mount
        env.services.menu.setCurrentMenu(1);
        await mount(MyStudioNavbar, target, { env });
        await nextTick();

        assert.containsN(
            target,
            ".o_menu_sections > *:not(.o_menu_sections_more):not(.d-none)",
            3,
            "should have 3 menu sections displayed (that are not the 'more' menu)"
        );
        assert.containsNone(target, ".o_menu_sections_more", "the 'more' menu should not exist");
        assert.containsN(
            target,
            ".o-studio--menu > *",
            2,
            "should have 2 studio menu elements displayed"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o-studio--menu > *")].map((el) => el.innerText),
            ["Edit Menu", "New Model"]
        );

        // Force minimal width and dispatch window resize event
        target.style.width = "0%";
        window.dispatchEvent(new Event("resize"));
        await nextTick();
        assert.containsOnce(
            target,
            ".o_menu_sections > *:not(.d-none)",
            "only one menu section should be displayed"
        );
        assert.containsOnce(
            target,
            ".o_menu_sections_more:not(.d-none)",
            "the displayed menu section should be the 'more' menu"
        );
        assert.containsN(
            target,
            ".o-studio--menu > *",
            2,
            "should have 2 studio menu elements displayed"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o-studio--menu > *")].map((el) => el.innerText),
            ["Edit Menu", "New Model"]
        );

        // Open the more menu
        await click(target, ".o_menu_sections_more .dropdown-toggle");
        assert.deepEqual(
            [...target.querySelectorAll(".dropdown-menu > *")].map((el) => el.textContent),
            ["Section 10", "Section 11", "Section 12", "Section 120", "Section 121", "Section 122"],
            "'more' menu should contain all hidden sections in correct order"
        );

        // Check the navbar adaptation calls
        assert.verifySteps(["adapt -> hide 0/3 sections", "adapt -> hide 3/3 sections"]);
    });

    QUnit.test("homemenu customizer rendering", async (assert) => {
        assert.expect(6);

        serviceRegistry.add("company", companyService);

        const fakeHTTPService = {
            start() {
                return {};
            },
        };
        serviceRegistry.add("http", fakeHTTPService);

        const env = await makeTestEnv(baseConfig);

        patchWithCleanup(env.services.studio, {
            get mode() {
                // Will force the navbar in the studio home_menu state
                return "home_menu";
            },
        });

        const target = getFixture();

        // Set menu and mount
        await mount(StudioNavbar, target, { env });
        await nextTick();

        assert.containsOnce(target, ".o_studio_navbar");
        assert.containsOnce(target, ".o_web_studio_home_studio_menu");

        await click(target.querySelector(".o_web_studio_home_studio_menu .dropdown-toggle"));

        assert.containsOnce(target, ".o_web_studio_change_background");
        assert.strictEqual(
            target.querySelector(".o_web_studio_change_background input").accept,
            "image/*",
            "Input should now only accept images"
        );

        assert.containsOnce(target, ".o_web_studio_import");
        assert.containsOnce(target, ".o_web_studio_export");
    });
});

QUnit.module("Studio > navbar coordination", (hooks) => {
    let serverData;
    let target;
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = getActionManagerServerData();
        registerStudioDependencies();
        serviceRegistry.add("company", companyService);
    });

    QUnit.test("adapt navbar when leaving studio", async (assert) => {
        assert.expect(8);

        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => {},
        });
        target.style.width = "1120px";

        serverData.menus[1].actionID = 1;
        serverData.actions[1].xml_id = "action_xml_id";

        const webClient = await createEnterpriseWebClient({ serverData });
        const width = document.body.style.width;
        document.body.style.width = "1120px";
        registerCleanup(() => {
            document.body.style.width = width;
        });

        window.dispatchEvent(new Event("resize"));
        await nextTick();
        await nextTick();
        await click(target.querySelector(".o_app[data-menu-xmlid=menu_1]"));
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_menu_sections .o_menu_sections_more");

        await openStudio(target);
        await nextTick();
        await nextTick();
        await nextTick();
        assert.containsOnce(target, ".o_studio .o_menu_sections");
        assert.containsNone(target, ".o_studio .o_menu_sections .o_menu_sections_more");

        Object.assign(serverData.menus, {
            10: {
                id: 10,
                children: [],
                name: "The chain",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            11: {
                id: 11,
                children: [111],
                name: "Running in the shadows, damn your love, damn your lies",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            12: {
                id: 12,
                children: [],
                name: "You would never break the chain (Never break the chain)",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            13: {
                id: 13,
                children: [],
                name: "Chain keep us together (running in the shadow)",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            111: {
                id: 111,
                children: [],
                name: "You will never love me again",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
        });
        serverData.menus[1].children = [10, 11, 12, 13];
        await webClient.env.services.menu.reload();
        // two ticks to allow the navbar to adapt
        await nextTick();
        await nextTick();
        assert.strictEqual(
            target.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length,
            3
        );
        assert.containsOnce(target, ".o_studio .o_menu_sections .o_menu_sections_more");

        await leaveStudio(target);
        // two more ticks to allow the navbar to adapt
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_studio");
        assert.strictEqual(
            target.querySelectorAll("header .o_menu_sections > *:not(.d-none)").length,
            4
        );
        assert.containsOnce(target, ".o_menu_sections .o_menu_sections_more");
    });

    QUnit.test("adapt navbar when refreshing studio (loadState)", async (assert) => {
        assert.expect(7);

        target.style.width = "800px";

        const adapted = [];
        patchWithCleanup(StudioNavbar.prototype, {
            async adapt() {
                const prom = super.adapt();
                adapted.push(prom);
                return prom;
            },
        });

        serverData.menus[1].actionID = 1;
        serverData.actions[1].xml_id = "action_xml_id";
        serverData.actions[1].id = 1;
        serverData.menus[1].children = [10, 11, 12, 13];

        Object.assign(serverData.menus, {
            10: {
                id: 10,
                children: [],
                name: "The chain",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            11: {
                id: 11,
                children: [111],
                name: "Running in the shadows, damn your love, damn your lies",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            12: {
                id: 12,
                children: [],
                name: "You would never break the chain (Never break the chain)",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            13: {
                id: 13,
                children: [],
                name: "Chain keep us together (running in the shadow)",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
            111: {
                id: 111,
                children: [],
                name: "You will never love me again",
                appID: 1,
                actionID: 1001,
                xmlid: "menu_1",
            },
        });

        const webClient = await createEnterpriseWebClient({ serverData });

        window.dispatchEvent(new Event("resize"));
        await Promise.all(adapted);
        await click(target.querySelector(".o_app[data-menu-xmlid=menu_1]"));
        await Promise.all(adapted);
        await nextTick();
        await nextTick();
        assert.containsNone(target, ".o_studio");
        assert.strictEqual(
            target.querySelectorAll("header .o_menu_sections > *:not(.d-none)").length,
            3
        );
        assert.containsOnce(target, ".o_menu_sections .o_menu_sections_more");

        await openStudio(target);
        await Promise.all(adapted);
        await nextTick();
        assert.strictEqual(
            target.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length,
            2
        );
        assert.containsOnce(target, ".o_studio .o_menu_sections .o_menu_sections_more");

        await nextTick();
        const state = webClient.env.services.router.current.hash;
        await loadState(webClient, state);
        await Promise.all(adapted);
        await nextTick();
        assert.strictEqual(
            target.querySelectorAll(".o_studio header .o_menu_sections > *:not(.d-none)").length,
            2
        );
        assert.containsOnce(target, ".o_studio .o_menu_sections .o_menu_sections_more");
    });
});
