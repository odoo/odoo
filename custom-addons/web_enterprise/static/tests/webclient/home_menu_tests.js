/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import {
    getFixture,
    nextTick,
    triggerHotkey,
    patchWithCleanup,
    drag,
} from "@web/../tests/helpers/utils";
import { commandService } from "@web/core/commands/command_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { browser } from "@web/core/browser/browser";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { session } from "@web/session";
import { templates } from "@web/core/assets";

import { App, EventBus } from "@odoo/owl";
const patchDate = testUtils.mock.patchDate;
const serviceRegistry = registry.category("services");
let target;

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

async function createHomeMenu(homeMenuProps, config = {}) {
    const env = await makeTestEnv(config);
    const app = new App(HomeMenu, {
        env,
        props: homeMenuProps,
        templates,
        test: true,
    });
    const homeMenu = await app.mount(target);
    registerCleanup(() => app.destroy());
    return homeMenu;
}

async function walkOn(assert, path) {
    for (const step of path) {
        triggerHotkey(`${step.shiftKey ? "shift+" : ""}${step.key}`);
        await nextTick();
        assert.hasClass(
            target.querySelectorAll(".o_menuitem")[step.index],
            "o_focused",
            `step ${step.number}`
        );
    }
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let homeMenuProps;
let bus;
QUnit.module(
    "web_enterprise",
    {
        beforeEach: function () {
            homeMenuProps = {
                apps: [
                    {
                        actionID: 121,
                        appID: 1,
                        id: 1,
                        label: "Discuss",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.1",
                    },
                    {
                        actionID: 122,
                        appID: 2,
                        id: 2,
                        label: "Calendar",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.2",
                    },
                    {
                        actionID: 123,
                        appID: 3,
                        id: 3,
                        label: "Contacts",
                        parents: "",
                        webIcon: false,
                        xmlid: "app.3",
                    },
                ],
            };

            bus = new EventBus();
            const fakeHomeMenuService = {
                name: "home_menu",
                start() {
                    return {
                        toggle(show) {
                            bus.trigger("toggle", show);
                        },
                    };
                },
            };
            const fakeMenuService = {
                name: "menu",
                start() {
                    return {
                        selectMenu(menu) {
                            bus.trigger("selectMenu", menu.id);
                        },
                        getMenu() {
                            return {};
                        },
                    };
                },
            };
            serviceRegistry.add("ui", uiService);
            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("command", commandService);
            serviceRegistry.add("localization", makeFakeLocalizationService());
            serviceRegistry.add("orm", ormService);
            serviceRegistry.add(enterpriseSubscriptionService.name, enterpriseSubscriptionService);
            serviceRegistry.add(fakeHomeMenuService.name, fakeHomeMenuService);
            serviceRegistry.add(fakeMenuService.name, fakeMenuService);

            target = getFixture();
        },
    },
    function () {
        QUnit.module("HomeMenu");

        QUnit.test("ESC Support", async function (assert) {
            bus.addEventListener("toggle", (ev) => {
                assert.step(`toggle ${ev.detail}`);
            });
            await createHomeMenu(homeMenuProps);
            await testUtils.dom.triggerEvent(window, "keydown", { key: "Escape" });
            assert.verifySteps(["toggle false"]);
        });

        QUnit.test("Click on an app", async function (assert) {
            bus.addEventListener("selectMenu", (ev) => {
                assert.step(`selectMenu ${ev.detail}`);
            });
            await createHomeMenu(homeMenuProps);

            await testUtils.dom.click(target.querySelectorAll(".o_menuitem")[0]);
            assert.verifySteps(["selectMenu 1"]);
        });

        QUnit.test("Display Expiration Panel (no module installed)", async function (assert) {
            const unpatchDate = patchDate(2019, 9, 10, 0, 0, 0);
            registerCleanup(unpatchDate);

            patchWithCleanup(session, {
                expiration_date: "2019-11-01 12:00:00",
                expiration_reason: "",
                isMailInstalled: false,
                warning: "admin",
            });

            await createHomeMenu(homeMenuProps);

            assert.containsOnce(target, ".database_expiration_panel");
            assert.strictEqual(
                target.querySelector(".database_expiration_panel .oe_instance_register").innerText,
                "You will be able to register your database once you have installed your first app.",
                "There should be an expiration panel displayed"
            );

            // Close the expiration panel
            await testUtils.dom.click(
                target.querySelector(".database_expiration_panel .oe_instance_hide_panel")
            );
            assert.containsNone(target, ".database_expiration_panel");
        });

        QUnit.test("Navigation (only apps, only one line)", async function (assert) {
            assert.expect(8);

            homeMenuProps = {
                apps: new Array(3).fill().map((x, i) => {
                    return {
                        actionID: 120 + i,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
            };
            await createHomeMenu(homeMenuProps);

            const path = [
                { number: 0, key: "ArrowDown", index: 0 },
                { number: 1, key: "ArrowRight", index: 1 },
                { number: 2, key: "Tab", index: 2 },
                { number: 3, key: "ArrowRight", index: 0 },
                { number: 4, key: "Tab", shiftKey: true, index: 2 },
                { number: 5, key: "ArrowLeft", index: 1 },
                { number: 6, key: "ArrowDown", index: 1 },
                { number: 7, key: "ArrowUp", index: 1 },
            ];

            await walkOn(assert, path);
        });

        QUnit.test("Navigation (only apps, two lines, one incomplete)", async function (assert) {
            assert.expect(19);

            homeMenuProps = {
                apps: new Array(8).fill().map((x, i) => {
                    return {
                        actionID: 121,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
            };
            await createHomeMenu(homeMenuProps);

            const path = [
                { number: 1, key: "ArrowRight", index: 0 },
                { number: 2, key: "ArrowUp", index: 6 },
                { number: 3, key: "ArrowUp", index: 0 },
                { number: 4, key: "ArrowDown", index: 6 },
                { number: 5, key: "ArrowDown", index: 0 },
                { number: 6, key: "ArrowRight", index: 1 },
                { number: 7, key: "ArrowRight", index: 2 },
                { number: 8, key: "ArrowUp", index: 7 },
                { number: 9, key: "ArrowUp", index: 1 },
                { number: 10, key: "ArrowRight", index: 2 },
                { number: 11, key: "ArrowDown", index: 7 },
                { number: 12, key: "ArrowDown", index: 1 },
                { number: 13, key: "ArrowUp", index: 7 },
                { number: 14, key: "ArrowRight", index: 6 },
                { number: 15, key: "ArrowLeft", index: 7 },
                { number: 16, key: "ArrowUp", index: 1 },
                { number: 17, key: "ArrowLeft", index: 0 },
                { number: 18, key: "ArrowLeft", index: 5 },
                { number: 19, key: "ArrowRight", index: 0 },
            ];

            await walkOn(assert, path);
        });

        QUnit.test("Navigation and open an app in the home menu", async function (assert) {
            assert.expect(7);

            bus.addEventListener("selectMenu", (ev) => {
                assert.step(`selectMenu ${ev.detail}`);
            });
            await createHomeMenu(homeMenuProps);

            // No app selected so nothing to open
            await testUtils.dom.triggerEvent(window, "keydown", { key: "Enter" });
            assert.verifySteps([]);

            const path = [
                { number: 0, key: "ArrowDown", index: 0 },
                { number: 1, key: "ArrowRight", index: 1 },
                { number: 2, key: "Tab", index: 2 },
                { number: 3, key: "shift+Tab", index: 1 },
            ];

            await walkOn(assert, path);

            // open first app (Calendar)
            await testUtils.dom.triggerEvent(window, "keydown", { key: "Enter" });

            assert.verifySteps(["selectMenu 2"]);
        });

        QUnit.test("Reorder apps in home menu using drag and drop", async function (assert) {
            homeMenuProps = {
                apps: new Array(8).fill().map((x, i) => {
                    return {
                        actionID: 121,
                        appID: i + 1,
                        id: i + 1,
                        label: `0${i}`,
                        parents: "",
                        webIcon: false,
                        xmlid: `app.${i}`,
                    };
                }),
            };
            patchWithCleanup(browser, {
                setTimeout: (callback, delay) => {
                    assert.step(`setTimeout of ${delay}ms`);
                    callback();
                },
            });
            patchWithCleanup(session, { user_settings: { id: 1, homemenu_config: "" } });
            const mockRPC = (route, args) => {
                if (args.method === "set_res_users_settings") {
                    assert.step(`set_res_users_settings`);
                    return {
                        id: 1,
                        homemenu_config:
                            '["app.1","app.2","app.3","app.0","app.4","app.5","app.6","app.7"]',
                    };
                }
            };
            const serverData = {
                models: {
                    "res.users.settings": {
                        fields: {
                            id: {
                                type: "number",
                            },
                            homemenu_config: {
                                type: "string",
                            },
                        },
                        records: [
                            {
                                id: 1,
                                homemenu_config: "",
                            },
                        ],
                    },
                },
            };
            await createHomeMenu(homeMenuProps, { serverData, mockRPC });

            const { drop } = await drag(".o_draggable:first-child");
            await drop(".o_draggable:nth-child(4)");
            assert.verifySteps(["setTimeout of 500ms", "set_res_users_settings"]);
            const apps = document.querySelectorAll(".o_app");
            assert.strictEqual(
                apps[0].getAttribute("data-menu-xmlid"),
                "app.1",
                "first displayed app has app.1 xmlid"
            );
            assert.strictEqual(
                apps[3].getAttribute("data-menu-xmlid"),
                "app.0",
                "app 0 is now at 4th position"
            );
        });

        QUnit.test(
            "The HomeMenu input takes the focus when you press a key only if no other element is the activeElement",
            async function (assert) {
                const target = getFixture();
                const homeMenu = await createHomeMenu(homeMenuProps);
                const input = target.querySelector(".o_search_hidden");
                assert.strictEqual(document.activeElement, input);

                const activeElement = document.createElement("div");
                homeMenu.env.services.ui.activateElement(activeElement);
                // remove the focus from the input
                const otherInput = document.createElement("input");
                target.querySelector(".o_home_menu").appendChild(otherInput);
                otherInput.focus();
                otherInput.blur();
                assert.notEqual(document.activeElement, input);

                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.notEqual(document.activeElement, input);

                homeMenu.env.services.ui.deactivateElement(activeElement);
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.strictEqual(document.activeElement, input);
            }
        );

        QUnit.test(
            "The HomeMenu input does not take the focus if it is already on another input",
            async function (assert) {
                const target = getFixture();
                await createHomeMenu(homeMenuProps);
                const homeMenuInput = target.querySelector(".o_search_hidden");
                assert.strictEqual(document.activeElement, homeMenuInput);

                const otherInput = document.createElement("input");
                target.querySelector(".o_home_menu").appendChild(otherInput);
                otherInput.focus();
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.notEqual(document.activeElement, homeMenuInput);

                otherInput.remove();
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.strictEqual(document.activeElement, homeMenuInput);
            }
        );

        QUnit.test(
            "The HomeMenu input does not take the focus if it is already on a textarea",
            async function (assert) {
                const target = getFixture();
                await createHomeMenu(homeMenuProps);
                const homeMenuInput = target.querySelector(".o_search_hidden");
                assert.strictEqual(document.activeElement, homeMenuInput);

                const textarea = document.createElement("textarea");
                target.querySelector(".o_home_menu").appendChild(textarea);
                textarea.focus();
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.notEqual(document.activeElement, homeMenuInput);

                textarea.remove();
                await testUtils.dom.triggerEvent(window, "keydown", { key: "a" });
                await nextTick();
                assert.strictEqual(document.activeElement, homeMenuInput);
            }
        );

        QUnit.test(
            "home search input shouldn't be focused on touch devices [REQUIRE FOCUS]",
            async function (assert) {
                // patch matchMedia to alter hasTouch value
                patchWithCleanup(browser, {
                    setTimeout: (fn) => fn(),
                    matchMedia: (media) => {
                        if (media === "(pointer:coarse)") {
                            return { matches: true };
                        }
                        this._super();
                    },
                });
                const target = getFixture();
                await createHomeMenu(homeMenuProps);
                const homeMenuInput = target.querySelector(".o_search_hidden");
                assert.notOk(
                    homeMenuInput.matches(":focus"),
                    "home menu search input shouldn't have the focus"
                );
            }
        );
    }
);
