/** @odoo-module */
import {
    openStudio,
    registerStudioDependencies,
    fillActionFieldsDefaults,
} from "@web_studio/../tests/helpers";
import { doAction as _doAction } from "@web/../tests/webclient/helpers";
import {
    getFixture,
    click,
    selectDropdownItem,
    makeDeferred,
    editInput,
    nextTick,
} from "@web/../tests/helpers/utils";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";

function doAction(env, action, options) {
    if (typeof action === "object") {
        action = fillActionFieldsDefaults(action);
    }
    return _doAction(env, action, options);
}

QUnit.module("ActionEditor", (hooks) => {
    let serverData;
    let target;
    hooks.beforeEach(() => {
        const models = {
            kikou: {
                fields: {
                    display_name: { type: "char", string: "Display Name" },
                    start: { type: "datetime", store: "true", string: "start date" },
                },
            },
            "res.groups": {
                fields: {
                    display_name: { string: "Display Name", type: "char" },
                },
                records: [
                    {
                        id: 4,
                        display_name: "Admin",
                    },
                ],
            },
        };

        const views = {
            "kikou,1,list": `<tree><field name="display_name" /></tree>`,
            "kikou,2,form": `<form><field name="display_name" /></form>`,
            "kikou,false,search": `<search />`,
        };
        serverData = { models, views };
        target = getFixture();
        registerStudioDependencies();
    });

    QUnit.test("add a gantt view", async function (assert) {
        assert.expect(5);

        const mockRPC = (route, args) => {
            if (route === "/web_studio/add_view_type") {
                assert.strictEqual(args.view_type, "gantt", "should add the correct view");
                return Promise.resolve(false);
            } else if (args.method === "fields_get") {
                assert.strictEqual(args.model, "kikou", "should read fields on the correct model");
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(
            webClient,
            {
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: "kikou",
                view_mode: "list",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
            },
            { clearBreadcrumbs: true }
        );
        await openStudio(target, { noEdit: true });

        await click(
            target.querySelector(
                '.o_web_studio_view_type[data-type="gantt"] .o_web_studio_thumbnail'
            )
        );
        assert.containsOnce(
            $,
            ".o_web_studio_new_view_dialog",
            "there should be an opened dialog to select gantt attributes"
        );
        assert.strictEqual(
            $('.o_web_studio_new_view_dialog select[name="date_start"]').val(),
            "start",
            "date start should be prefilled (mandatory)"
        );
        assert.strictEqual(
            $('.o_web_studio_new_view_dialog select[name="date_stop"]').val(),
            "start",
            "date stop should be prefilled (mandatory)"
        );
    });

    QUnit.test("create unavailable view", async function (assert) {
        assert.expect(2);

        const mockRPC = (route, args) => {
            if (route === "/web_studio/activity_allowed") {
                assert.strictEqual(args.model, "kikou", "should verify allowed view on the correct model")
                return false;
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(
            webClient,
            {
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: "kikou",
                view_mode: "list",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
            },
            { clearBreadcrumbs: true }
        );
        await openStudio(target, { noEdit: true });

        await click(
            target.querySelector(
                '.o_web_studio_view_type[data-type="activity"] .o_web_studio_thumbnail'
            )
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").innerHTML,
            "Activity view unavailable on this model"
        );
    });

    QUnit.test("disable the view from studio", async function (assert) {
        assert.expect(3);

        const actions = {
            1: {
                id: 1,
                xml_id: "kikou.action",
                name: "Kikou Action",
                help: "",
                res_model: "kikou",
                type: "ir.actions.act_window",
                view_mode: "list,form",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
                groups_id: [],
            },
        };

        const views = {
            "kikou,1,list": `<tree><field name="display_name"/></tree>`,
            "kikou,1,search": `<search></search>`,
            "kikou,2,form": `<form><field name="display_name"/></form>`,
        };
        Object.assign(serverData, { actions, views });

        let loadActionStep = 0;
        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_action") {
                return true;
            } else if (route === "/web/action/load") {
                loadActionStep++;
                /**
                 * step 1: initial action/load
                 * step 2: on disabling list view
                 */
                if (loadActionStep === 2) {
                    return {
                        name: "Kikou Action",
                        help: "",
                        res_model: "kikou",
                        view_mode: "form",
                        type: "ir.actions.act_window",
                        views: [[2, "form"]],
                        id: 1,
                        groups_id: [],
                    };
                }
            }
        };

        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);
        await openStudio(target);

        await click(target.querySelector(".o_menu_sections a"));

        // make list view disable and form view only will be there in studio view
        await click(target.querySelector('div[data-type="list"] .o_web_studio_more'));
        await click(target.querySelector('div[data-type="list"] [data-action="disable_view"]'));
        // reloadAction = false;
        assert.hasClass(
            $(target).find('div[data-type="list"]'),
            "o_web_studio_inactive",
            "list view should have become inactive"
        );

        // make form view disable and it should prompt the alert dialog
        await click(target.querySelector('div[data-type="form"] .o_web_studio_more'));
        await click(target.querySelector('div[data-type="form"] [data-action="disable_view"]'));
        assert.containsOnce(
            $,
            ".o_technical_modal",
            "should display a modal when attempting to disable last view"
        );
        assert.strictEqual(
            $(".o_technical_modal .modal-body").text().trim(),
            "You cannot deactivate this view as it is the last one active.",
            "modal should tell that last view cannot be disabled"
        );
    });

    QUnit.test("add groups on action", async function (assert) {
        assert.expect(1);

        const actions = {
            1: {
                id: 1,
                name: "",
                help: "",
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: "kikou",
                view_mode: "list",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
                groups_id: [],
            },
        };
        Object.assign(serverData, { actions });

        const mockRPC = (route, args) => {
            if (route === "/web_studio/edit_action") {
                assert.deepEqual(
                    args.args.groups_id[0],
                    [4, 4],
                    "group admin should be applied on action"
                );
                return Promise.resolve(true);
            }
        };
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        await openStudio(target, { noEdit: true });

        await selectDropdownItem(target, "groups_id", "Admin");
    });

    QUnit.test("concurrency: keep user's input when editing action", async (assert) => {
        const actions = {
            1: {
                id: 1,
                name: "",
                help: "",
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: "kikou",
                view_mode: "list",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
                groups_id: [],
            },
        };
        Object.assign(serverData, { actions });

        const def = makeDeferred();
        const mockRPC = async (route, args) => {
            if (route === "/web_studio/edit_action") {
                assert.step("edit_action");
                assert.deepEqual(
                    args.args,
                    { name: "testInput" },
                    "The call to edit_action must be correct"
                );
                actions[1].name = args.args.name;
                await def;
                return Promise.resolve(true);
            }
            if (route === "/web/action/load") {
                assert.step("action_load");
            }
        };
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.verifySteps(["action_load"]);

        await openStudio(target, { noEdit: true });

        editInput(target, ".o_web_studio_sidebar_content input#name", "testInput");
        const textarea = target.querySelector(".o_web_studio_sidebar_content textarea#help");
        textarea.value = "<p>test help</p>";
        textarea.dispatchEvent(new Event("input"));
        def.resolve();
        await def;
        await nextTick();
        assert.verifySteps(["edit_action", "action_load"]);
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar_content input#name").value,
            "testInput"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar_content textarea#help").value,
            "<p>test help</p>"
        );
    });

    QUnit.test("active_id and active_ids present in context at reload", async function (assert) {
        const actions = {
            1: {
                id: 1,
                name: "",
                help: "",
                xml_id: "some.xml_id",
                type: "ir.actions.act_window",
                res_model: "kikou",
                view_mode: "list",
                views: [
                    [1, "list"],
                    [2, "form"],
                ],
                context: {
                    active_id: 90,
                    active_ids: [90, 91],
                },
                groups_id: [],
            },
        };
        Object.assign(serverData, { actions });

        const mockRPC = (route, args) => {
            if (route === "/web/action/load") {
                assert.step(`action load: ${JSON.stringify(args)}`);
            }
            if (route === "/web_studio/edit_action") {
                assert.step("edit_action");
                return Promise.resolve(true);
            }
        };
        const webClient = await createEnterpriseWebClient({ serverData, mockRPC });
        await doAction(webClient, 1, { clearBreadcrumbs: true });
        assert.verifySteps([`action load: {"action_id":1,"additional_context":{}}`]);
        await openStudio(target, { noEdit: true });

        await editInput(target, ".o_web_studio_sidebar #name", "new name");
        assert.verifySteps([
            "edit_action",
            `action load: {"action_id":1,"additional_context":{"active_id":90,"active_ids":[90,91]}}`,
        ]);
    });
});
