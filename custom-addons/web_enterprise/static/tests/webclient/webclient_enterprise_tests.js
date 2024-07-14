/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    nextTick,
    patchWithCleanup,
    mount,
} from "@web/../tests/helpers/utils";
import { doAction, getActionManagerServerData, loadState } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { editView } from "@web/views/debug_items";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { browser } from "@web/core/browser/browser";
import { errorService } from "@web/core/errors/error_service";
import { session } from "@web/session";
import { shareUrlMenuItem } from "@web_enterprise/webclient/share_url/share_url";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

import { Component, onMounted, xml } from "@odoo/owl";

let serverData;
let fixture;
const serviceRegistry = registry.category("services");

// Should test ONLY the webClient and features present in Enterprise
// Those tests rely on hidden view to be in CSS: display: none
QUnit.module("WebClient Enterprise", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        fixture = getFixture();
        serviceRegistry.add("home_menu", homeMenuService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
    });

    QUnit.module("basic flow with home menu", (hooks) => {
        let mockRPC;
        hooks.beforeEach((assert) => {
            serverData.menus[1].actionID = 4;
            serverData.menus.root.children = [1];
            serverData.views["partner,false,form"] = `
                <form>
                    <field name="display_name"/>
                    <field name="m2o" open_target="current"/>
                </form>`;
            mockRPC = async (route) => {
                assert.step(route);
                if (route === "/web/dataset/call_kw/partner/get_formview_action") {
                    return {
                        type: "ir.actions.act_window",
                        res_model: "partner",
                        view_type: "form",
                        view_mode: "form",
                        views: [[false, "form"]],
                        target: "current",
                        res_id: 2,
                    };
                }
            };
        });

        QUnit.test("1 -- start up", async function (assert) {
            await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            assert.ok(document.body.classList.contains("o_home_menu_background"));
            assert.containsOnce(fixture, ".o_home_menu");
            assert.isNotVisible(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, ".o_app.o_menuitem");
        });

        QUnit.test("2 -- navbar updates on displaying an action", async function (assert) {
            await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(fixture.querySelector(".o_app.o_menuitem"));
            await nextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ]);
            assert.notOk(document.body.classList.contains("o_home_menu_background"));
            assert.containsNone(fixture, ".o_home_menu");
            assert.containsOnce(fixture, ".o_kanban_view");
            const menuToggle = fixture.querySelector(".o_menu_toggle");
            assert.isVisible(menuToggle);
            assert.notOk(menuToggle.classList.contains("o_menu_toggle_back"));
        });

        QUnit.test("3 -- push another action in the breadcrumb", async function (assert) {
            await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(fixture.querySelector(".o_app.o_menuitem"));
            await nextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ]);
            assert.containsOnce(fixture, ".o_kanban_view");
            await click(fixture.querySelector(".o_kanban_record"));
            await nextTick(); // there is another tick to update navbar and destroy HomeMenu
            assert.verifySteps(["/web/dataset/call_kw/partner/web_read"]);
            assert.isVisible(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, ".o_form_view");
            assert.strictEqual(
                fixture.querySelector(".o_breadcrumb .active").textContent,
                "First record"
            );
        });

        QUnit.test("4 -- push a third action in the breadcrumb", async function (assert) {
            await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(fixture.querySelector(".o_app.o_menuitem"));
            await nextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ]);
            assert.containsOnce(fixture, ".o_kanban_view");
            await click(fixture.querySelector(".o_kanban_record"));
            assert.verifySteps(["/web/dataset/call_kw/partner/web_read"]);
            await click(fixture, '.o_field_widget[name="m2o"] .o_external_button');
            assert.verifySteps([
                "/web/dataset/call_kw/partner/get_formview_action",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_read",
            ]);
            assert.containsOnce(fixture, ".o_form_view");
            assert.strictEqual(
                fixture.querySelector(".o_breadcrumb .active").textContent,
                "Second record"
            );
            // The third one is the active one
            assert.containsN(fixture, ".breadcrumb-item", 2);
        });

        QUnit.test(
            "5 -- switch to HomeMenu from an action with 2 breadcrumbs",
            async function (assert) {
                await createEnterpriseWebClient({ fixture, serverData, mockRPC });
                assert.verifySteps(["/web/webclient/load_menus"]);
                await click(fixture.querySelector(".o_app.o_menuitem"));
                await nextTick();
                assert.verifySteps([
                    "/web/action/load",
                    "/web/dataset/call_kw/partner/get_views",
                    "/web/dataset/call_kw/partner/web_search_read",
                ]);
                assert.containsOnce(fixture, ".o_kanban_view");
                await click(fixture.querySelector(".o_kanban_record"));
                assert.verifySteps(["/web/dataset/call_kw/partner/web_read"]);
                await click(fixture, '.o_field_widget[name="m2o"] .o_external_button');
                assert.verifySteps([
                    "/web/dataset/call_kw/partner/get_formview_action",
                    "/web/dataset/call_kw/partner/get_views",
                    "/web/dataset/call_kw/partner/web_read",
                ]);
                const menuToggle = fixture.querySelector(".o_menu_toggle");
                await click(menuToggle);
                assert.verifySteps([]);
                assert.ok(menuToggle.classList.contains("o_menu_toggle_back"));
                assert.containsOnce(fixture, ".o_home_menu");
                assert.isNotVisible(fixture.querySelector(".o_form_view"));
            }
        );

        QUnit.test("6 -- back to underlying action with many breadcrumbs", async function (assert) {
            await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            assert.verifySteps(["/web/webclient/load_menus"]);
            await click(fixture.querySelector(".o_app.o_menuitem"));
            await nextTick();
            assert.verifySteps([
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ]);
            assert.containsOnce(fixture, ".o_kanban_view");
            await click(fixture.querySelector(".o_kanban_record"));
            assert.verifySteps(["/web/dataset/call_kw/partner/web_read"]);
            await click(fixture, '.o_field_widget[name="m2o"] .o_external_button');
            assert.verifySteps([
                "/web/dataset/call_kw/partner/get_formview_action",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_read",
            ]);
            const menuToggle = fixture.querySelector(".o_menu_toggle");
            await click(menuToggle);

            // can't click again too soon because of the mutex in home_menu
            // service (waiting for the url to be updated)
            await nextTick();

            await click(menuToggle);

            assert.verifySteps(
                ["/web/dataset/call_kw/partner/web_read"],
                "the underlying view should reload when toggling the HomeMenu to off"
            );
            assert.containsNone(fixture, ".o_home_menu");
            assert.containsOnce(fixture, ".o_form_view");
            assert.notOk(menuToggle.classList.contains("o_menu_toggle_back"));
            assert.strictEqual(
                fixture.querySelector(".o_breadcrumb .active").textContent,
                "Second record"
            );
            // Third breadcrumb is the active one
            assert.containsN(fixture, ".breadcrumb-item", 2);
        });

        QUnit.test("restore the newly created record in form view", async (assert) => {
            const action = serverData.actions[6];
            delete action.res_id;
            action.target = "current";
            const webClient = await createEnterpriseWebClient({ fixture, serverData });

            await doAction(webClient, 6);
            assert.containsOnce(fixture, ".o_form_view");
            assert.containsOnce(fixture, ".o_form_view .o_form_editable");
            await editInput(fixture, ".o_field_widget[name=display_name] input", "red right hand");
            await click(fixture.querySelector(".o_form_button_save"));
            assert.strictEqual(
                fixture.querySelector(".o_breadcrumb .active").textContent,
                "red right hand"
            );
            await click(fixture.querySelector(".o_menu_toggle"));
            assert.isNotVisible(fixture.querySelector(".o_form_view"));

            // can't click again too soon because of the mutex in home_menu
            // service (waiting for the url to be updated)
            await nextTick();

            await click(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, ".o_form_view");
            assert.containsOnce(fixture, ".o_form_view .o_form_saved");
            assert.strictEqual(
                fixture.querySelector(".o_breadcrumb .active").textContent,
                "red right hand"
            );
        });

        QUnit.skip("fast clicking on restore (implementation detail)", async (assert) => {
            assert.expect(6);

            let doVeryFastClick = false;

            class DelayedClientAction extends Component {
                setup() {
                    onMounted(() => {
                        if (doVeryFastClick) {
                            doVeryFastClick = false;
                            click(fixture.querySelector(".o_menu_toggle"));
                        }
                    });
                }
            }
            DelayedClientAction.template = xml`<div class='delayed_client_action'>
                <button t-on-click="resolve">RESOLVE</button>
            </div>`;

            registry.category("actions").add("DelayedClientAction", DelayedClientAction);
            const webClient = await createEnterpriseWebClient({ fixture, serverData });
            await doAction(webClient, "DelayedClientAction");
            await nextTick();
            await click(fixture.querySelector(".o_menu_toggle"));
            assert.isVisible(fixture.querySelector(".o_home_menu"));
            assert.isNotVisible(fixture.querySelector(".delayed_client_action"));

            doVeryFastClick = true;
            await click(fixture.querySelector(".o_menu_toggle"));
            await nextTick();
            // off homemenu
            assert.isVisible(fixture.querySelector(".o_home_menu"));
            assert.isNotVisible(fixture.querySelector(".delayed_client_action"));

            await click(fixture.querySelector(".o_menu_toggle"));
            await nextTick();
            assert.containsNone(fixture, ".o_home_menu");
            assert.containsOnce(fixture, ".delayed_client_action");
        });
    });

    QUnit.test("clear unCommittedChanges when toggling home menu", async function (assert) {
        assert.expect(6);
        // Edit a form view, don't save, toggle home menu
        // the autosave feature of the Form view is activated
        // and relied upon by this test

        const mockRPC = (route, args) => {
            if (args.method === "web_save") {
                assert.strictEqual(args.model, "partner");
                assert.deepEqual(args.args[1], {
                    display_name: "red right hand",
                    foo: false,
                });
            }
        };

        const webClient = await createEnterpriseWebClient({ fixture, serverData, mockRPC });
        await doAction(webClient, 3, { viewType: "form" });
        assert.containsOnce(fixture, ".o_form_view .o_form_editable");
        await editInput(fixture, ".o_field_widget[name=display_name] input", "red right hand");

        await click(fixture.querySelector(".o_menu_toggle"));
        assert.containsNone(fixture, ".o_form_view");
        assert.containsNone(fixture, ".modal");
        assert.containsOnce(fixture, ".o_home_menu");
    });

    QUnit.test("can have HomeMenu and dialog action", async function (assert) {
        const webClient = await createEnterpriseWebClient({ fixture, serverData });
        assert.containsOnce(fixture, ".o_home_menu");
        assert.containsNone(fixture, ".modal .o_form_view");
        await doAction(webClient, 5);
        assert.containsOnce(fixture, ".modal .o_form_view");
        assert.isVisible(fixture.querySelector(".modal .o_form_view"));
        assert.containsOnce(fixture, ".o_home_menu");
    });

    QUnit.test("supports attachments of apps deleted", async function (assert) {
        // When doing a pg_restore without the filestore
        // LPE fixme: may not be necessary anymore since menus are not HomeMenu props anymore
        serverData.menus = {
            root: { id: "root", children: [1], name: "root", appID: "root" },
            1: {
                id: 1,
                appID: 1,
                actionID: 1,
                xmlid: "",
                name: "Partners",
                children: [],
                webIconData: "",
                webIcon: "bloop,bloop",
            },
        };
        patchWithCleanup(odoo, { debug: "1" });
        await createEnterpriseWebClient({ fixture, serverData });
        assert.containsOnce(fixture, ".o_home_menu");
    });

    QUnit.test(
        "debug manager resets to global items when home menu is displayed",
        async function (assert) {
            const debugRegistry = registry.category("debug");
            debugRegistry.category("view").add("editView", editView);
            debugRegistry.category("default").add("item_1", () => {
                return {
                    type: "item",
                    description: "globalItem",
                    callback: () => {},
                    sequence: 10,
                };
            });
            const mockRPC = async (route) => {
                if (route.includes("check_access_rights")) {
                    return true;
                }
            };
            patchWithCleanup(odoo, { debug: "1" });
            const webClient = await createEnterpriseWebClient({ fixture, serverData, mockRPC });
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(fixture, ".o_debug_manager .dropdown-item:contains('globalItem')");
            assert.containsNone(
                fixture,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            await doAction(webClient, 1);
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(fixture, ".o_debug_manager .dropdown-item:contains('globalItem')");
            assert.containsOnce(
                fixture,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(fixture.querySelector(".o_menu_toggle"));
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(fixture, ".o_debug_manager .dropdown-item:contains('globalItem')");
            assert.containsNone(
                fixture,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            await doAction(webClient, 3);
            await click(fixture.querySelector(".o_debug_manager .dropdown-toggle"));
            assert.containsOnce(fixture, ".o_debug_manager .dropdown-item:contains('globalItem')");
            assert.containsOnce(
                fixture,
                ".o_debug_manager .dropdown-item:contains('Edit View: List')"
            );
            assert.containsNone(
                fixture,
                ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
            );
        }
    );

    QUnit.test(
        "url state is well handled when going in and out of the HomeMenu",
        async function (assert) {
            const webClient = await createEnterpriseWebClient({ fixture, serverData });
            await nextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, { action: "menu" });

            await click(fixture.querySelector(".o_apps > .o_draggable:nth-child(2) > .o_app"));
            await nextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, {
                action: 1002,
                menu_id: 2,
            });

            await click(fixture.querySelector(".o_menu_toggle"));
            await nextTick();
            assert.deepEqual(webClient.env.services.router.current.hash, {
                action: "menu",
                menu_id: 2,
            });

            await click(fixture.querySelector(".o_menu_toggle"));
            await nextTick();
            // if we reload on going back to underlying action
            // end if
            assert.deepEqual(webClient.env.services.router.current.hash, {
                action: 1002,
                menu_id: 2,
            });
        }
    );

    QUnit.test(
        "underlying action's menu items are invisible when HomeMenu is displayed",
        async function (assert) {
            serverData.menus[1].children = [99];
            serverData.menus[99] = {
                id: 99,
                children: [],
                name: "SubMenu",
                appID: 1,
                actionID: 1002,
                xmlid: "",
                webIconData: undefined,
                webIcon: false,
            };
            await createEnterpriseWebClient({ fixture, serverData });
            assert.containsNone(fixture, "nav .o_menu_sections");
            assert.containsNone(fixture, "nav .o_menu_brand");
            await click(fixture.querySelector(".o_app.o_menuitem:nth-child(1)"));
            await nextTick();
            assert.containsOnce(fixture, "nav .o_menu_sections");
            assert.containsOnce(fixture, "nav .o_menu_brand");
            assert.isVisible(fixture.querySelector(".o_menu_sections"));
            assert.isVisible(fixture.querySelector(".o_menu_brand"));
            await click(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, "nav .o_menu_sections");
            assert.containsOnce(fixture, "nav .o_menu_brand");
            assert.isNotVisible(fixture.querySelector(".o_menu_sections"));
            assert.isNotVisible(fixture.querySelector(".o_menu_brand"));
        }
    );

    QUnit.test("loadState back and forth keeps relevant keys in state", async function (assert) {
        const webClient = await createEnterpriseWebClient({ fixture, serverData });

        await click(fixture.querySelector(".o_apps > .o_draggable:nth-child(2) > .o_app"));
        await nextTick();
        assert.containsOnce(fixture, ".test_client_action");
        assert.strictEqual(
            fixture.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.containsNone(fixture, ".o_home_menu");
        const state = webClient.env.services.router.current.hash;
        assert.deepEqual(state, {
            action: 1002,
            menu_id: 2,
        });

        await loadState(webClient, {});
        assert.containsNone(fixture, ".test_client_action");
        assert.containsOnce(fixture, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "menu",
        });

        await loadState(webClient, state);
        assert.containsOnce(fixture, ".test_client_action");
        assert.strictEqual(
            fixture.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 2"
        );
        assert.containsNone(fixture, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, state);

        await loadState(webClient, {});
        assert.containsNone(fixture, ".test_client_action");
        assert.containsOnce(fixture, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "menu",
        });

        // switch to  the first app
        const app1State = { action: 1001, menu_id: 1 };
        await loadState(webClient, app1State);
        assert.containsOnce(fixture, ".test_client_action");
        assert.strictEqual(
            fixture.querySelector(".test_client_action").textContent.trim(),
            "ClientAction_Id 1"
        );
        assert.containsNone(fixture, ".o_home_menu");
        assert.deepEqual(webClient.env.services.router.current.hash, app1State);
    });

    QUnit.test(
        "go back to home menu using browser back button (i.e. loadState)",
        async function (assert) {
            const webClient = await createEnterpriseWebClient({ fixture, serverData });
            assert.containsOnce(fixture, ".o_home_menu");
            assert.isNotVisible(fixture.querySelector(".o_main_navbar .o_menu_toggle"));

            await click(fixture.querySelector(".o_apps > .o_draggable:nth-child(2) > .o_app"));
            assert.containsNone(fixture, ".test_client_action");
            await nextTick();
            assert.containsOnce(fixture, ".test_client_action");
            assert.containsNone(fixture, ".o_home_menu");

            await loadState(webClient, { action: "menu" }); // FIXME: this might need to be changed
            assert.containsNone(fixture, ".test_client_action");
            assert.containsOnce(fixture, ".o_home_menu");
            assert.isNotVisible(fixture.querySelector(".o_main_navbar .o_menu_toggle"));
        }
    );

    QUnit.test("initial action crashes", async (assert) => {
        assert.expectErrors();
        browser.location.hash = "#action=__test__client__action__&menu_id=1";
        const ClientAction = registry.category("actions").get("__test__client__action__");
        class Override extends ClientAction {
            setup() {
                super.setup();
                assert.step("clientAction setup");
                throw new Error("my error");
            }
        }
        registry.category("actions").add("__test__client__action__", Override, { force: true });

        registry.category("services").add("error", errorService);

        const webClient = await createEnterpriseWebClient({ fixture, serverData });
        assert.verifySteps(["clientAction setup"]);
        assert.containsOnce(fixture, "nav .o_menu_toggle");
        assert.isVisible(fixture.querySelector("nav .o_menu_toggle"));
        assert.strictEqual(fixture.querySelector(".o_action_manager").innerHTML, "");
        assert.deepEqual(webClient.env.services.router.current.hash, {
            action: "__test__client__action__",
            menu_id: 1,
        });
        await nextTick();
        assert.verifyErrors(["my error"]);
    });

    QUnit.test(
        "Apps are reordered at startup based on session's user settings",
        async function (assert) {
            // Config is written with apps xmlids order (default is menu_1, menu_2)
            patchWithCleanup(session, {
                user_settings: { id: 1, homemenu_config: '["menu_2","menu_1"]' },
            });
            await createEnterpriseWebClient({ fixture, serverData });

            const apps = document.querySelectorAll(".o_app");
            assert.strictEqual(
                apps[0].getAttribute("data-menu-xmlid"),
                "menu_2",
                "first displayed app has menu_2 xmlid"
            );
            assert.strictEqual(
                apps[1].getAttribute("data-menu-xmlid"),
                "menu_1",
                "second displayed app has menu_1 xmlid"
            );
            assert.strictEqual(apps[0].textContent, "App2", "first displayed app is App2");
            assert.strictEqual(apps[1].textContent, "App1", "second displayed app is App1");
        }
    );

    QUnit.test(
        "Share URL item is present in the user menu when running as PWA",
        async function (assert) {
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(display-mode: standalone)") {
                        return { matches: true };
                    } else {
                        this._super();
                    }
                },
            });

            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("action", actionService);
            serviceRegistry.add("menu", menuService);

            const env = await makeTestEnv();

            registry.category("user_menuitems").add("share_url", shareUrlMenuItem);
            await mount(UserMenu, fixture, { env });
            await click(fixture.querySelector(".o_user_menu button"));
            assert.containsOnce(fixture, ".o_user_menu .dropdown-item");
            assert.strictEqual(
                fixture.querySelector(".o_user_menu .dropdown-item span").textContent,
                "Share",
                "share button is visible"
            );
        }
    );

    QUnit.test(
        "Share URL item is not present in the user menu when not running as PWA",
        async function (assert) {
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(display-mode: standalone)") {
                        return { matches: false };
                    } else {
                        this._super();
                    }
                },
            });

            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("action", actionService);
            serviceRegistry.add("menu", menuService);

            const env = await makeTestEnv();

            registry.category("user_menuitems").add("share_url", shareUrlMenuItem);
            await mount(UserMenu, fixture, { env });
            await click(fixture.querySelector(".o_user_menu button"));
            assert.containsNone(
                fixture,
                ".o_user_menu .dropdown-item",
                "share button is not visible"
            );
        }
    );

    QUnit.test(
        "Navigate to an application from the HomeMenu should generate only one pushState",
        async function (assert) {
            const pushState = browser.history.pushState;
            patchWithCleanup(browser, {
                history: Object.assign({}, browser.history, {
                    pushState(state, title, url) {
                        pushState(...arguments);
                        assert.step(url.split("#")[1]);
                    },
                }),
            });
            await createEnterpriseWebClient({ fixture, serverData });

            await click(fixture.querySelector(".o_apps > .o_draggable:nth-child(2) > .o_app"));
            await nextTick();
            assert.containsOnce(fixture, ".test_client_action");
            assert.strictEqual(
                fixture.querySelector(".test_client_action").textContent.trim(),
                "ClientAction_Id 2"
            );

            await click(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, ".o_home_menu");

            await click(fixture.querySelector(".o_apps > .o_draggable:nth-child(1) > .o_app"));
            await nextTick();
            assert.containsOnce(fixture, ".test_client_action");
            assert.strictEqual(
                fixture.querySelector(".test_client_action").textContent.trim(),
                "ClientAction_Id 1"
            );

            await click(fixture.querySelector(".o_menu_toggle"));
            await nextTick();
            assert.containsOnce(fixture, ".o_home_menu");
            assert.verifySteps([
                "action=menu",
                "action=1002&menu_id=2",
                "action=menu&menu_id=2",
                "action=1001&menu_id=1",
                "action=menu&menu_id=1",
            ]);
        }
    );
});
