/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { makeTestEnv } from "../../helpers/mock_env";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { click, getFixture, hushConsole, nextTick, patchWithCleanup } from "../../helpers/utils";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
    setupWebClientRegistries,
} from "./../helpers";
import { listView } from "@web/views/list/list_view";
import { companyService } from "@web/webclient/company_service";
import { onWillStart } from "@odoo/owl";

let serverData;
let target;
const actionRegistry = registry.category("actions");
const actionHandlersRegistry = registry.category("action_handlers");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Misc");

    QUnit.test("can execute actions from id, xmlid and tag", async (assert) => {
        assert.expect(6);
        serverData.actions[1] = {
            tag: "client_action_by_db_id",
            target: "main",
            type: "ir.actions.client",
        };
        serverData.actions["wowl.some_action"] = {
            tag: "client_action_by_xml_id",
            target: "main",
            type: "ir.actions.client",
        };
        actionRegistry
            .add("client_action_by_db_id", () => assert.step("client_action_db_id"))
            .add("client_action_by_xml_id", () => assert.step("client_action_xml_id"))
            .add("client_action_by_object", () => assert.step("client_action_object"));
        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData });
        await doAction(env, 1);
        assert.verifySteps(["client_action_db_id"]);
        await doAction(env, "wowl.some_action");
        assert.verifySteps(["client_action_xml_id"]);
        await doAction(env, {
            tag: "client_action_by_object",
            target: "current",
            type: "ir.actions.client",
        });
        assert.verifySteps(["client_action_object"]);
    });

    QUnit.test("action doesn't exists", async (assert) => {
        assert.expect(1);
        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData });
        try {
            await doAction(env, {
                tag: "this_is_a_tag",
                target: "current",
                type: "ir.not_action.error",
            });
        } catch (e) {
            assert.strictEqual(
                e.message,
                "The ActionManager service can't handle actions of type ir.not_action.error"
            );
        }
    });

    QUnit.test("action in handler registry", async (assert) => {
        assert.expect(2);
        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData });
        actionHandlersRegistry.add("ir.action_in_handler_registry", ({ action }) =>
            assert.step(action.type)
        );
        await doAction(env, {
            tag: "this_is_a_tag",
            target: "current",
            type: "ir.action_in_handler_registry",
        });
        assert.verifySteps(["ir.action_in_handler_registry"]);
    });

    QUnit.test("properly handle case when action id does not exist", async (assert) => {
        assert.expect(2);
        const webClient = await createWebClient({ serverData });
        patchWithCleanup(window, { console: hushConsole });
        patchWithCleanup(webClient.env.services.notification, {
            add(message) {
                assert.strictEqual(message, "No action with id '4448' could be found");
            },
        });
        await doAction(webClient, 4448);
        assert.containsOnce(target, "div.o_invalid_action");
    });

    QUnit.test("actions can be cached", async function (assert) {
        assert.expect(8);

        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                assert.step(JSON.stringify(args));
            }
        };

        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData, mockRPC });

        const loadAction = env.services.action.loadAction;

        // With no additional params
        await loadAction(3);
        await loadAction(3);

        // With specific additionalContext
        await loadAction(3, { additionalContext: { configuratorMode: "add" } });
        await loadAction(3, { additionalContext: { configuratorMode: "edit" } });

        // With same active_id
        await loadAction(3, { active_id: 1 });
        await loadAction(3, { active_id: 1 });

        // With active_id change
        await loadAction(3, { active_id: 2 });

        // With same active_ids
        await loadAction(3, { active_ids: [1, 2] });
        await loadAction(3, { active_ids: [1, 2] });

        // With active_ids change
        await loadAction(3, { active_ids: [1, 2, 3] });

        // With same active_model
        await loadAction(3, { active_model: "a" });
        await loadAction(3, { active_model: "a" });

        // With active_model change
        await loadAction(3, { active_model: "b" });

        assert.verifySteps(
            [
                '{"action_id":3,"additional_context":{}}',
                '{"action_id":3,"additional_context":{"active_id":1}}',
                '{"action_id":3,"additional_context":{"active_id":2}}',
                '{"action_id":3,"additional_context":{"active_ids":[1,2]}}',
                '{"action_id":3,"additional_context":{"active_ids":[1,2,3]}}',
                '{"action_id":3,"additional_context":{"active_model":"a"}}',
                '{"action_id":3,"additional_context":{"active_model":"b"}}',
            ],
            "should load from server once per active_id/active_ids/active_model change, nothing else"
        );
    });

    QUnit.test("action cache: additionalContext is respected", async function (assert) {
        assert.expect(5);

        const mockRPC = async (route) => {
            if (route === "/web/action/load") {
                assert.step("server loaded");
            }
        };

        setupWebClientRegistries();
        const env = await makeTestEnv({ serverData, mockRPC });
        const { loadAction } = env.services.action;
        const actionParams = {
            additionalContext: {
                some: { deep: { nested: "Robert" } },
            },
        };

        let action = await loadAction(3, actionParams);
        assert.verifySteps(["server loaded"]);
        assert.deepEqual(action.context, actionParams);

        // Modify the action in place
        action.context.additionalContext.some.deep.nested = "Nesta";

        // Change additionalContext and reload from cache
        actionParams.additionalContext.some.deep.nested = "Marley";
        action = await loadAction(3, actionParams);
        assert.verifySteps([], "loaded from cache");
        assert.deepEqual(action.context, actionParams);
    });

    QUnit.test('action with "no_breadcrumbs" set to true', async function (assert) {
        serverData.actions[4].context = { no_breadcrumbs: true };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_control_panel .o_breadcrumb");
        // push another action flagged with 'no_breadcrumbs=true'
        await doAction(webClient, 4);
        assert.containsNone(target, ".o_control_panel .o_breadcrumb");
    });

    QUnit.test("document's title is updated when an action is executed", async function (assert) {
        const defaultTitle = { zopenerp: "Odoo" };
        const webClient = await createWebClient({ serverData });
        await nextTick();
        let currentTitle = webClient.env.services.title.getParts();
        assert.deepEqual(currentTitle, defaultTitle);
        let currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, {});
        await doAction(webClient, 4);
        await nextTick();
        currentTitle = webClient.env.services.title.getParts();
        assert.deepEqual(currentTitle, {
            ...defaultTitle,
            action: "Partners Action 4",
        });
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, { action: 4, model: "partner", view_type: "kanban" });
        await doAction(webClient, 8);
        await nextTick();
        currentTitle = webClient.env.services.title.getParts();
        assert.deepEqual(currentTitle, {
            ...defaultTitle,
            action: "Favorite Ponies",
        });
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, { action: 8, model: "pony", view_type: "list" });
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await nextTick();
        currentTitle = webClient.env.services.title.getParts();
        assert.deepEqual(currentTitle, {
            ...defaultTitle,
            action: "Twilight Sparkle",
        });
        currentHash = webClient.env.services.router.current.hash;
        assert.deepEqual(currentHash, { action: 8, id: 4, model: "pony", view_type: "form" });
    });

    QUnit.test('handles "history_back" event', async function (assert) {
        assert.expect(4);
        let list;
        patchWithCleanup(listView.Controller.prototype, {
            setup() {
                super.setup(...arguments);
                list = this;
            },
        });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        await doAction(webClient, 3);
        assert.containsOnce(target, "ol.breadcrumb");
        assert.containsOnce(target, ".o_breadcrumb span");
        list.env.config.historyBack();
        await nextTick();
        assert.containsOnce(target, ".o_breadcrumb span");
        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "Partners Action 4",
            "breadcrumbs should display the display_name of the action"
        );
    });

    QUnit.test("stores and restores scroll position (in kanban)", async function (assert) {
        serverData.actions[3].views = [[false, "kanban"]];
        for (let i = 0; i < 60; i++) {
            serverData.models.partner.records.push({ id: 100 + i, foo: `Record ${i}` });
        }
        const container = document.createElement("div");
        container.classList.add("o_web_client");
        container.style.height = "250px";
        target.appendChild(container);
        const webClient = await createWebClient({ target: container, serverData });
        // execute a first action
        await doAction(webClient, 3);
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 0);
        // simulate a scroll
        target.querySelector(".o_content").scrollTop = 100;
        // execute a second action (in which we don't scroll)
        await doAction(webClient, 4);
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 0);
        // go back using the breadcrumbs
        await click(target.querySelector(".o_control_panel .breadcrumb a"));
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 100);
    });

    QUnit.test("stores and restores scroll position (in list)", async function (assert) {
        for (let i = 0; i < 60; i++) {
            serverData.models.partner.records.push({ id: 100 + i, foo: `Record ${i}` });
        }
        const container = document.createElement("div");
        container.classList.add("o_web_client");
        container.style.height = "250px";
        target.appendChild(container);
        const webClient = await createWebClient({ target: container, serverData });
        // execute a first action
        await doAction(webClient, 3);
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 0);
        assert.strictEqual(target.querySelector(".o_list_renderer").scrollTop, 0);
        // simulate a scroll
        target.querySelector(".o_list_renderer").scrollTop = 100;
        await nextTick();
        // execute a second action (in which we don't scroll)
        await doAction(webClient, 4);
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 0);
        // go back using the breadcrumbs
        await click(target.querySelector(".o_control_panel .breadcrumb a"));
        assert.strictEqual(target.querySelector(".o_content").scrollTop, 0);
        assert.strictEqual(target.querySelector(".o_list_renderer").scrollTop, 100);
    });

    QUnit.test(
        'executing an action with target != "new" closes all dialogs',
        async function (assert) {
            serverData.views["partner,false,form"] = `
                <form>
                    <field name="o2m">
                    <tree><field name="foo"/></tree>
                    <form><field name="foo"/></form>
                    </field>
                </form>
                `;
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");
            await click(target.querySelector(".o_list_view .o_data_row .o_list_char"));
            assert.containsOnce(target, ".o_form_view");
            await click(target.querySelector(".o_form_view .o_data_row .o_data_cell"));
            assert.containsOnce(document.body, ".modal .o_form_view");
            await doAction(webClient, 1); // target != 'new'
            await nextTick(); // wait for the dialog to be closed
            assert.containsNone(document.body, ".modal");
        }
    );

    QUnit.test(
        'executing an action with target "new" does not close dialogs',
        async function (assert) {
            assert.expect(4);
            serverData.views["partner,false,form"] = `
                <form>
                    <field name="o2m">
                    <tree><field name="foo"/></tree>
                    <form><field name="foo"/></form>
                    </field>
                </form>
                `;
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");
            await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));
            assert.containsOnce(target, ".o_form_view");
            await click(target.querySelector(".o_form_view .o_data_row .o_data_cell"));
            assert.containsOnce(document.body, ".modal .o_form_view");
            await doAction(webClient, 5); // target 'new'
            assert.containsN(document.body, ".modal .o_form_view", 2);
        }
    );

    QUnit.test(
        "retrieving a stored action should remove 'allowed_company_ids' from its context",
        async function (assert) {
            // Prepare a multi company scenario
            session.user_companies = {
                allowed_companies: {
                    3: { id: 3, name: "Hermit", sequence: 1 },
                    2: { id: 2, name: "Herman's", sequence: 2 },
                    1: { id: 1, name: "Heroes TM", sequence: 3 },
                },
                current_company: 3,
            };
            registry.category("services").add("company", companyService);

            // Prepare a stored action
            browser.sessionStorage.setItem(
                "current_action",
                JSON.stringify({
                    ...serverData.actions[1],
                    context: {
                        someKey: 44,
                        allowed_company_ids: [1, 2],
                        lang: "not_en",
                        tz: "not_taht",
                        uid: 42,
                    },
                })
            );

            // Prepare the URL hash to make sure the stored action will get executed.
            browser.location.hash = "#model=partner&view_type=kanban";

            // Create the web client. It should execute the stored action.
            const webClient = await createWebClient({ serverData });
            await nextTick();

            // Check the current action context
            assert.deepEqual(webClient.env.services.action.currentController.action.context, {
                // action context
                someKey: 44,
                lang: "not_en",
                tz: "not_taht",
                uid: 42,
                // note there is no 'allowed_company_ids' in the action context
            });
        }
    );

    QUnit.test(
        "action is removed while waiting for another action with selectMenu",
        async (assert) => {
            let def;
            const actionRegistry = registry.category("actions");
            const ClientAction = actionRegistry.get("__test__client__action__");

            patchWithCleanup(ClientAction.prototype, {
                setup() {
                    super.setup();
                    onWillStart(() => {
                        return def;
                    });
                },
            });
            const webClient = await createWebClient({ serverData });
            // starting point: a kanban view
            await doAction(webClient, 4);
            const root = document.querySelector(".o_web_client");
            assert.containsOnce(root, ".o_kanban_view");

            // select one new app in navbar menu
            def = testUtils.makeTestPromise();
            const menus = webClient.env.services.menu.getApps();
            webClient.env.services.menu.selectMenu(menus[1], { resetScreen: true });
            await nextTick();

            // check that the action manager is empty, even though client action is loading
            assert.strictEqual(root.querySelector(".o_action_manager").textContent, "");

            // resolve onwillstart so client action is ready
            def.resolve();
            await nextTick();
            assert.strictEqual(
                root.querySelector(".o_action_manager").textContent,
                " ClientAction_Id 1"
            );
        }
    );
});
