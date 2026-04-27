/* @odoo-module */

import { contains } from "@web/../tests/utils";

import { patchUserWithCleanup } from "@web/../tests/helpers/mock_services";
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    editInput,
    triggerEvents,
} from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";

import { toggleSearchBarMenu, toggleMenuItem } from "@web/../tests/search/helpers";
import { companyService } from "@web/webclient/company_service";
import { commandService } from "@web/core/commands/command_service";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { doAction, getActionManagerServerData } from "@web/../tests/webclient/helpers";
import {
    leaveStudio,
    openStudio,
    registerStudioDependencies,
    fillActionFieldsDefaults,
} from "@web_studio/../tests/legacy/helpers";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { StudioView } from "@web_studio/client_action/view_editor/studio_view";
import { ViewEditor } from "@web_studio/client_action/view_editor/view_editor";
import { StudioClientAction } from "@web_studio/client_action/studio_client_action";
import { ListEditorRenderer } from "@web_studio/client_action/view_editor/editors/list/list_editor_renderer";
import { onMounted } from "@odoo/owl";
import { selectorContains } from "@web_studio/../tests/legacy/client_action/view_editors/view_editor_tests_utils";
import { redirect } from "@web/core/utils/urls";

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

let serverData;
let target;
QUnit.module("Studio", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = getActionManagerServerData();

        const actions = serverData.actions;
        for (const actId of Object.keys(actions)) {
            actions[actId] = fillActionFieldsDefaults(actions[actId]);
        }

        registerStudioDependencies();
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("company", companyService);

        // tweak a bit the default config to better fit with studio needs:
        //  - add some menu items we can click on to test the navigation
        //  - add a one2many field in a form view to test the one2many edition
        serverData.menus = {
            root: { id: "root", children: [1, 2, 3], name: "root", appID: "root" },
            1: {
                id: 1,
                children: [11, 12],
                name: "Partners",
                appID: 1,
                actionID: 4,
                xmlid: "app_1",
            },
            11: {
                id: 11,
                children: [],
                name: "Partners (Action 4)",
                appID: 1,
                actionID: 4,
                xmlid: "menu_11",
            },
            12: {
                id: 12,
                children: [],
                name: "Partners (Action 3)",
                appID: 1,
                actionID: 3,
                xmlid: "menu_12",
            },
            2: {
                id: 2,
                children: [],
                name: "Ponies",
                appID: 2,
                actionID: 8,
                xmlid: "app_2",
            },
            3: {
                id: 3,
                children: [],
                name: "Client Action",
                appID: 3,
                actionID: 9,
                xmlid: "app_3",
            },
        };
        serverData.models.partner.fields.date = { string: "Date", type: "date" };
        serverData.models.partner.fields.pony_id = {
            string: "Pony",
            type: "many2one",
            relation: "pony",
        };
        serverData.models.pony.fields.partner_ids = {
            string: "Partners",
            type: "one2many",
            relation: "partner",
            relation_field: "pony_id",
        };
        serverData.views["pony,false,form"] = `
            <form>
                <field name="name"/>
                <field name='partner_ids'>
                    <form>
                        <sheet>
                            <field name='display_name'/>
                        </sheet>
                    </form>
                </field>
            </form>`;
    });

    QUnit.module("Studio Navigation");

    QUnit.test("Studio not available for non system users", async function (assert) {
        assert.expect(2);

        patchUserWithCleanup({ isSystem: false });
        await createEnterpriseWebClient({ serverData });
        assert.containsOnce(target, ".o_main_navbar");

        assert.containsNone(target, ".o_main_navbar .o_web_studio_navbar_item button");
    });

    QUnit.test("Studio icon matches the clickbot selector", async function (assert) {
        // This test looks stupid, but if you ever need to adapt the selector,
        // you must adapt it as well in the clickbot (in web), otherwise Studio
        // might not be tested anymore by the click_everywhere test.
        await createEnterpriseWebClient({ serverData });
        assert.containsOnce(target, ".o_web_studio_navbar_item:not(.o_disabled) i");
    });

    QUnit.test("open Studio with act_window", async function (assert) {
        assert.expect(21);

        const mockRPC = async (route) => {
            assert.step(route);
        };
        await createEnterpriseWebClient({ serverData, mockRPC });
        assert.containsOnce(target, ".o_home_menu");

        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action

        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps(
            [
                "/web/webclient/load_menus",
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ],
            "should have loaded the action"
        );
        assert.containsOnce(target, ".o_main_navbar .o_web_studio_navbar_item button");

        await openStudio(target);

        assert.verifySteps(
            [
                "/web/dataset/call_kw/partner/get_views",

                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/partner/web_search_read",
            ],
            "should have opened the action in Studio"
        );

        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_kanban_view_editor",
            "the kanban view should be opened"
        );
        assert.containsOnce(
            target,
            ".o_kanban_record:contains(yop)",
            "the first partner should be displayed"
        );
        assert.containsOnce(target, ".o_studio_navbar .o_web_studio_leave a");

        await leaveStudio(target);

        assert.verifySteps(
            [
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ],
            "should have reloaded the previous action edited by Studio"
        );

        assert.containsNone(target, ".o_web_studio_editor_manager", "Studio should be closed");
        assert.containsOnce(
            target,
            ".o_kanban_view .o_kanban_record:contains(yop)",
            "the first partner should be displayed in kanban"
        );
    });

    QUnit.test("open Studio with act_window and viewType", async function (assert) {
        await createEnterpriseWebClient({ serverData });

        // open app Partners (act window action), sub menu Partners (action 3)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        // the menu is rendered once the action is ready, so potentially in the next animation frame
        await nextTick();
        await click(target, ".o_menu_sections .o_nav_entry:nth-child(2)");
        await nextTick();
        assert.containsOnce(target, ".o_list_view");

        await click(target.querySelector(".o_data_row .o_data_cell")); // open a record
        assert.containsOnce(target, ".o_form_view");

        await openStudio(target);
        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_form_view_editor",
            "the form view should be opened"
        );
        assert.strictEqual(
            $(target).find('.o_field_widget[name="foo"]').text(),
            "yop",
            "the first partner should be displayed"
        );
    });

    QUnit.test("reload the studio view", async function (assert) {
        assert.expect(5);

        const webClient = await createEnterpriseWebClient({ serverData });

        // open app Partners (act window action), sub menu Partners (action 3)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action
        assert.strictEqual(
            $(target).find(".o_kanban_record:contains(yop)").length,
            1,
            "the first partner should be displayed"
        );

        await click(target.querySelector(".o_kanban_record")); // open a record
        assert.containsOnce(target, ".o_form_view");
        const inputs = [...target.querySelectorAll(".o_form_view input")].filter((el) => el.value === "yop");
        assert.strictEqual(inputs.length, 1, "should have open the same record")

        let prom = makeDeferred();
        const unpatch = patch(StudioView.prototype, {
            setup() {
                super.setup();
                onMounted(() => {
                    prom.resolve();
                });
            },
        });
        await openStudio(target);
        await prom;
        prom = makeDeferred();
        await webClient.env.services.studio.reload();
        await prom;
        unpatch();

        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_form_view_editor",
            "the studio view should be opened after reloading"
        );
        assert.strictEqual(
            $(target).find(".o_form_view span:contains(yop)").length,
            1,
            "should have open the same record"
        );
    });

    QUnit.test("switch view and close Studio", async function (assert) {
        assert.expect(6);

        await createEnterpriseWebClient({ serverData });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action
        assert.containsOnce(target, ".o_kanban_view");

        await openStudio(target);
        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_kanban_view_editor"
        );

        // click on tab "Views"
        await click(target.querySelector(".o_web_studio_menu .o_menu_sections a"));
        assert.containsOnce(target, ".o_web_studio_action_editor");

        // open list view
        await click(
            target.querySelector(
                ".o_web_studio_views .o_web_studio_thumbnail_item.o_web_studio_thumbnail_list"
            )
        );

        assert.containsOnce(target, ".o_web_studio_editor_manager .o_web_studio_list_view_editor");

        await leaveStudio(target);

        assert.containsNone(target, ".o_web_studio_editor_manager", "Studio should be closed");
        assert.containsOnce(target, ".o_list_view", "the list view should be opened");
    });

    QUnit.test("navigation in Studio with act_window", async function (assert) {
        assert.expect(26);

        const mockRPC = async (route) => {
            assert.step(route);
        };

        await createEnterpriseWebClient({ serverData, mockRPC });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action

        assert.verifySteps(
            [
                "/web/webclient/load_menus",
                "/web/action/load",
                "/web/dataset/call_kw/partner/get_views",
                "/web/dataset/call_kw/partner/web_search_read",
            ],
            "should have loaded the action"
        );

        await openStudio(target);

        assert.verifySteps(
            [
                "/web/dataset/call_kw/partner/get_views",

                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/partner/web_search_read",
            ],
            "should have opened the action in Studio"
        );

        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_kanban_view_editor",
            "the kanban view should be opened"
        );
        assert.strictEqual(
            $(target).find(".o_kanban_record:contains(yop)").length,
            1,
            "the first partner should be displayed"
        );

        await click(target.querySelector(".o_studio_navbar .o_menu_toggle"));

        assert.containsOnce(target, ".o_studio_home_menu");

        // open app Ponies (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_2]"));

        assert.verifySteps(
            [
                "/web/action/load",
                "/web/dataset/call_kw/pony/get_views",

                "/web_studio/get_studio_view_arch",
                "/web/dataset/call_kw/pony/web_search_read",
            ],
            "should have opened the navigated action in Studio"
        );

        assert.containsOnce(
            target,
            ".o_web_studio_editor_manager .o_web_studio_list_view_editor",
            "the list view should be opened"
        );
        assert.strictEqual(
            $(target).find(".o_list_view .o_data_cell").text(),
            "Twilight SparkleApplejackFluttershy",
            "the list of ponies should be correctly displayed"
        );

        await leaveStudio(target);

        assert.verifySteps(
            [
                "/web/action/load",
                "/web/dataset/call_kw/pony/get_views",
                "/web/dataset/call_kw/pony/web_search_read",
            ],
            "should have reloaded the previous action edited by Studio"
        );

        assert.containsNone(target, ".o_web_studio_editor_manager", "Studio should be closed");
        assert.containsOnce(target, ".o_list_view", "the list view should be opened");
        assert.strictEqual(
            $(target).find(".o_list_view .o_data_cell").text(),
            "Twilight SparkleApplejackFluttershy",
            "the list of ponies should be correctly displayed"
        );
    });

    QUnit.test("keep action context when leaving Studio", async function (assert) {
        assert.expect(5);

        let nbLoadAction = 0;
        const mockRPC = async (route, args) => {
            if (route === "/web/action/load") {
                nbLoadAction++;
                if (nbLoadAction === 2) {
                    assert.strictEqual(
                        args.context.active_id,
                        1,
                        "the context should be correctly passed when leaving Studio"
                    );
                }
            }
        };
        serverData.actions[4].context = "{'active_id': 1}";

        await createEnterpriseWebClient({
            serverData,
            mockRPC,
        });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action

        assert.containsOnce(target, ".o_kanban_view");

        await openStudio(target);

        assert.containsOnce(target, ".o_web_studio_kanban_view_editor");

        await leaveStudio(target);

        assert.containsOnce(target, ".o_kanban_view");
        assert.strictEqual(nbLoadAction, 2, "the action should have been loaded twice");
    });

    QUnit.test("user context is unpolluted when entering studio in error", async (assert) => {
        assert.expectErrors();
        patchWithCleanup(StudioClientAction.prototype, {
            setup() {
                throw new Error("Boom");
            },
        });

        const mockRPC = (route, args) => {
            if (route === "/web/dataset/call_kw/partner/get_views") {
                const context = args.kwargs.context;
                const options = args.kwargs.options;
                assert.step(
                    `get_views, context studio: "${context.studio}", option studio: "${options.studio}"`
                );
            }
        };
        await createEnterpriseWebClient({
            serverData,
            mockRPC,
        });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action
        assert.verifySteps([`get_views, context studio: "undefined", option studio: "undefined"`]);

        assert.containsOnce(target, ".o_kanban_view");

        await openStudio(target);

        assert.containsNone(target, ".o_web_studio_kanban_view_editor");
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifyErrors(["Boom"]);

        await click(target.querySelector(".o_menu_sections a[data-menu-xmlid=menu_12]"));
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
        assert.verifySteps([`get_views, context studio: "undefined", option studio: "undefined"`]);
    });

    QUnit.test("user context is not polluted when getting views", async (assert) => {
        const mockRPC = (route, args) => {
            if (route === "/web/dataset/call_kw/partner/get_views") {
                const context = args.kwargs.context;
                const options = args.kwargs.options;
                assert.step(
                    `get_views, context studio: "${context.studio}", option studio: "${options.studio}"`
                );
            }
            if (route === "/web_studio/get_studio_action") {
                assert.step("get_studio_action");
                return {
                    type: "ir.actions.act_window",
                    res_model: "partner",
                    views: [[false, "list"]],
                    context: { studio: 1 },
                };
            }
            if (args.method === "web_search_read") {
                assert.step(`web_search_read, context studio: "${args.kwargs.context.studio}"`);
            }
        };
        await createEnterpriseWebClient({
            serverData,
            mockRPC,
        });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick(); // BlankComponent, first, wait for the real action
        assert.verifySteps([
            `get_views, context studio: "undefined", option studio: "undefined"`,
            `web_search_read, context studio: "undefined"`,
        ]);

        assert.containsOnce(target, ".o_kanban_view");

        await openStudio(target);
        assert.verifySteps([
            `get_views, context studio: "undefined", option studio: "true"`,
            `web_search_read, context studio: "1"`,
        ]);
        assert.containsOnce(target, ".o_web_studio_kanban_view_editor");

        await click(target.querySelector(".o_menu_sections a[data-menu-xmlid=menu_12]"));
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
        assert.verifySteps([
            `get_views, context studio: "undefined", option studio: "true"`,
            `web_search_read, context studio: "1"`,
        ]);

        await click(
            selectorContains(target, ".o_web_studio_menu .o_menu_sections a", "Automations")
        );
        await contains(".o_web_studio_editor  :not(.o_web_studio_view_renderer) .o_list_view");
        assert.verifySteps([
            "get_studio_action",
            `get_views, context studio: "undefined", option studio: "undefined"`,
            `web_search_read, context studio: "1"`,
        ]);
    });

    QUnit.test("error bubbles up if first rendering", async (assert) => {
        assert.expectErrors();
        const _console = window.console;
        window.console = Object.assign(Object.create(_console), {
            warn(msg) {
                assert.step(msg);
            },
        });
        registerCleanup(() => {
            window.console = _console;
        });

        patchWithCleanup(ListEditorRenderer.prototype, {
            setup() {
                throw new Error("Boom");
            },
        });

        await createEnterpriseWebClient({
            serverData,
        });
        // open app Partners (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
        await nextTick();
        await click(target.querySelector(".o_menu_sections [data-menu-xmlid=menu_12]"));
        await nextTick();
        assert.containsOnce(target, ".o_list_view");

        await openStudio(target);
        assert.verifyErrors(["Boom"]);
        // FIXME : due to https://github.com/odoo/owl/issues/1298,
        // the visual result is not asserted here, ideally we'd want to be in the studio
        // action, with a blank editor
    });

    QUnit.test("error when new app's view is invalid", async (assert) => {
        assert.expectErrors();

        serverData.menus.root.children.push(99);
        serverData.menus[99] = {
            id: 99,
            children: [],
            actionID: 99,
            xmlid: "testMenu",
            name: "test",
            appID: 99,
        };
        serverData.actions[99] = {
            xmlid: "testAction",
            id: 99,
            type: "ir.actions.act_window",
            res_model: "partner",
            views: [[false, "list"]],
            help: "",
            name: "test action",
            groups_id: [],
        };

        await createEnterpriseWebClient({
            serverData,
            mockRPC: async (route, args) => {
                if (route === "/web_studio/create_new_app") {
                    return { menu_id: 99, action_id: 99 };
                }
                if (route === "/web_studio/get_studio_view_arch") {
                    return Promise.reject(new Error("Boom"));
                }
            },
        });

        await click(target, ".o_web_studio_navbar_item button");
        await click(target, ".o_web_studio_new_app");
        await click(target, ".o_web_studio_app_creator_next");
        await editInput(target, ".o_web_studio_app_creator_name input", "testApp");
        await click(target, ".o_web_studio_app_creator_next");
        await editInput(target, ".o_web_studio_menu_creator input", "testMenu");
        await click(target, ".o_web_studio_app_creator_next");
        await click(target, ".o_web_studio_model_configurator_next");
        await contains(".o_web_studio_action_editor");
        // Wait for the error event to be handled
        await nextTick();
        assert.verifyErrors(["Boom"]);
    });

    QUnit.test("open same record when leaving form", async function (assert) {
        await createEnterpriseWebClient({ serverData });
        // open app Ponies (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_2]"));
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
        // Dont'pick the first record for testing
        await click(target.querySelectorAll(".o_data_row .o_data_cell")[1]);
        assert.strictEqual(
            target.querySelector(".o_form_view .o_field_widget[name=name] input").value,
            "Applejack"
        );
        assert.containsOnce(target, ".o_form_view");

        await openStudio(target);
        assert.strictEqual(
            target.querySelector(
                ".o_form_view .o_field_widget[data-studio-xpath='/form[1]/field[1]'] span"
            ).textContent,
            "Applejack"
        );
        assert.containsOnce(target, ".o_web_studio_editor_manager .o_web_studio_form_view_editor");

        await leaveStudio(target);
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_view .o_field_widget[name=name] input");
        assert.strictEqual(
            target.querySelector(".o_form_view .o_field_widget[name=name] input").value,
            "Applejack"
        );
    });

    QUnit.test("open Studio with non editable view", async function (assert) {
        assert.expect(2);

        serverData.menus[99] = {
            id: 9,
            children: [],
            name: "Action with Grid view",
            appID: 9,
            actionID: 99,
            xmlid: "app_9",
        };
        serverData.menus.root.children.push(99);
        serverData.actions[99] = {
            id: 99,
            xml_id: "some.xml_id",
            name: "Partners Action 99",
            res_model: "partner",
            type: "ir.actions.act_window",
            help: "",
            groups_id: [],
            views: [
                [42, "grid"],
                [2, "list"],
                [false, "form"],
            ],
        };
        serverData.views["partner,42,grid"] = `
            <grid>
                <field name="foo" type="row"/>
                <field name="id" type="measure"/>
                <field name="date" type="col">
                    <range name="week" string="Week" span="week" step="day"/>
                </field>
            </grid>`;

        await createEnterpriseWebClient({
            serverData,
            async mockRPC(route, args) {
                if (args.method === "grid_unavailability") {
                    return {};
                }
            },
        });
        await click(target.querySelector(".o_app[data-menu-xmlid=app_9]"));
        await nextTick(); // BlankComponent, first, wait for the real action

        assert.containsOnce(target, ".o_grid_view");

        await openStudio(target);

        assert.containsOnce(
            target,
            ".o_web_studio_action_editor",
            "action editor should be opened (grid is not editable)"
        );
    });

    QUnit.test(
        "open list view with sample data gives empty list view in studio",
        async function (assert) {
            assert.expect(2);

            serverData.models.pony.records = [];
            serverData.views["pony,false,list"] = `<list sample="1"><field name="name"/></list>`;

            await createEnterpriseWebClient({
                serverData,
            });
            // open app Ponies (act window action)
            await click(target.querySelector(".o_app[data-menu-xmlid=app_2]"));
            await nextTick(); // BlankComponent, first, wait for the real action

            assert.ok(
                [...target.querySelectorAll(".o_list_table .o_data_row")].length > 0,
                "there should be some sample data in the list view"
            );

            await openStudio(target);

            assert.containsNone(
                target,
                ".o_list_table .o_data_row",
                "the list view should not contain any data"
            );
        }
    );

    QUnit.test("kanban in studio should always ignore sample data", async function (assert) {
        serverData.models.pony.fields.m2o = {
            string: "m2o",
            relation: "partner",
            type: "many2one",
        };

        serverData.actions[8].views = [[false, "kanban"]];
        serverData.models.pony.records = [];
        serverData.views["pony,false,kanban"] = `
                <kanban sample="1" default_group_by="m2o">
                    <t t-name="card">
                        <field name="name"/>
                        <field name="m2o" />
                    </t>
                </kanban>`;

        await createEnterpriseWebClient({
            serverData,
        });
        // open app Ponies (act window action)
        await click(target.querySelector(".o_app[data-menu-xmlid=app_2]"));
        await nextTick(); // BlankComponent, first, wait for the real action

        assert.ok(
            [...target.querySelectorAll(".o_kanban_view .o_kanban_examples_ghost")].length > 0,
            "there should be some sample data in the kanban view"
        );

        await openStudio(target);

        assert.containsOnce(
            target,
            ".o_web_studio_kanban_view_editor .o_kanban_group .o_kanban_record:not(.o_kanban_ghost):not(.o_kanban_demo)",
            "the kanban view should not contain any sample data"
        );

        assert.containsNone(target, "o_web_studio_kanban_view_editor .o_view_nocontent");
    });

    QUnit.test("entering a kanban keeps the user's domain", async (assert) => {
        serverData.views["pony,false,kanban"] = `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name" />
                    </t>
                </templates>
            </kanban>
        `;

        serverData.views["pony,58,search"] = `
            <search>
                <filter name="apple" string="apple" domain="[('name', 'ilike', 'Apple')]" />
            </search>
        `;

        serverData.menus[43] = {
            id: 43,
            children: [],
            name: "kanban",
            appID: 43,
            actionID: 43,
            xmlid: "app_43",
        };
        serverData.menus.root.children.push(43);
        serverData.actions[43] = {
            id: 43,
            name: "Pony Action 43",
            res_model: "pony",
            type: "ir.actions.act_window",
            views: [[false, "kanban"]],
            search_view_id: [58],
            xml_id: "action_43",
        };

        const mockRPC = async (route, args) => {
            if (args.method === "web_search_read") {
                assert.step(`${args.method}: ${JSON.stringify(args.kwargs)}`);
            }
        };

        await createEnterpriseWebClient({
            serverData,
            mockRPC,
        });
        assert.verifySteps([]);
        await click(target.querySelector(".o_app[data-menu-xmlid=app_43]"));
        await nextTick();
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps([
            `web_search_read: {"specification":{"display_name":{}},"offset":0,"order":"","limit":40,"context":{"lang":"en","tz":"taht","allowed_company_ids":[1],"uid":7,"bin_size":true,"current_company_id":1},"count_limit":10001,"domain":[]}`,
        ]);
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Apple");
        assert.verifySteps([
            `web_search_read: {"specification":{"display_name":{}},"offset":0,"order":"","limit":40,"context":{"lang":"en","tz":"taht","allowed_company_ids":[1],"uid":7,"bin_size":true,"current_company_id":1},"count_limit":10001,"domain":[["name","ilike","Apple"]]}`,
        ]);

        await openStudio(target);
        assert.containsOnce(target, ".o_web_studio_kanban_view_editor");
        assert.verifySteps([
            `web_search_read: {"specification":{"display_name":{}},"offset":0,"order":"","limit":1,"context":{"lang":"en","tz":"taht","allowed_company_ids":[1],"uid":7,"bin_size":true,"studio":1,"current_company_id":1},"count_limit":10001,"domain":[["name","ilike","Apple"]]}`,
        ]);
        assert.strictEqual(target.querySelector(".o_kanban_record").textContent, "Applejack");
    });

    QUnit.test(
        "open Studio with editable form view and check context propagation",
        async function (assert) {
            assert.expect(6);

            serverData.menus[43] = {
                id: 43,
                children: [],
                name: "Form with context",
                appID: 43,
                actionID: 43,
                xmlid: "app_43",
            };
            serverData.menus.root.children.push(43);
            serverData.actions[43] = {
                id: 43,
                name: "Pony Action 43",
                res_model: "pony",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                context: "{'default_type': 'foo'}",
                res_id: 4,
                xml_id: "action_43",
                groups_id: [],
            };

            const mockRPC = async (route, args) => {
                if (route === "/web/dataset/call_kw/pony/web_read") {
                    // We pass here twice: once for the "classic" action
                    // and once when entering studio
                    assert.strictEqual(args.kwargs.context.default_type, "foo");
                }
                if (route === "/web/dataset/call_kw/partner/onchange") {
                    assert.ok(
                        !("default_type" in args.kwargs.context),
                        "'default_x' context value should not be propaged to x2m model"
                    );
                }
            };

            await createEnterpriseWebClient({
                serverData,
                mockRPC,
            });
            await click(target.querySelector(".o_app[data-menu-xmlid=app_43]"));
            await nextTick(); // BlankComponent, first, wait for the real action

            assert.containsOnce(target, ".o_form_view");

            await openStudio(target);

            assert.containsOnce(
                target,
                ".o_web_studio_editor_manager .o_web_studio_form_view_editor",
                "the form view should be opened"
            );

            await click(target.querySelector(".o_web_studio_form_view_editor .o_field_one2many"));
            await click(
                target.querySelector(
                    '.o_web_studio_form_view_editor .o_field_one2many .o_web_studio_editX2Many[data-type="form"]'
                )
            );

            assert.containsOnce(
                target,
                ".o_web_studio_editor_manager .o_web_studio_form_view_editor",
                "the form view should be opened"
            );
        }
    );

    QUnit.test(
        "concurrency: execute a non editable action and try to enter studio",
        async function (assert) {
            // the purpose of this test is to ensure that there's no time window
            // during which if the icon isn't disabled, but the current action isn't
            // editable (typically, just after the current action has changed).
            assert.expect(5);

            const def = makeDeferred();
            serverData.actions[4].xml_id = false; // make action 4 non editable
            const webClient = await createEnterpriseWebClient({ serverData });
            assert.containsOnce(target, ".o_home_menu");

            webClient.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", () => {
                assert.containsOnce(target, ".o_kanban_view");
                assert.hasClass(target.querySelector(".o_web_studio_navbar_item"), "o_disabled");
                def.resolve();
            });

            // open app Partners (non editable act window action)
            await click(target.querySelector(".o_app[data-menu-xmlid=app_1]"));
            await def;

            assert.containsOnce(target, ".o_kanban_view");
            assert.hasClass(target.querySelector(".o_web_studio_navbar_item"), "o_disabled");
        }
    );

    QUnit.test("command palette inside studio", async (assert) => {
        registry.category("services").add("command", commandService);
        await createEnterpriseWebClient({ serverData });
        await openStudio(target);

        // disable opacity: 0 in tests
        // doesn't have any effect on the test itself
        document.body.classList.add("debug");
        registerCleanup(() => document.body.classList.remove("debug"));
        target.classList.add("debug");

        assert.containsOnce(target, ".o_studio_home_menu");
        const hiddenInput = target.querySelector("input.o_search_hidden");
        hiddenInput.value = "Part";
        await triggerEvents(hiddenInput, null, ["input"]);
        assert.containsOnce(target, ".o_command_palette");

        await click(target.querySelector(".o_command_palette .o_command"));
        await nextTick();
        assert.containsNone(target, ".o_studio_home_menu");
        assert.containsOnce(target, ".o_studio .o_web_studio_kanban_view_editor");
    });

    QUnit.test("command palette inside studio with error", async (assert) => {
        serverData.menus.root.children.push(99);
        serverData.menus[99] = {
            id: 99,
            children: [],
            actionID: 99,
            xmlid: "testMenu",
            name: "On Error",
            appID: 99,
        };
        serverData.actions[99] = {
            id: 99,
            type: "ir.actions.act_window",
            res_model: "partner",
            views: [[false, "list"]],
            name: "test action",
            groups_id: [],
        };

        registry.category("services").add("command", commandService);
        await createEnterpriseWebClient({ serverData });
        await openStudio(target);

        // disable opacity: 0 in tests
        // doesn't have any effect on the test itself
        document.body.classList.add("debug");
        registerCleanup(() => document.body.classList.remove("debug"));
        target.classList.add("debug");

        assert.containsOnce(target, ".o_studio_home_menu");
        const hiddenInput = target.querySelector("input.o_search_hidden");
        hiddenInput.value = "On Error";

        await triggerEvents(hiddenInput, null, ["input"]);
        assert.containsOnce(target, ".o_command_palette");

        await click(target.querySelector(".o_command_palette .o_command"));
        await nextTick();
        assert.containsOnce(target, "div.o_notification[role=alert]");
    });

    QUnit.test("leaving studio with a pending rendering in Studio", async (assert) => {
        serverData.models.pony.fields.selection = {
            type: "selection",
            selection: [["1", "1"]],
            manual: true,
        };
        serverData.models.pony.records = [{ id: 1, selection: "1" }];

        serverData.views["pony,false,form"] = `<form><field name="selection" /></form>`;
        let vem;
        patchWithCleanup(ViewEditor.prototype, {
            setup() {
                super.setup();
                vem = this;
            },
        });

        const loadActionDef = makeDeferred();
        let enableRPCWatch = false;
        const mockRPC = async (route, args) => {
            if (!enableRPCWatch) {
                return;
            }
            let res;
            if (route === "/web/action/load") {
                await loadActionDef;
            }
            if (args.method === "web_read") {
                res = [{ id: args.args[0], selection: "2" }];
            }

            assert.step(route);
            return res;
        };

        await createEnterpriseWebClient({ serverData, mockRPC });
        await click(target.querySelector(".o_app[data-menu-xmlid=app_2]"));
        await contains(".o_data_cell");
        await click(target.querySelector(".o_data_cell"));
        await contains(".o_form_view");
        await openStudio(target);
        await contains(".o_studio");

        await contains(".o_field_widget[name='selection']", { text: "1" });

        enableRPCWatch = true;
        await click(target.querySelector(".o_web_studio_leave"));
        vem.viewEditorModel.fields.selection.selection.push(["2", "2"]);
        await contains(".o_field_widget[name='selection']", { text: "2" });

        loadActionDef.resolve();
        await loadActionDef;
        await contains("body:not(:has(.o_studio)) .o_form_view");

        assert.verifySteps([
            "/web/dataset/call_kw/pony/web_read",
            "/web/action/load",
            "/web/dataset/call_kw/pony/get_views",
            "/web/dataset/call_kw/pony/web_read",
        ]);
    });

    QUnit.test("auto-save feature works in studio (not editing a view)", async (assert) => {
        serverData.models["base.automation"] = {
            fields: {},
            records: [],
        };

        serverData.views[
            "base.automation,false,list"
        ] = `<list><field name="display_name" /></list>`;
        serverData.views["base.automation,false,search"] = `<search/>`;

        serverData.views[
            "base.automation,false,form"
        ] = `<form><field name="display_name" /></form>`;
        const mockRPC = (route, args) => {
            if (route === "/web_studio/get_studio_action") {
                return {
                    name: "Automated Actions",
                    type: "ir.actions.act_window",
                    res_model: "base.automation",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                };
            }

            if (args.method === "web_save") {
                assert.step(`web_save: ${args.model}: ${JSON.stringify(args.args)}`);
            }
        };
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient.env, 1);
        await openStudio(target);
        const menuAutomations = Array.from(target.querySelectorAll(".o_menu_sections a")).find(
            (el) => el.textContent === "Automations"
        );
        await click(menuAutomations);
        await click(target.querySelector(".o_web_studio_editor .o_list_button_add"));
        await editInput(
            target,
            ".o_field_widget[name='display_name'] input",
            "created base automation"
        );
        await click(target, ".o_web_studio_leave");
        assert.verifySteps([
            'web_save: base.automation: [[],{"display_name":"created base automation"}]',
        ]);
        assert.containsNone(target, ".o_studio");
        assert.containsOnce(target, ".o_kanban_view");
    });

    QUnit.test("load with active_id active_ids", async (assert) => {
        serverData.actions[4].context = `{"some_key": active_ids}`;
        redirect("/odoo/studio?mode=editor&_action=4&_view_type=form&_tab=views&active_id=451")
        await createEnterpriseWebClient({
            serverData,
            mockRPC: (route, args) => {
                if (args.method === "onchange") {
                    assert.step("onchange");
                    assert.deepEqual(args.kwargs.context, {
                        active_id: 451,
                        active_ids: [451],
                        allowed_company_ids: [1],
                        lang: "en",
                        some_key: [451],
                        studio: 1,
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });
        await contains(".o_web_studio_view_renderer .o_form_view");
        assert.verifySteps(["onchange"]);
    });
});
