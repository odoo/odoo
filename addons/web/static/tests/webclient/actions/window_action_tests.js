/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { editView } from "@web/views/debug_items";
import { clearUncommittedChanges } from "@web/webclient/actions/action_service";
import { listView } from "@web/views/list/list_view";
import { useSetupAction } from "@web/webclient/actions/action_hook";
import testUtils from "web.test_utils";
import { session } from "@web/session";
import {
    click,
    getFixture,
    editInput,
    getNodesTextContent,
    legacyExtraNextTick,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    clickSave,
} from "../../helpers/utils";
import { createWebClient, doAction, getActionManagerServerData, loadState } from "./../helpers";
import { errorService } from "../../../src/core/errors/error_service";
import { RPCError } from "@web/core/network/rpc_service";
import { registerCleanup } from "../../helpers/cleanup";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { makeFakeUserService, fakeCookieService } from "@web/../tests/helpers/mock_services";
import * as cpHelpers from "@web/../tests/search/helpers";

import { onMounted } from "@odoo/owl";
let serverData;
let target;
const serviceRegistry = registry.category("services");

QUnit.module("ActionManager", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
    });

    QUnit.module("Window Actions");

    QUnit.test("can execute act_window actions from db ID", async function (assert) {
        assert.expect(7);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(
            document.body,
            ".o_control_panel",
            "should have rendered a control panel"
        );
        assert.containsOnce(target, ".o_kanban_view", "should have rendered a kanban view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("sidebar is present in list view", async function (assert) {
        assert.expect(4);

        serverData.models.partner.toolbar = {
            print: [{ name: "Print that record" }],
        };
        const mockRPC = async (route, args) => {
            if (args && args.method === "get_views") {
                assert.strictEqual(
                    args.kwargs.options.toolbar,
                    true,
                    "should ask for toolbar information"
                );
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsNone(target, ".o_cp_action_menus");
        await click(target.querySelector("input.form-check-input"));
        assert.isVisible(
            $(target).find('.o_cp_action_menus button.dropdown-toggle:contains("Print")')[0]
        );
        assert.isVisible(
            $(target).find('.o_cp_action_menus button.dropdown-toggle:contains("Action")')[0]
        );
    });

    QUnit.test("can switch between views", async function (assert) {
        assert.expect(19);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view", "should display the list view");
        // switch to kanban view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "should no longer display the list view");
        assert.containsOnce(target, ".o_kanban_view", "should display the kanban view");
        // switch back to list view
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should display the list view");
        assert.containsNone(target, ".o_kanban_view", "should no longer display the kanban view");
        // open a record in form view
        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "should no longer display the list view");
        assert.containsOnce(target, ".o_form_view", "should display the form view");
        assert.strictEqual(
            $(target).find(".o_field_widget[name=foo] input").val(),
            "yop",
            "should have opened the correct record"
        );
        // go back to list view using the breadcrumbs
        await testUtils.dom.click(target.querySelector(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should display the list view");
        assert.containsNone(target, ".o_form_view", "should no longer display the form view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "web_search_read",
            "web_search_read",
            "read",
            "web_search_read",
        ]);
    });

    QUnit.test("switching into a view with mode=edit lands in edit mode", async function (assert) {
        serverData.views["partner,1,kanban"] = `
            <kanban on_create="quick_create" default_group_by="m2o">
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click"><field name="foo"/></div>
                    </t>
                </templates>
            </kanban>`;
        serverData.actions[1] = {
            id: 1,
            xml_id: "action_1",
            name: "Partners Action 1 patched",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
        };
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view", "should display the kanban view");
        // quick create record
        await testUtils.dom.click(target.querySelector(".o-kanban-button-new"));
        await editInput(target, ".o_field_widget[name=display_name] input", "New name");

        // edit quick-created record
        await testUtils.dom.click(target.querySelector(".o_kanban_edit"));
        assert.containsOnce(
            target,
            ".o_form_view .o_form_editable",
            "should display the form view in edit mode"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_read_group",
            "web_search_read",
            "web_search_read",
            "onchange",
            "name_create",
            "read",
            "read",
        ]);
    });

    QUnit.test(
        "orderedBy in context is not propagated when executing another action",
        async function (assert) {
            assert.expect(6);
            serverData.models.partner.fields.foo.sortable = true;
            serverData.views["partner,false,form"] = `
        <form>
          <header>
            <button name="8" string="Execute action" type="action"/>
          </header>
        </form>`;
            serverData.models.partner.filters = [
                {
                    id: 1,
                    context: "{}",
                    domain: "[]",
                    sort: "[]",
                    is_default: true,
                    name: "My filter",
                },
            ];
            let searchReadCount = 1;
            const mockRPC = async (route, args) => {
                if (args.method === "web_search_read") {
                    args = args || {};
                    if (searchReadCount === 1) {
                        assert.strictEqual(args.model, "partner");
                        assert.notOk(args.sort);
                    }
                    if (searchReadCount === 2) {
                        assert.strictEqual(args.model, "partner");
                        assert.strictEqual(args.kwargs.order, "foo ASC");
                    }
                    if (searchReadCount === 3) {
                        assert.strictEqual(args.model, "pony");
                        assert.notOk(args.sort);
                    }
                    searchReadCount += 1;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 3);
            // Sort records
            await click(target.querySelector(".o_list_view th.o_column_sortable"));
            // Get to the form view of the model, on the first record
            await click(target.querySelector(".o_data_cell"));
            // Execute another action by clicking on the button within the form
            await click(target.querySelector('button[name="8"]'));
        }
    );

    QUnit.test("breadcrumbs are updated when switching between views", async function (assert) {
        assert.expect(15);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item").text(),
            "Partners",
            "breadcrumbs should display the display_name of the action"
        );
        // switch to kanban view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should still be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item").text(),
            "Partners",
            "breadcrumbs should still display the display_name of the action"
        );
        // open a record in form view
        await testUtils.dom.click(target.querySelector(".o_kanban_view .o_kanban_record"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record"
        );
        // go back to kanban view using the breadcrumbs
        await testUtils.dom.click(target.querySelector(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item").text(),
            "Partners",
            "breadcrumbs should display the display_name of the action"
        );
        // switch back to list view
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should still be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item").text(),
            "Partners",
            "breadcrumbs should still display the display_name of the action"
        );
        // open a record in form view
        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record"
        );
        // go back to list view using the breadcrumbs
        await testUtils.dom.click(target.querySelector(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should be back on list view");
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item").text(),
            "Partners",
            "breadcrumbs should display the display_name of the action"
        );
    });

    QUnit.test("switch buttons are updated when switching between views", async function (assert) {
        assert.expect(13);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsN(
            target,
            ".o_control_panel button.o_switch_view",
            2,
            "should have two switch buttons (list and kanban)"
        );
        assert.containsOnce(
            target,
            ".o_control_panel button.o_switch_view.active",
            "should have only one active button"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view"),
            "o_list",
            "list switch button should be the first one"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view.o_list"),
            "active",
            "list should be the active view"
        );
        // switch to kanban view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .o_switch_view",
            2,
            "should still have two switch buttons (list and kanban)"
        );
        assert.containsOnce(
            target,
            ".o_control_panel .o_switch_view.active",
            "should still have only one active button"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view"),
            "o_list",
            "list switch button should still be the first one"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view.o_kanban"),
            "active",
            "kanban should now be the active view"
        );
        // switch back to list view
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .o_switch_view",
            2,
            "should still have two switch buttons (list and kanban)"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view.o_list"),
            "active",
            "list should now be the active view"
        );
        // open a record in form view
        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsNone(
            target,
            ".o_control_panel .o_switch_view",
            "should not have any switch buttons"
        );
        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .o_switch_view",
            2,
            "should have two switch buttons (list and kanban)"
        );
        assert.hasClass(
            target.querySelector(".o_control_panel .o_switch_view.o_list"),
            "active",
            "list should be the active view"
        );
    });
    QUnit.test("pager is updated when switching between views", async function (assert) {
        assert.expect(10);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 4);
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_value").text(),
            "1-5",
            "value should be correct for kanban"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_limit").text(),
            "5",
            "limit should be correct for kanban"
        );
        // switch to list view
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_value").text(),
            "1-3",
            "value should be correct for list"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_limit").text(),
            "5",
            "limit should be correct for list"
        );
        // open a record in form view
        await testUtils.dom.click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_value").text(),
            "1",
            "value should be correct for form"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_limit").text(),
            "3",
            "limit should be correct for form"
        );
        // go back to list view using the breadcrumbs
        await testUtils.dom.click(target.querySelector(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_value").text(),
            "1-3",
            "value should be correct for list"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_limit").text(),
            "5",
            "limit should be correct for list"
        );
        // switch back to kanban view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_value").text(),
            "1-5",
            "value should be correct for kanban"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .o_pager_limit").text(),
            "5",
            "limit should be correct for kanban"
        );
    });

    QUnit.test("Props are updated and kept when switching/restoring views", async (assert) => {
        serverData.views["partner,false,form"] = /* xml */ `
            <form>
                <group>
                    <field name="display_name" />
                    <field name="m2o" open_target="current" />
                </group>
            </form>
        `;

        const mockRPC = async (_route, { args, method, model }) => {
            if (method === "get_formview_action") {
                return {
                    res_id: args[0][0],
                    res_model: model,
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                };
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);

        // 5 records initially
        assert.containsN(target, ".o_data_row", 5);

        await click(target, ".o_data_row:first-of-type .o_data_cell");

        // Open 1 / 5
        assert.strictEqual(target.querySelector(".o_field_char input").value, "First record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [1]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 5);

        await click(target, ".o_field_many2one .o_external_button");

        // Click on M2O -> 1 / 1
        assert.strictEqual(target.querySelector(".o_field_char input").value, "Third record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [1]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 1);

        await click(target, ".o_back_button");

        // Back to 1 / 5
        assert.strictEqual(target.querySelector(".o_field_char input").value, "First record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [1]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 5);

        await cpHelpers.pagerNext(target);

        // Next page -> 2 / 5
        assert.strictEqual(target.querySelector(".o_field_char input").value, "Second record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [2]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 5);

        await click(target, ".o_field_many2one .o_external_button");

        // Click on M2O -> still 1 / 1
        assert.strictEqual(target.querySelector(".o_field_char input").value, "Third record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [1]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 1);

        await click(target, ".o_back_button");

        // Back to 2 / 5
        assert.strictEqual(target.querySelector(".o_field_char input").value, "Second record");
        assert.deepEqual(cpHelpers.getPagerValue(target), [2]);
        assert.strictEqual(cpHelpers.getPagerLimit(target), 5);
    });

    QUnit.test("domain is kept when switching between views", async function (assert) {
        assert.expect(5);
        serverData.actions[3].search_view_id = [4, "a custom search view"];
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsN(target, ".o_data_row", 5);
        // activate a domain
        await cpHelpers.toggleFilterMenu(target);
        await cpHelpers.toggleMenuItem(target, "Bar");
        await legacyExtraNextTick();
        assert.containsN(target, ".o_data_row", 2);
        // switch to kanban
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
        // remove the domain
        await testUtils.dom.click(target.querySelector(".o_searchview .o_facet_remove"));
        await legacyExtraNextTick();
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
        // switch back to list
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsN(target, ".o_data_row", 5);
    });

    QUnit.test("A new form view can be reloaded after a failed one", async function (assert) {
        assert.expect(5);
        const webClient = await createWebClient({serverData});

        await doAction(webClient, 3);
        await cpHelpers.switchView(target, "list");
        assert.containsOnce(target, ".o_list_view", "The list view should be displayed");

        // Click on the first record
        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:first .o_data_cell:first"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view", "The form view should be displayed");

        // Delete the current record
        await testUtils.controlPanel.toggleActionMenu(target);
        await testUtils.dom.click(
            Array.from(document.querySelectorAll('.o_menu_item')).find(e => e.textContent === "Delete")
        );
        await legacyExtraNextTick();
        assert.containsOnce(target, ".modal", "a confirm modal should be displayed");
        await testUtils.dom.click(target.querySelector(".modal-footer button.btn-primary"));
        await legacyExtraNextTick();

        // The form view is automatically switched to the next record
        // Go back to the previous (now deleted) record
        webClient.env.bus.trigger("test:hashchange", {
            model: "partner",
            id: 1,
            action: 3,
            view_type: "form",
        });
        await legacyExtraNextTick();

        // Go back to the list view
        webClient.env.bus.trigger("test:hashchange", {
            model: "partner",
            action: 3,
            view_type: "list",
        });
        await legacyExtraNextTick();
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still display the list view");

        await testUtils.dom.click($(target).find(".o_list_view .o_data_row:first .o_data_cell:first"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view",
            "The form view should still load after a previous failed update | reload");
    });

    QUnit.test("there is no flickering when switching between views", async function (assert) {
        assert.expect(20);
        let def;
        const mockRPC = async (route, args) => {
            await def;
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // switch to kanban view
        def = testUtils.makeTestPromise();
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still display the list view");
        assert.containsNone(target, ".o_kanban_view", "shouldn't display the kanban view yet");
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "shouldn't display the list view anymore");
        assert.containsOnce(target, ".o_kanban_view", "should now display the kanban view");
        // switch back to list view
        def = testUtils.makeTestPromise();
        await cpHelpers.switchView(target, "list");
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view", "should still display the kanban view");
        assert.containsNone(target, ".o_list_view", "shouldn't display the list view yet");
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_kanban_view", "shouldn't display the kanban view anymore");
        assert.containsOnce(target, ".o_list_view", "should now display the list view");
        // open a record in form view
        def = testUtils.makeTestPromise();
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still display the list view");
        assert.containsNone(target, ".o_form_view", "shouldn't display the form view yet");
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should still be one controller in the breadcrumbs"
        );
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_list_view", "should no longer display the list view");
        assert.containsOnce(target, ".o_form_view", "should display the form view");
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        // go back to list view using the breadcrumbs
        def = testUtils.makeTestPromise();
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view", "should still display the form view");
        assert.containsNone(target, ".o_list_view", "shouldn't display the list view yet");
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should still be two controllers in the breadcrumbs"
        );
        def.resolve();
        await testUtils.nextTick();
        await legacyExtraNextTick();
        assert.containsNone(target, ".o_form_view", "should no longer display the form view");
        assert.containsOnce(target, ".o_list_view", "should display the list view");
        assert.containsOnce(
            target,
            ".o_control_panel .breadcrumb-item",
            "there should be one controller in the breadcrumbs"
        );
    });

    QUnit.test("breadcrumbs are updated when display_name changes", async function (assert) {
        assert.expect(4);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        // switch to edit mode and change the display_name
        await editInput(target, ".o_field_widget[name=display_name] input", "New name");
        await clickSave(target);
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should still be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "New name",
            "breadcrumbs should contain the display_name of the opened record"
        );
    });

    QUnit.test('reverse breadcrumb works on accesskey "b"', async function (assert) {
        assert.expect(4);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        await testUtils.dom.click($(target).find(".o_form_view button:contains(Execute action)"));
        assert.containsN(target, ".o_control_panel .breadcrumb li", 3);
        let $previousBreadcrumb = $(target).find(".o_control_panel .breadcrumb li.active").prev();
        assert.strictEqual(
            $previousBreadcrumb.attr("data-hotkey"),
            "b",
            "previous breadcrumb should have accessKey 'b'"
        );
        await testUtils.dom.click($previousBreadcrumb);
        assert.containsN(target, ".o_control_panel .breadcrumb li", 2);
        $previousBreadcrumb = $(target).find(".o_control_panel .breadcrumb li.active").prev();
        assert.strictEqual(
            $previousBreadcrumb.attr("data-hotkey"),
            "b",
            "previous breadcrumb should have accessKey 'b'"
        );
    });

    QUnit.test("reload previous controller when discarding a new record", async function (assert) {
        assert.expect(9);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // create a new record
        await testUtils.dom.click($(target).find(".o_control_panel .o_list_button_add"));
        await legacyExtraNextTick();
        assert.containsOnce(
            target,
            ".o_form_view .o_form_editable",
            "should have opened the form view in edit mode"
        );
        // discard
        await testUtils.dom.click($(target).find(".o_control_panel .o_form_button_cancel"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should have switched back to the list view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "onchange",
            "web_search_read",
        ]);
    });

    QUnit.test("requests for execute_action of type object are handled", async function (assert) {
        assert.expect(11);
        patchWithCleanup(session.user_context, { some_key: 2 });
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (route === "/web/dataset/call_button") {
                assert.deepEqual(
                    args,
                    {
                        args: [[1]],
                        kwargs: {
                            context: {
                                lang: "en",
                                uid: 7,
                                tz: "taht",
                                some_key: 2,
                            },
                        },
                        method: "object",
                        model: "partner",
                    },
                    "should call route with correct arguments"
                );
                const record = serverData.models.partner.records.find(
                    (r) => r.id === args.args[0][0]
                );
                record.foo = "value changed";
                return Promise.resolve(false);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_field_widget[name=foo] input").val(),
            "yop",
            "check initial value of 'yop' field"
        );
        // click on 'Call method' button (should call an Object method)
        await testUtils.dom.click($(target).find(".o_form_view button:contains(Call method)"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_field_widget[name=foo] input").val(),
            "value changed",
            "'yop' has been changed by the server, and should be updated in the UI"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "read",
            "object",
            "read",
        ]);
    });

    QUnit.test(
        "requests for execute_action of type object: disable buttons (2)",
        async function (assert) {
            assert.expect(6);
            serverData.views["pony,44,form"] = `
    <form>
    <field name="name"/>
    <button string="Cancel" class="cancel-btn" special="cancel"/>
    </form>`;
            serverData.actions[4] = {
                id: 4,
                name: "Create a Partner",
                res_model: "pony",
                target: "new",
                type: "ir.actions.act_window",
                views: [[44, "form"]],
            };
            const def = testUtils.makeTestPromise();
            const mockRPC = async (route, args) => {
                if (args.method === "onchange") {
                    // delay the opening of the dialog
                    await def;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");
            // open first record in form view
            await testUtils.dom.click(target.querySelector(".o_list_view .o_data_cell"));
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_form_view");
            // click on 'Execute action', to execute action 4 in a dialog
            await testUtils.dom.click(target.querySelector('.o_form_view button[name="4"]'));
            await legacyExtraNextTick();
            assert.ok(
                target.querySelector(".o_form_button_create").disabled,
                "control panel buttons should be disabled"
            );
            def.resolve();
            await nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".modal .o_form_view");
            assert.notOk(
                target.querySelector(".o_form_button_create").disabled,
                "control panel buttons should have been re-enabled"
            );
            await testUtils.dom.click(target.querySelector(".modal .cancel-btn"));
            await legacyExtraNextTick();
            assert.notOk(
                target.querySelector(".o_form_button_create").disabled,
                "control panel buttons should still be enabled"
            );
        }
    );

    QUnit.test(
        "requests for execute_action of type object raises error: re-enables buttons",
        async function (assert) {
            assert.expect(3);
            const mockRPC = async (route, args) => {
                if (route === "/web/dataset/call_button") {
                    return Promise.reject();
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 3, { viewType: "form" });
            assert.containsOnce(target, ".o_form_view");
            // save to ensure the presence of the create button
            await click(target.querySelector(".o_form_button_save"));
            // click on 'Execute action', to execute action 4 in a dialogdebugger
            click(target.querySelector('.o_form_view button[name="object"]'));
            assert.ok(target.querySelector(".o_form_button_create").disabled);
            await nextTick();
            await legacyExtraNextTick();
            assert.notOk(target.querySelector(".o_form_button_create").disabled);
        }
    );

    QUnit.test(
        "requests for execute_action of type object raises error in modal: re-enables buttons",
        async function (assert) {
            assert.expect(5);
            serverData.views["partner,false,form"] = `
        <form>
          <field name="display_name"/>
          <footer>
            <button name="object" string="Call method" type="object"/>
          </footer>
        </form>
      `;
            const mockRPC = async (route, args) => {
                if (route === "/web/dataset/call_button") {
                    return Promise.reject();
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 5);
            assert.containsOnce(target, ".modal .o_form_view");
            testUtils.dom.click(target.querySelector('.modal footer button[name="object"]'));
            assert.containsOnce(target, ".modal .o_form_view");
            assert.ok(target.querySelector(".modal footer button").disabled);
            await testUtils.nextTick();
            await legacyExtraNextTick();
            assert.containsOnce(target, ".modal .o_form_view");
            assert.notOk(target.querySelector(".modal footer button").disabled);
        }
    );

    QUnit.test("requests for execute_action of type action are handled", async function (assert) {
        assert.expect(12);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        // click on 'Execute action' button (should execute an action)
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two parts in the breadcrumbs"
        );
        await testUtils.dom.click($(target).find(".o_form_view button:contains(Execute action)"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            3,
            "the returned action should have been stacked over the previous one"
        );
        assert.containsOnce(
            target,
            ".o_kanban_view",
            "the returned action should have been executed"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "read",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("execute smart button and back", async function (assert) {
        const mockRPC = async (route, args) => {
            if (args.method === "read") {
                assert.step("read");
                assert.notOk("default_partner" in args.kwargs.context);
            }
            if (args.method === "web_search_read") {
                assert.step("web_search_read");
                assert.strictEqual(args.kwargs.context.default_partner, 2);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 24);
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_button_create:not([disabled])");
        await testUtils.dom.click(target.querySelector(".oe_stat_button"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_kanban_view");
        await testUtils.dom.click(target.querySelector(".breadcrumb-item"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_button_create:not([disabled])");
        assert.verifySteps(["read", "web_search_read", "read"]);
    });

    QUnit.test("execute smart button and fails", async function (assert) {
        assert.expect(13);
        const mockRPC = async (route, args) => {
            assert.step(route);
            if (args.method === "web_search_read") {
                return Promise.reject();
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 24);
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_button_create:not([disabled])");
        await testUtils.dom.click(target.querySelector(".oe_stat_button"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_button_create:not([disabled])");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/read",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
            "/web/dataset/call_kw/partner/read",
        ]);
    });

    QUnit.test(
        "requests for execute_action of type object: disable buttons",
        async function (assert) {
            assert.expect(2);
            let def = undefined;
            const mockRPC = async (route, args) => {
                if (route === "/web/dataset/call_button") {
                    return Promise.resolve(false);
                } else if (args && args.method === "read") {
                    await def; // block the 'read' call
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 3);
            // open a record in form view
            await click(target.querySelector(".o_list_view .o_data_cell"));
            await legacyExtraNextTick();
            // click on 'Call method' button (should call an Object method)
            def = testUtils.makeTestPromise();
            await testUtils.dom.click($(target).find(".o_form_view button:contains(Call method)"));
            await legacyExtraNextTick();
            // Buttons should be disabled
            assert.strictEqual(
                $(target).find(".o_form_view button:contains(Call method)").attr("disabled"),
                "disabled",
                "buttons should be disabled"
            );
            // Release the 'read' call
            def.resolve();
            await testUtils.nextTick();
            await legacyExtraNextTick();
            // Buttons should be enabled after the reload
            assert.strictEqual(
                $(target).find(".o_form_view button:contains(Call method)").attr("disabled"),
                undefined,
                "buttons should not be disabled anymore"
            );
        }
    );

    QUnit.test("action with html help returned by a call_button", async function (assert) {
        const mockRPC = async (route, args) => {
            if (route === "/web/dataset/call_button") {
                return Promise.resolve({
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                    help: "<p>I am not a helper</p>",
                    domain: [[0, "=", 1]],
                });
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);

        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));

        await click(target.querySelector(".o_statusbar_buttons button"));
        assert.strictEqual(
            target.querySelector(".o_list_view .o_nocontent_help p").innerText,
            "I am not a helper"
        );
    });

    QUnit.test("can open different records from a multi record view", async function (assert) {
        assert.expect(12);
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // open the first record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        assert.strictEqual(
            $(target).find(".o_field_widget[name=foo] input").val(),
            "yop",
            "should have opened the correct record"
        );
        // go back to list view using the breadcrumbs
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a"));
        await legacyExtraNextTick();
        // open the second record in form view
        await testUtils.dom.click(
            $(target).find(".o_list_view .o_data_row:nth(1) .o_data_cell:first")
        );
        await legacyExtraNextTick();
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "Second record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        assert.strictEqual(
            $(target).find(".o_field_widget[name=foo] input").val(),
            "blip",
            "should have opened the correct record"
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "read",
            "web_search_read",
            "read",
        ]);
    });

    QUnit.test("restore previous view state when switching back", async function (assert) {
        assert.expect(5);
        registry.category("services").add("cookie", fakeCookieService);
        serverData.actions[3].views.unshift([false, "graph"]);
        serverData.views["partner,false,graph"] = "<graph/>";
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.hasClass(
            $(target).find(".o_control_panel [data-mode='bar']")[0],
            "active",
            "bar chart button is active"
        );
        assert.doesNotHaveClass(
            $(target).find(".o_control_panel [data-mode='line']")[0],
            "active",
            "line chart button is not active"
        );
        // display line chart
        await testUtils.dom.click($(target).find(".o_control_panel [data-mode='line']"));
        await legacyExtraNextTick();
        assert.hasClass(
            $(target).find(".o_control_panel [data-mode='line']")[0],
            "active",
            "line chart button is now active"
        );
        // switch to kanban and back to graph view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsNone(
            target,
            ".o_control_panel [data-mode='line']",
            "graph buttons are no longer in control panel"
        );
        await cpHelpers.switchView(target, "graph");
        await legacyExtraNextTick();
        assert.hasClass(
            $(target).find(".o_control_panel [data-mode='line']")[0],
            "active",
            "line chart button is still active"
        );
    });

    QUnit.test("can't restore previous action if form is invalid", async function (assert) {
        serverData.models.partner.fields.foo.required = true;

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");

        await click(target.querySelector(".o_list_button_add"));
        assert.containsOnce(target, ".o_form_view");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_required_modifier");

        await editInput(target, ".o_field_widget[name=display_name] input", "make record dirty");
        await click(target.querySelector(".breadcrumb .o_back_button"));
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_notification_manager .o_notification");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_invalid");
    });

    QUnit.test("view switcher is properly highlighted in graph view", async function (assert) {
        assert.expect(4);
        registry.category("services").add("cookie", fakeCookieService);
        serverData.actions[3].views.splice(1, 1, [false, "graph"]);
        serverData.views["partner,false,graph"] = "<graph/>";
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.hasClass(
            $(target).find(".o_control_panel .o_switch_view.o_list")[0],
            "active",
            "list button in control panel is active"
        );
        assert.doesNotHaveClass(
            $(target).find(".o_control_panel .o_switch_view.o_graph")[0],
            "active",
            "graph button in control panel is not active"
        );
        // switch to graph view
        await cpHelpers.switchView(target, "graph");
        await legacyExtraNextTick();
        assert.doesNotHaveClass(
            $(target).find(".o_control_panel .o_switch_view.o_list")[0],
            "active",
            "list button in control panel is not active"
        );
        assert.hasClass(
            $(target).find(".o_control_panel .o_switch_view.o_graph")[0],
            "active",
            "graph button in control panel is active"
        );
    });

    QUnit.test("can interact with search view", async function (assert) {
        assert.expect(2);
        serverData.views["partner,false,search"] = `
      <search>
        <group>
          <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
        </group>
      </search>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.doesNotHaveClass(
            $(target).find(".o_list_table")[0],
            "o_list_table_grouped",
            "list view is not grouped"
        );
        // open group by dropdown
        await cpHelpers.toggleGroupByMenu(target);
        // click on foo link
        await cpHelpers.toggleMenuItem(target, "foo");
        await legacyExtraNextTick();
        assert.hasClass(
            $(target).find(".o_list_table")[0],
            "o_list_table_grouped",
            "list view is now grouped"
        );
    });

    QUnit.test("can open a many2one external window", async function (assert) {
        serverData.models.partner.records[0].bar = 2;
        serverData.views["partner,false,search"] = `
            <search>
                <group>
                    <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
                </group>
            </search>`;
        serverData.views["partner,false,form"] = `
            <form>
                <field name="foo"/>
                <field name="bar" open_target="new"/>
            </form>`;
        const mockRPC = async (route, args) => {
            assert.step(route);
            if (args && args.method === "get_formview_id") {
                return Promise.resolve(false);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        // open first record in form view
        await testUtils.dom.click(target.querySelector(".o_data_row .o_data_cell"));
        // click on external button for m2o
        await testUtils.dom.click(target.querySelector(".o_external_button"));
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/web_search_read",
            "/web/dataset/call_kw/partner/read",
            "/web/dataset/call_kw/partner/get_formview_id",
            "/web/dataset/call_kw/partner/get_views",
            "/web/dataset/call_kw/partner/read",
        ]);
    });

    QUnit.test('save when leaving a "dirty" view', async function (assert) {
        assert.expect(4);
        const mockRPC = async (route, { args, method, model }) => {
            if (model === "partner" && method === "write") {
                assert.deepEqual(args, [[1], { foo: "pinkypie" }]);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 4);
        // open record in form view
        await click(target.querySelector(".o_kanban_record"));
        await editInput(target, '.o_field_widget[name="foo"] input', "pinkypie");
        // go back to kanban view
        await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
        assert.containsNone(document.body, ".modal", "should not display a modal dialog");
        assert.containsNone(target, ".o_form_view", "should no longer be in form view");
        assert.containsOnce(target, ".o_kanban_view", "should be in kanban view");
    });

    QUnit.test("limit set in action is passed to each created controller", async function (assert) {
        assert.expect(2);
        serverData.actions[3].limit = 2;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsN(target, ".o_data_row", 2);
        // switch to kanban view
        await cpHelpers.switchView(target, "kanban");
        await legacyExtraNextTick();
        assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 2);
    });

    QUnit.test("go back to a previous action using the breadcrumbs", async function (assert) {
        assert.expect(10);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        // open a record in form view
        await click(target.querySelector(".o_list_view .o_data_cell"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        // push another action on top of the first one, and come back to the form view
        await doAction(webClient, 4);
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            3,
            "there should be three controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "Partners Action 4",
            "breadcrumbs should contain the name of the current action"
        );
        // go back using the breadcrumbs
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a:nth(1)"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "First record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        // push again the other action on top of the first one, and come back to the list view
        await doAction(webClient, 4);
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            3,
            "there should be three controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "Partners Action 4",
            "breadcrumbs should contain the name of the current action"
        );
        // go back using the breadcrumbs
        await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a:first"));
        await legacyExtraNextTick();
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            1,
            "there should be one controller in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "Partners",
            "breadcrumbs should contain the name of the current action"
        );
    });

    QUnit.test(
        "form views are restored in edit when coming back in breadcrumbs",
        async function (assert) {
            assert.expect(2);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 3);
            // open a record in form view
            await click(target.querySelector(".o_list_view .o_data_cell"));
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            // do some other action
            await doAction(webClient, 4);
            // go back to form view
            await click(target.querySelectorAll(".o_control_panel .breadcrumb a")[1]);
            await legacyExtraNextTick();
            assert.containsOnce(target, ".o_form_view .o_form_editable");
        }
    );

    QUnit.test(
        "form views are restored with the correct id in its url when coming back in breadcrumbs",
        async function (assert) {
            assert.expect(3);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 3);
            // open a record in form view
            await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));
            await nextTick(); // wait for the router to update its state
            assert.strictEqual(webClient.env.services.router.current.hash.id, 1);
            // do some other action
            await doAction(webClient, 4);
            await nextTick(); // wait for the router to update its state
            assert.notOk(webClient.env.services.router.current.hash.id);
            // go back to form view
            await click(target.querySelectorAll(".o_control_panel .breadcrumb a")[1]);
            await nextTick(); // wait for the router to update its state
            assert.strictEqual(webClient.env.services.router.current.hash.id, 1);
        }
    );

    QUnit.test("honor group_by specified in actions context", async function (assert) {
        assert.expect(5);
        serverData.actions[3].context = "{'group_by': 'bar'}";
        serverData.views["partner,false,search"] = `
      <search>
        <group>
          <filter name="foo" string="foo" context="{'group_by': 'foo'}"/>
        </group>
      </search>`;
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_table_grouped", "should be grouped");
        assert.containsN(
            target,
            ".o_group_header",
            2,
            "should be grouped by 'bar' (two groups) at first load"
        );
        // groupby 'bar' using the searchview
        await click(target.querySelectorAll(".o_control_panel .o_cp_bottom_right button")[1]);
        await click(target.querySelector(".o_control_panel .o_group_by_menu .o_menu_item"));
        assert.containsN(target, ".o_group_header", 5, "should be grouped by 'foo' (five groups)");
        // remove the groupby in the searchview
        await click(target.querySelector(".o_control_panel .o_searchview .o_facet_remove"));
        assert.containsOnce(target, ".o_list_table_grouped", "should still be grouped");
        assert.containsN(
            target,
            ".o_group_header",
            2,
            "should be grouped by 'bar' (two groups) at reload"
        );
    });

    QUnit.test("switch request to unknown view type", async function (assert) {
        assert.expect(8);
        serverData.actions[33] = {
            id: 33,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [1, "kanban"],
            ],
        };
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 33);
        assert.containsOnce(target, ".o_list_view", "should display the list view");
        // try to open a record in a form view
        testUtils.dom.click($(target).find(".o_list_view .o_data_row:first"));
        await legacyExtraNextTick();
        assert.containsOnce(target, ".o_list_view", "should still display the list view");
        assert.containsNone(target, ".o_form_view", "should not display the form view");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
        ]);
    });

    QUnit.test("execute action with unknown view type", async function (assert) {
        serverData.views["partner,false,unknown"] = "<unknown/>";
        serverData.actions[33] = {
            id: 33,
            name: "Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "unknown"], // typically, an enterprise-only view on a community db
                [false, "kanban"],
                [false, "form"],
            ],
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 33);
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_cp_switch_buttons button", 2);
    });

    QUnit.test("flags field of ir.actions.act_window is used", async function (assert) {
        // more info about flags field : https://github.com/odoo/odoo/commit/c9b133813b250e89f1f61816b0eabfb9bee2009d
        assert.expect(6);
        serverData.actions[44] = {
            id: 33,
            name: "Partners",
            res_id: 1,
            res_model: "partner",
            type: "ir.actions.act_window",
            flags: {
                mode: "edit",
            },
            views: [[false, "form"]],
        };
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 44);
        assert.containsOnce(
            target,
            ".o_form_view .o_form_editable",
            "should display the form view in edit mode"
        ); // provided that the default mode is readonly

        assert.verifySteps(["/web/webclient/load_menus", "/web/action/load", "get_views", "read"]);
    });

    QUnit.test("save current search", async function (assert) {
        assert.expect(4);

        serverData.actions[33] = {
            id: 33,
            context: {
                shouldNotBeInFilterContext: false,
            },
            name: "Partners",
            res_model: "partner",
            search_view_id: [4, "a custom search view"],
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        };
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        patchWithCleanup(listView.Controller.prototype, {
            setup() {
                this._super(...arguments);
                useSetupAction({
                    getContext: () => ({ shouldBeInFilterContext: true }),
                });
            },
        });

        const mockRPC = async (route, args) => {
            if (args.method === "create_or_replace") {
                assert.strictEqual(args.args[0].domain, `[("bar", "=", 1)]`);
                assert.deepEqual(args.args[0].context, {
                    group_by: [],
                    shouldBeInFilterContext: true,
                });
                return 3; // fake filter id
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 33);
        assert.containsN(target, ".o_data_row", 5, "should contain 5 records");
        // filter on bar
        await cpHelpers.toggleFilterMenu(target);
        await cpHelpers.toggleMenuItem(target, "Bar");
        assert.containsN(target, ".o_data_row", 2);
        // save filter
        await cpHelpers.toggleFavoriteMenu(target);
        await cpHelpers.toggleSaveFavorite(target);
        await cpHelpers.editFavoriteName(target, "some name");
        await cpHelpers.saveFavorite(target);
    });

    QUnit.test(
        "list with default_order and favorite filter with no orderedBy",
        async function (assert) {
            serverData.views["partner,1,list"] =
                '<tree default_order="foo desc"><field name="foo"/></tree>';
            serverData.actions[100] = {
                id: 100,
                name: "Partners",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [1, "list"],
                    [false, "form"],
                ],
            };
            serverData.models.partner.filters = [
                {
                    name: "favorite filter",
                    id: 5,
                    context: "{}",
                    sort: "[]",
                    domain: '[("bar", "=", 1)]',
                    is_default: false,
                },
            ];
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 100);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell")),
                ["zoup", "yop", "plop", "gnap", "blip"],
                "record should be in descending order as default_order applies"
            );

            await cpHelpers.toggleFavoriteMenu(target);
            await cpHelpers.toggleMenuItem(target, "favorite filter");
            assert.strictEqual(
                target.querySelector(".o_control_panel .o_facet_values").innerText.trim(),
                "favorite filter",
                "favorite filter should be applied"
            );
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell")),
                ["gnap", "blip"],
                "record should still be in descending order after default_order applied"
            );

            // go to formview and come back to listview
            await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));
            await testUtils.dom.click(target.querySelector(".o_control_panel .breadcrumb a"));
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell")),
                ["gnap", "blip"],
                "order of records should not be changed, while coming back through breadcrumb"
            );

            // remove filter
            await cpHelpers.removeFacet(target, 0);
            assert.deepEqual(
                getNodesTextContent(target.querySelectorAll(".o_data_row .o_data_cell")),
                ["zoup", "yop", "plop", "gnap", "blip"],
                "order of records should not be changed, after removing current filter"
            );
        }
    );

    QUnit.test("action with default favorite and context.active_id", async function (assert) {
        assert.expect(4);

        serverData.actions[3].context = { active_id: 4, active_ids: [4], active_model: "whatever" };
        serverData.models.partner.filters = [
            {
                name: "favorite filter",
                id: 5,
                context: "{}",
                sort: "[]",
                domain: '[("bar", "=", 1)]',
                is_default: true,
            },
        ];
        const mockRPC = (route, args) => {
            if (args.method === "web_search_read") {
                assert.deepEqual(args.kwargs.domain, [["bar", "=", 1]]);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);

        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_searchview .o_searchview_facet");
        assert.strictEqual(target.querySelector(".o_facet_value").innerText, "favorite filter");
    });

    QUnit.test(
        "search menus are still available when switching between actions",
        async function (assert) {
            assert.expect(3);
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);
            assert.isVisible(
                target.querySelector(".o_search_options .dropdown.o_filter_menu"),
                "the search options should be available"
            );
            await doAction(webClient, 3);
            assert.isVisible(
                target.querySelector(".o_search_options .dropdown.o_filter_menu"),
                "the search options should be available"
            );
            // go back using the breadcrumbs
            await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb a:first"));
            await legacyExtraNextTick();
            assert.isVisible(
                target.querySelector(".o_search_options .dropdown.o_filter_menu"),
                "the search options should be available"
            );
        }
    );

    QUnit.test(
        "current act_window action is stored in session_storage if possible",
        async function (assert) {
            let expectedAction;
            patchWithCleanup(browser, {
                sessionStorage: Object.assign(Object.create(sessionStorage), {
                    setItem(k, value) {
                        assert.deepEqual(JSON.parse(value), expectedAction);
                    },
                }),
            });
            const webClient = await createWebClient({ serverData });

            // execute an action that can be stringified -> should be stored
            expectedAction = serverData.actions[3];
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");

            // execute an action that can't be stringified -> should not crash
            expectedAction = {};
            const x = {};
            x.y = x;
            await doAction(webClient, {
                type: "ir.actions.act_window",
                res_model: "partner",
                views: [[false, "kanban"]],
                flags: { x },
            });
            assert.containsOnce(target, ".o_kanban_view");
        }
    );

    QUnit.test("destroy action with lazy loaded controller", async function (assert) {
        assert.expect(6);
        const webClient = await createWebClient({ serverData });
        await loadState(webClient, {
            action: 3,
            id: 2,
            view_type: "form",
        });
        assert.containsNone(target, ".o_list_view");
        assert.containsOnce(target, ".o_form_view");
        assert.containsN(
            target,
            ".o_control_panel .breadcrumb-item",
            2,
            "there should be two controllers in the breadcrumbs"
        );
        assert.strictEqual(
            $(target).find(".o_control_panel .breadcrumb-item:last").text(),
            "Second record",
            "breadcrumbs should contain the display_name of the opened record"
        );
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.containsNone(target, ".o_form_view");
        assert.containsOnce(target, ".o_kanban_view");
    });

    QUnit.test("execute action from dirty, new record, and come back", async function (assert) {
        serverData.models.partner.fields.bar.default = 1;
        serverData.views["partner,false,form"] = `
            <form>
                <field name="display_name"/>
                <field name="foo"/>
                <field name="bar" readonly="1"/>
            </form>`;
        const mockRPC = async (route, args) => {
            assert.step((args && args.method) || route);
            if (args && args.method === "get_formview_action") {
                return Promise.resolve({
                    res_id: 1,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                });
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });

        // execute an action and create a new record
        await doAction(webClient, 3);
        await click(target.querySelector(".o_list_button_add"));
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.containsOnce(target, ".o_form_uri:contains(First record)");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_control_panel .breadcrumb-item")),
            ["Partners", "New"]
        );

        // set form view dirty and open m2o record
        await editInput(target, '.o_field_widget[name="display_name"] input', "test");
        await editInput(target, ".o_field_widget[name=foo] input", "val");
        await click(target.querySelector(".o_form_uri"));
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_control_panel .breadcrumb-item")),
            ["Partners", "test", "First record"]
        );
        // go back to test using the breadcrumbs
        await testUtils.dom.click(
            target.querySelectorAll(".o_control_panel .breadcrumb-item a")[1]
        );
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_control_panel .breadcrumb-item")),
            ["Partners", "test"]
        );
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "web_search_read",
            "onchange",
            "get_formview_action",
            "create", // FIXME: to check with mcm
            "get_views",
            "read",
            "read",
        ]);
    });

    QUnit.test("execute a contextual action from a form view", async function (assert) {
        assert.expect(4);
        const contextualAction = serverData.actions[8];
        contextualAction.context = "{}"; // need a context to evaluate
        serverData.models.partner.toolbar = {
            action: [contextualAction],
            print: [],
        };
        const mockRPC = async (route, args) => {
            if (args && args.method === "get_views" && args.model === "partner") {
                assert.strictEqual(
                    args.kwargs.options.toolbar,
                    true,
                    "should ask for toolbar information"
                );
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        // execute an action and open a record
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
        // execute the custom action from the action menu
        await cpHelpers.toggleActionMenu(target);
        await cpHelpers.toggleMenuItem(target, "Favorite Ponies");
        assert.containsOnce(target, ".o_list_view");
    });

    QUnit.test(
        "go back to action with form view as main view, and res_id",
        async function (assert) {
            serverData.actions[999] = {
                id: 999,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                res_id: 2,
                views: [[44, "form"]],
            };
            serverData.views["partner,44,form"] =
                '<form><field name="m2o" open_target="current"/></form>';
            const mockRPC = async (route, args) => {
                if (args.method === "get_formview_action") {
                    return Promise.resolve({
                        res_id: 3,
                        res_model: "partner",
                        type: "ir.actions.act_window",
                        views: [[false, "form"]],
                    });
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 999);
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            assert.strictEqual(
                target.querySelector(".o_control_panel .breadcrumb").textContent,
                "Second record"
            );
            // push another action in the breadcrumb
            await click(target, ".o_field_many2one .o_external_button");
            assert.strictEqual(
                target.querySelector(".o_control_panel .breadcrumb").textContent,
                "Second recordThird record"
            );
            // go back to the form view
            await click(target.querySelector(".o_control_panel .breadcrumb a"));
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            assert.strictEqual(
                target.querySelector(".o_control_panel .breadcrumb-item").textContent,
                "Second record"
            );
        }
    );

    QUnit.test("open a record, come back, and create a new record", async function (assert) {
        assert.expect(7);
        const webClient = await createWebClient({ serverData });
        // execute an action and open a record
        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_list_view .o_data_row", 5);
        await click(target.querySelector(".o_list_view .o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_view .o_form_editable");
        // go back using the breadcrumbs
        await click(target.querySelector(".o_control_panel .breadcrumb-item a"));
        assert.containsOnce(target, ".o_list_view");
        // create a new record
        await click(target.querySelector(".o_list_button_add"));
        assert.containsOnce(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_view .o_form_editable");
    });

    QUnit.test(
        "open form view, use the pager, execute action, and come back",
        async function (assert) {
            assert.expect(8);
            const webClient = await createWebClient({ serverData });
            // execute an action and open a record
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");
            assert.containsN(target, ".o_list_view .o_data_row", 5);
            await click(target.querySelector(".o_list_view .o_data_cell"));
            assert.containsOnce(target, ".o_form_view");
            assert.strictEqual(
                $(target).find(".o_field_widget[name=display_name] input").val(),
                "First record"
            );
            // switch to second record
            await click(target.querySelector(".o_pager_next"));
            assert.strictEqual(
                $(target).find(".o_field_widget[name=display_name] input").val(),
                "Second record"
            );
            // execute an action from the second record
            await testUtils.dom.click($(target).find(".o_statusbar_buttons button[name=4]"));
            assert.containsOnce(target, ".o_kanban_view");
            // go back using the breadcrumbs
            await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb-item:nth(1) a"));
            assert.containsOnce(target, ".o_form_view");
            assert.strictEqual(
                $(target).find(".o_field_widget[name=display_name] input").val(),
                "Second record"
            );
        }
    );

    QUnit.test(
        "create a new record in a form view, execute action, and come back",
        async function (assert) {
            assert.expect(8);
            const webClient = await createWebClient({ serverData });
            // execute an action and create a new record
            await doAction(webClient, 3);
            assert.containsOnce(target, ".o_list_view");
            await click(target.querySelector(".o_list_button_add"));
            assert.containsOnce(target, ".o_form_view");
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            await editInput(target, ".o_field_widget[name=display_name] input", "another record");
            await click(target.querySelector(".o_form_button_save"));
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            // execute an action from the second record
            await testUtils.dom.click($(target).find(".o_statusbar_buttons button[name=4]"));
            assert.containsOnce(target, ".o_kanban_view");
            // go back using the breadcrumbs
            await testUtils.dom.click($(target).find(".o_control_panel .breadcrumb-item:nth(1) a"));
            assert.containsOnce(target, ".o_form_view");
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            assert.strictEqual(
                $(target).find(".o_field_widget[name=display_name] input").val(),
                "another record"
            );
        }
    );

    QUnit.test("onClose should be called only once with right parameters", async function (assert) {
        assert.expect(5);
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 24); // main form view
        await doAction(webClient, 25, {
            // form view in target new
            onClose(infos) {
                assert.step("onClose");
                assert.deepEqual(infos, { cantaloupe: "island" });
            },
        });
        assert.containsOnce(target, ".modal");
        await doAction(webClient, {
            type: "ir.actions.act_window_close",
            infos: { cantaloupe: "island" },
        });
        assert.verifySteps(["onClose"]);
        assert.containsNone(target, ".modal");
    });

    QUnit.test("search view should keep focus during do_search", async function (assert) {
        assert.expect(5);
        // One should be able to type something in the search view, press on enter to
        // make the facet and trigger the search, then do this process
        // over and over again seamlessly.
        // Verifying the input's value is a lot trickier than verifying the search_read
        // because of how native events are handled in tests
        const searchPromise = testUtils.makeTestPromise();
        const mockRPC = async (route, args) => {
            if (args.method === "web_search_read") {
                assert.step("search_read " + args.kwargs.domain);
                if (JSON.stringify(args.domain) === JSON.stringify([["foo", "ilike", "m"]])) {
                    await searchPromise;
                }
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        await cpHelpers.editSearch(target, "m");
        await cpHelpers.validateSearch(target);
        assert.verifySteps(["search_read ", "search_read foo,ilike,m"]);
        // Triggering the do_search above will kill the current searchview Input
        await cpHelpers.editSearch(target, "o");
        // We have something in the input of the search view. Making the search_read
        // return at this point will trigger the redraw of the view.
        // However we want to hold on to what we just typed
        searchPromise.resolve();
        await cpHelpers.validateSearch(target);
        assert.verifySteps(["search_read |,foo,ilike,m,foo,ilike,o"]);
    });

    QUnit.test(
        "Call twice clearUncommittedChanges in a row does not save twice",
        async function (assert) {
            assert.expect(4);
            let writeCalls = 0;
            const mockRPC = async (route, { method }) => {
                if (method === "write") {
                    writeCalls += 1;
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            // execute an action and edit existing record
            await doAction(webClient, 3);
            await click(target.querySelector(".o_list_view .o_data_cell"));
            assert.containsOnce(target, ".o_form_view .o_form_editable");
            await editInput(target, ".o_field_widget[name=foo] input", "val");
            clearUncommittedChanges(webClient.env);
            await nextTick();
            assert.containsNone(document.body, ".modal");
            clearUncommittedChanges(webClient.env);
            await nextTick();
            assert.containsNone(document.body, ".modal");
            assert.strictEqual(writeCalls, 1);
        }
    );

    QUnit.test(
        "executing a window action with onchange warning does not hide it",
        async function (assert) {
            serverData.views["partner,false,form"] = `<form><field name="foo"/></form>`;
            const mockRPC = (route, args) => {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: {},
                        warning: {
                            title: "Warning",
                            message: "Everything is alright",
                            type: "dialog",
                        },
                    });
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });

            await doAction(webClient, 3);

            await click(target.querySelector(".o_list_button_add"));
            assert.containsOnce(
                document.body,
                ".modal.o_technical_modal",
                "Warning modal should be opened"
            );

            await click(document.querySelector(".modal.o_technical_modal button.btn-close"));
            assert.containsNone(
                document.body,
                ".modal.o_technical_modal",
                "Warning modal should be closed"
            );
        }
    );

    QUnit.test(
        "do not call clearUncommittedChanges() when target=new and dialog is opened",
        async function (assert) {
            const webClient = await createWebClient({ serverData });
            // Open Partner form view and enter some text
            await doAction(webClient, 3, { viewType: "form" });
            assert.containsOnce(target, ".o_action_manager .o_form_view .o_form_editable");
            await editInput(target, ".o_field_widget[name=display_name] input", "TEST");
            // Open dialog without saving should not ask to discard
            await doAction(webClient, 5);
            assert.containsOnce(target, ".o_action_manager .o_form_view .o_form_editable");
            assert.containsOnce(target, ".o_dialog .o_view_controller");
        }
    );

    QUnit.test("do not pushState when target=new and dialog is opened", async function (assert) {
        const webClient = await createWebClient({ serverData });
        // Open Partner form in create mode
        await doAction(webClient, 3, { viewType: "form" });
        const prevHash = Object.assign({}, webClient.env.services.router.current.hash);
        // Edit another partner in a dialog
        await doAction(webClient, {
            name: "Edit a Partner",
            res_model: "partner",
            res_id: 3,
            type: "ir.actions.act_window",
            views: [[3, "form"]],
            target: "new",
            view_mode: "form",
        });
        assert.deepEqual(
            webClient.env.services.router.current.hash,
            prevHash,
            "push_state in dialog shouldn't change the hash"
        );
    });

    QUnit.test("do not restore after action button clicked", async function (assert) {
        assert.expect(4);
        const mockRPC = async (route, args) => {
            if (route === "/web/dataset/call_button" && args.method === "do_something") {
                return true;
            }
        };
        serverData.views["partner,false,form"] = `
      <form>
        <header><button name="do_something" string="Call button" type="object"/></header>
        <sheet>
          <field name="display_name"/>
        </sheet>
      </form>`;
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3, { viewType: "form", props: { resId: 1 } });
        await legacyExtraNextTick();
        await editInput(target, "div[name='display_name'] input", "Edited value");
        assert.isVisible(target.querySelector(".o_form_button_save"));
        assert.isVisible(target.querySelector(".o_statusbar_buttons button[name=do_something]"));
        await click(target.querySelector(".o_statusbar_buttons button[name=do_something]"));
        await legacyExtraNextTick();
        assert.isVisible(target.querySelector(".o_form_button_save"));
        await click(target.querySelector(".o_form_button_save"));
        await legacyExtraNextTick();
        assert.isNotVisible(target.querySelector(".o_form_buttons_view .o_form_button_save"));
    });

    QUnit.test("debugManager is active for (legacy) views", async function (assert) {
        assert.expect(2);

        registry.category("debug").category("view").add("editView", editView);
        patchWithCleanup(odoo, { debug: "1" });
        const mockRPC = async (route) => {
            if (route.includes("check_access_rights")) {
                return true;
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsNone(
            target,
            ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
        );
        await click(target.querySelector(".o_debug_manager .dropdown-toggle"));
        assert.containsOnce(
            target,
            ".o_debug_manager .dropdown-item:contains('Edit View: Kanban')"
        );
    });

    QUnit.test("reload a view via the view switcher keep state", async function (assert) {
        assert.expect(6);
        serverData.actions[3].views.unshift([false, "pivot"]);
        serverData.views["partner,false,pivot"] = "<pivot/>";
        const mockRPC = async (route, args) => {
            if (args.method === "read_group") {
                assert.step(args.method);
            }
        };

        registry.category("services").add("user", makeFakeUserService());
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 3);
        assert.doesNotHaveClass(
            target.querySelector(".o_pivot_measure_row"),
            "o_pivot_sort_order_asc"
        );
        await click(target.querySelector(".o_pivot_measure_row"));
        assert.hasClass(target.querySelector(".o_pivot_measure_row"), "o_pivot_sort_order_asc");
        await cpHelpers.switchView(target, "pivot");
        await legacyExtraNextTick();
        assert.hasClass(target.querySelector(".o_pivot_measure_row"), "o_pivot_sort_order_asc");
        assert.verifySteps([
            "read_group", // initial read_group
            "read_group", // read_group at reload after switch view
        ]);
    });

    QUnit.test("doAction supports being passed globalState prop", async function (assert) {
        assert.expect(1);
        const searchModel = JSON.stringify({
            nextGroupId: 2,
            nextGroupNumber: 2,
            nextId: 2,
            searchItems: {
                1: {
                    description: `ID is "99"`,
                    domain: `[("id","=",99)]`,
                    type: "filter",
                    groupId: 1,
                    groupNumber: 1,
                    id: 1,
                },
            },
            query: [{ searchItemId: 1 }],
            sections: [],
        });
        const mockRPC = async (route, args) => {
            if (args.method === "web_search_read") {
                assert.deepEqual(args.kwargs.domain, [["id", "=", 99]]);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1, {
            props: {
                globalState: { searchModel },
            },
        });
    });

    QUnit.test("window action in target new fails (onchange)", async (assert) => {
        /*
         * By-pass QUnit's and test's error handling because the error service needs to be active
         */
        const handler = (ev) => {
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => window.removeEventListener("unhandledrejection", handler));

        patchWithCleanup(QUnit, {
            onUnhandledRejection: () => {},
        });

        const originOnunhandledrejection = window.onunhandledrejection;
        window.onunhandledrejection = () => {};
        registerCleanup(() => {
            window.onunhandledrejection = originOnunhandledrejection;
        });
        /*
         * End By pass error handling
         */

        const warningOpened = makeDeferred();
        class WarningDialogWait extends WarningDialog {
            setup() {
                super.setup();
                onMounted(() => warningOpened.resolve());
            }
        }

        serviceRegistry.add("error", errorService);
        registry
            .category("error_dialogs")
            .add("odoo.exceptions.ValidationError", WarningDialogWait);

        const mockRPC = (route, args) => {
            if (args.method === "onchange" && args.model === "partner") {
                const error = new RPCError();
                error.exceptionName = "odoo.exceptions.ValidationError";
                error.code = 200;
                return Promise.reject(error);
            }
        };

        serverData.views["partner,666,form"] = /*xml*/ `
            <form>
                <header>
                    <button name="5" type="action"/>
                </header>
                <field name="display_name"/>
            </form>`;

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 24);
        await click(target, ".o_form_view button[name='5']");

        await warningOpened;
        assert.containsOnce(target, ".modal");
        assert.containsOnce(target, ".modal .o_dialog_warning");
        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent,
            "Validation Error"
        );
    });

    QUnit.test("action and get_views rpcs are cached", async function (assert) {
        const mockRPC = async (route, args) => {
            assert.step(args.method || route);
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        assert.verifySteps(["/web/webclient/load_menus"]);

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");
        assert.verifySteps(["/web/action/load", "get_views", "web_search_read"]);

        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_kanban_view");

        assert.verifySteps(["web_search_read"]);
    });

    QUnit.test("pushState also changes the title of the tab", async (assert) => {
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3); // list view
        const titleService = webClient.env.services.title;
        assert.strictEqual(titleService.current, '{"zopenerp":"Odoo","action":"Partners"}');
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(titleService.current, '{"zopenerp":"Odoo","action":"First record"}');
        await click(target.querySelector(".o_pager_next"));
        assert.strictEqual(titleService.current, '{"zopenerp":"Odoo","action":"Second record"}');
    });

    QUnit.test("action part of title is updated when an action is mounted", async (assert) => {
        // use a PivotView because we need a view converted to wowl
        // those two lines can be removed once the list view is converted to wowl
        serverData.actions[3].views.unshift([false, "pivot"]);
        serverData.views["partner,false,pivot"] = "<pivot/>";
        serviceRegistry.add("user", makeFakeUserService());

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 3);
        const titleService = webClient.env.services.title;
        assert.strictEqual(titleService.current, '{"zopenerp":"Odoo","action":"Partners"}');
    });

    QUnit.test("action group_by of type string", async function (assert) {
        assert.expect(2);
        serverData.views["partner,false,pivot"] = `<pivot/>`;
        registry.category("services").add("user", makeFakeUserService());
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[3, "pivot"]],
            context: { group_by: "foo" },
        });
        assert.containsOnce(target, ".o_pivot_view");
        assert.containsN(target, ".o_pivot_view tbody th", 6);
    });

    QUnit.test("action help given to View in props if not empty", async function (assert) {
        serverData.models.partner.records = [];
        const action = serverData.actions[3];
        serverData.actions[3] = {
            ...action,
            help: '<p class="hello">Hello</p>',
        };
        serverData.actions[4] = {
            ...action,
            id: 4,
            help: '<p class="hello"></p>',
        };

        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 3);
        assert.containsOnce(target, ".o_list_view");
        assert.containsOnce(target, ".o_view_nocontent");
        assert.strictEqual(target.querySelector(".o_view_nocontent").innerText, "Hello");
        assert.containsNone(target, "table");

        await doAction(webClient, 4);
        assert.containsOnce(target, ".o_list_view");
        assert.containsNone(target, ".o_view_nocontent");
        assert.containsOnce(target, "table");
    });

    QUnit.test("process context.form_view_initial_mode", async function (assert) {
        serverData.views = {
            "partner,false,form": `<form><field name="name"/></form>`,
            "partner,false,search": `<search/>`,
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "current",
            res_model: "partner",
            views: [[false, "form"]],
            context: {
                form_view_initial_mode: "edit",
            },
        });

        assert.containsOnce(target, ".o_form_view .o_form_editable");
    });

    QUnit.test("process context.form_view_initial_mode (2)", async function (assert) {
        serverData.views = {
            "partner,false,form": `<form><field name="name"/></form>`,
            "partner,false,search": `<search/>`,
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "new",
            res_model: "partner",
            views: [[false, "form"]],
            context: {
                form_view_initial_mode: "readonly",
            },
        });

        // mode is "edit" because target="new"
        assert.containsOnce(target, ".o_form_view .o_form_editable");
    });

    QUnit.test("load a tree", async function (assert) {
        serverData.views = {
            "partner,false,list": `<list><field name="name"/></list>`,
            "partner,false,search": `<search/>`,
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "current",
            res_model: "partner",
            views: [[false, "tree"]],
        });
        assert.containsOnce(target, ".o_list_view");
    });
});
