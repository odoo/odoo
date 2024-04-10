import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryAllTexts, queryText } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, onMounted, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    getService,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    stepAllNetworkCalls,
    webModels,
} from "@web/../tests/web_test_helpers";

import { ClientErrorDialog } from "@web/core/errors/error_dialogs";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";

const { ResCompany, ResPartner, ResUsers } = webModels;

class Partner extends models.Model {
    _rec_name = "display_name";

    _records = [
        { id: 1, display_name: "First record" },
        { id: 2, display_name: "Second record" },
    ];
    _views = {
        "form,false": `
            <form>
                <header>
                    <button name="object" string="Call method" type="object"/>
                    <button name="4" string="Execute action" type="action"/>
                </header>
                <group>
                    <field name="display_name"/>
                </group>
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div class="oe_kanban_global_click">
                            <field name="display_name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<tree><field name="display_name"/></tree>`,
        "list,2": `<tree limit="3"><field name="display_name"/></tree>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner, ResCompany, ResPartner, ResUsers]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
    {
        id: 4,
        xml_id: "action_4",
        name: "Partners Action 4",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [1, "kanban"],
            [2, "list"],
            [false, "form"],
        ],
    },
    {
        id: 5,
        xml_id: "action_5",
        name: "Create a Partner",
        res_model: "partner",
        target: "new",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    },
    {
        id: 15,
        name: "Partners Action Fullscreen",
        res_model: "partner",
        target: "fullscreen",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
]);

describe("new", () => {
    test('can execute act_window actions in target="new"', async () => {
        stepAllNetworkCalls();

        await mountWithCleanup(WebClient);
        await getService("action").doAction(5);
        expect(".o_technical_modal .o_form_view").toHaveCount(1, {
            message: "should have rendered a form view in a modal",
        });
        expect(".o_technical_modal .modal-body").toHaveClass("o_act_window", {
            message: "dialog main element should have classname 'o_act_window'",
        });
        expect(".o_technical_modal .o_form_view .o_form_editable").toHaveCount(1, {
            message: "form view should be in edit mode",
        });
        expect([
            "/web/webclient/translations",
            "/web/webclient/load_menus",
            "/web/action/load",
            "get_views",
            "onchange",
        ]).toVerifySteps();
    });

    test("chained action on_close", async () => {
        function onClose(closeInfo) {
            expect(closeInfo).toBe("smallCandle");
            expect.step("Close Action");
        }
        await mountWithCleanup(WebClient);
        await getService("action").doAction(5, { onClose });
        // a target=new action shouldn't activate the on_close
        await getService("action").doAction(5);
        expect([]).toVerifySteps();
        // An act_window_close should trigger the on_close
        await getService("action").doAction({
            type: "ir.actions.act_window_close",
            infos: "smallCandle",
        });
        expect(["Close Action"]).toVerifySteps();
    });

    test("footer buttons are moved to the dialog footer", async () => {
        Partner._views["form,false"] = `
            <form>
                <field name="display_name"/>
                <footer>
                    <button string="Create" type="object" class="infooter"/>
                </footer>
            </form>`;

        await mountWithCleanup(WebClient);
        await getService("action").doAction(5);
        expect(".o_technical_modal .modal-body button.infooter").toHaveCount(0, {
            message: "the button should not be in the body",
        });
        expect(".o_technical_modal .modal-footer button.infooter").toHaveCount(1, {
            message: "the button should be in the footer",
        });
        expect(".modal-footer button:not(.d-none)").toHaveCount(1, {
            message: "the modal footer should only contain one visible button",
        });
    });

    test("Button with `close` attribute closes dialog", async () => {
        Partner._views = {
            "form,false": `
                <form>
                    <header>
                        <button string="Open dialog" name="5" type="action"/>
                    </header>
                </form>`,
            "form,17": `
                <form>
                    <footer>
                        <button string="I close the dialog" name="some_method" type="object" close="1"/>
                    </footer>
                </form>`,
            "search,false": "<search></search>",
        };
        defineActions([
            {
                id: 4,
                name: "Partners Action 4",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
            {
                id: 5,
                name: "Create a Partner",
                res_model: "partner",
                target: "new",
                type: "ir.actions.act_window",
                views: [[17, "form"]],
            },
        ]);

        onRpc("/web/dataset/call_button", async (request) => {
            const { params } = await request.json();
            if (params.method === "some_method") {
                return {
                    tag: "display_notification",
                    type: "ir.actions.client",
                };
            }
        });
        stepAllNetworkCalls();

        await mountWithCleanup(WebClient);
        expect(["/web/webclient/translations", "/web/webclient/load_menus"]).toVerifySteps();
        await getService("action").doAction(4);
        expect(["/web/action/load", "get_views", "onchange"]).toVerifySteps();
        await contains(`button[name="5"]`).click();
        expect(["web_save", "/web/action/load", "get_views", "onchange"]).toVerifySteps();
        expect(".modal").toHaveCount(1);
        await contains(`button[name=some_method]`).click();
        expect(["web_save", "some_method", "web_read"]).toVerifySteps();
        expect(".modal").toHaveCount(0);
    });

    test('footer buttons are updated when having another action in target "new"', async () => {
        defineActions([
            {
                id: 25,
                name: "Create a Partner",
                res_model: "partner",
                target: "new",
                type: "ir.actions.act_window",
                views: [[3, "form"]],
            },
        ]);
        Partner._views = {
            "form,false": `
                <form>
                    <field name="display_name"/>
                    <footer>
                        <button string="Create" type="object" class="infooter"/>
                    </footer>
                </form>`,
            "form,3": `
                <form>
                    <footer>
                        <button class="btn-primary" string="Save" special="save"/>
                    </footer>
                </form>`,
        };

        await mountWithCleanup(WebClient);
        await getService("action").doAction(5);
        expect('.o_technical_modal .modal-body button[special="save"]').toHaveCount(0);
        expect(".o_technical_modal .modal-body button.infooter").toHaveCount(0);
        expect(".o_technical_modal .modal-footer button.infooter").toHaveCount(1);
        expect(".o_technical_modal .modal-footer button:not(.d-none)").toHaveCount(1);
        await getService("action").doAction(25);
        expect(".o_technical_modal .modal-body button.infooter").toHaveCount(0);
        expect(".o_technical_modal .modal-footer button.infooter").toHaveCount(0);
        expect('.o_technical_modal .modal-body button[special="save"]').toHaveCount(0);
        expect('.o_technical_modal .modal-footer button[special="save"]').toHaveCount(1);
        expect(".o_technical_modal .modal-footer button:not(.d-none)").toHaveCount(1);
    });

    test('button with confirm attribute in act_window action in target="new"', async () => {
        defineActions([
            {
                id: 999,
                name: "A window action",
                res_model: "partner",
                target: "new",
                type: "ir.actions.act_window",
                views: [[999, "form"]],
            },
        ]);
        Partner._views["form,999"] = `
            <form>
                <button name="method" string="Call method" type="object" confirm="Are you sure?"/>
            </form>`;
        Partner._views["form,1000"] = `<form>Another action</form>`;

        onRpc("method", () => {
            return Promise.resolve({
                id: 1000,
                name: "Another window action",
                res_model: "partner",
                target: "new",
                type: "ir.actions.act_window",
                views: [[1000, "form"]],
            });
        });

        await mountWithCleanup(WebClient);
        await getService("action").doAction(999);
        expect(".modal button[name=method]").toHaveCount(1);

        await contains(".modal button[name=method]").click();
        expect(".modal").toHaveCount(2);
        expect($(".modal:last .modal-body").text()).toBe("Are you sure?");

        await contains(".modal:last .modal-footer .btn-primary").click();
        // needs two renderings to close the ConfirmationDialog:
        //  - 1 to open the next dialog (the action in target="new")
        //  - 1 to close the ConfirmationDialog, once the next action is executed
        await animationFrame();
        expect(".modal").toHaveCount(1);
        expect(".modal main .o_content").toHaveText("Another action");
    });

    test('actions in target="new" do not update page title', async () => {
        mockService("title", () => {
            return {
                setParts({ action }) {
                    if (action) {
                        expect.step(action);
                    }
                },
            };
        });

        await mountWithCleanup(WebClient);

        // sanity check: execute an action in target="current"
        await getService("action").doAction(1);
        expect(["Partners Action 1"]).toVerifySteps();

        // execute an action in target="new"
        await getService("action").doAction(5);
        expect([]).toVerifySteps();
    });

    test("do not commit a dialog in error", async () => {
        expect.assertions(7);
        expect.errors(1);

        class ErrorClientAction extends Component {
            static template = xml`<div/>`;
            static props = ["*"];
            setup() {
                throw new Error("my error");
            }
        }
        registry.category("actions").add("failing", ErrorClientAction);

        class ClientActionTargetNew extends Component {
            static template = xml`<div class="my_action_new" />`;
            static props = ["*"];
        }
        registry.category("actions").add("clientActionNew", ClientActionTargetNew);

        class ClientAction extends Component {
            static template = xml`
                <div class="my_action" t-on-click="onClick">
                    My Action
                </div>`;
            static props = ["*"];
            setup() {
                this.action = useService("action");
            }
            async onClick() {
                try {
                    await this.action.doAction(
                        { type: "ir.actions.client", tag: "failing", target: "new" },
                        { onClose: () => expect.step("failing dialog closed") }
                    );
                } catch (e) {
                    expect(e.cause.message).toBe("my error");
                    throw e;
                }
            }
        }
        registry.category("actions").add("clientAction", ClientAction);

        const errorDialogOpened = new Deferred();
        patchWithCleanup(ClientErrorDialog.prototype, {
            setup() {
                super.setup(...arguments);
                onMounted(() => errorDialogOpened.resolve());
            },
        });

        await mountWithCleanup(WebClient);
        await getService("action").doAction({ type: "ir.actions.client", tag: "clientAction" });
        await contains(".my_action").click();
        await errorDialogOpened;
        expect(".modal").toHaveCount(1);

        await contains(".modal-body button.btn-link").click();
        expect(queryText(".modal-body .o_error_detail")).toInclude("my error");
        expect(["my error"]).toVerifyErrors();

        await contains(".modal-footer .btn-primary").click();
        expect(".modal").toHaveCount(0);

        await getService("action").doAction({
            type: "ir.actions.client",
            tag: "clientActionNew",
            target: "new",
        });
        expect(".modal .my_action_new").toHaveCount(1);

        expect([]).toVerifySteps();
    });

    test('breadcrumbs of actions in target="new"', async () => {
        await mountWithCleanup(WebClient);

        // execute an action in target="current"
        await getService("action").doAction(1);
        expect(queryAllTexts(".o_breadcrumb span")).toEqual(["Partners Action 1"]);

        // execute an action in target="new" and a list view (s.t. there is a control panel)
        await getService("action").doAction({
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });
        expect(".modal .o_breadcrumb").toHaveCount(0);
    });

    test('call switchView in an action in target="new"', async () => {
        await mountWithCleanup(WebClient);

        // execute an action in target="current"
        await getService("action").doAction(4);
        expect(".o_kanban_view").toHaveCount(1);

        // execute an action in target="new" and a list view (s.t. we can call switchView)
        await getService("action").doAction({
            xml_id: "action_5",
            name: "Create a Partner",
            res_model: "partner",
            target: "new",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        });
        expect(".modal .o_list_view").toHaveCount(1);
        expect(".o_kanban_view").toHaveCount(1);

        // click on a record in the dialog -> should do nothing as we can't switch view
        // in the dialog, and we don't want to switch view behind the dialog
        await contains(".modal .o_data_row .o_data_cell").click();
        expect(".modal .o_list_view").toHaveCount(1);
        expect(".o_kanban_view").toHaveCount(1);
    });

    test("action with 'dialog_size' key in context", async () => {
        const action = {
            name: "Some Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            target: "new",
            views: [[false, "form"]],
        };
        await mountWithCleanup(WebClient);

        await getService("action").doAction(action);
        expect(".o_dialog .modal-dialog").toHaveClass("modal-lg");

        await getService("action").doAction({ ...action, context: { dialog_size: "small" } });
        expect(".o_dialog .modal-dialog").toHaveClass("modal-sm");

        await getService("action").doAction({ ...action, context: { dialog_size: "medium" } });
        expect(".o_dialog .modal-dialog").toHaveClass("modal-md");

        await getService("action").doAction({ ...action, context: { dialog_size: "large" } });
        expect(".o_dialog .modal-dialog").toHaveClass("modal-lg");

        await getService("action").doAction({ ...action, context: { dialog_size: "extra-large" } });
        expect(".o_dialog .modal-dialog").toHaveClass("modal-xl");
    });

    test('click on record in list view action in target="new"', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "My Partners",
            res_model: "partner",
            type: "ir.actions.act_window",
            target: "new",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });

        // The list view has been opened in a dialog
        expect(".o_dialog .modal-dialog .o_list_view").toHaveCount(1);

        // click on a record in the dialog -> should do nothing as we can't switch view in the dialog
        await contains(".modal .o_data_row .o_data_cell").click();
        expect(".o_dialog .modal-dialog .o_list_view").toHaveCount(1);
        expect(".o_form_view").toHaveCount(0);
    });
});

describe("fullscreen", () => {
    test('correctly execute act_window actions in target="fullscreen"', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction(15);
        await animationFrame(); // wait for the webclient template to be re-rendered
        expect(".o_control_panel").toHaveCount(1, {
            message: "should have rendered a control panel",
        });
        expect(".o_kanban_view").toHaveCount(1, { message: "should have rendered a kanban view" });
        expect(".o_main_navbar").toHaveCount(0);
    });

    test.tags("desktop")('fullscreen on action change: back to a "current" action', async () => {
        defineActions([
            {
                id: 6,
                xml_id: "action_6",
                name: "Partner",
                res_id: 2,
                res_model: "partner",
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        ]);
        Partner._views["form,false"] = `
            <form>
                <button name="15" type="action" class="oe_stat_button" />
            </form>`;

        await mountWithCleanup(WebClient);
        await getService("action").doAction(6);
        expect(".o_main_navbar").toHaveCount(1);

        await contains("button[name='15']").click();
        await animationFrame(); // wait for the webclient template to be re-rendered
        expect(".o_main_navbar").toHaveCount(0);

        await contains(".breadcrumb li a").click();
        await animationFrame(); // wait for the webclient template to be re-rendered
        expect(".o_main_navbar").toHaveCount(1);
    });

    test.tags("desktop")('fullscreen on action change: all "fullscreen" actions', async () => {
        defineActions([
            {
                id: 6,
                xml_id: "action_6",
                name: "Partner",
                res_id: 2,
                res_model: "partner",
                target: "fullscreen",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        ]);
        Partner._views["form,false"] = `
            <form>
                <button name="15" type="action" class="oe_stat_button" />
            </form>`;

        await mountWithCleanup(WebClient);
        await getService("action").doAction(6);
        await animationFrame(); // for the webclient to react and remove the navbar
        expect(".o_main_navbar").not.toBeVisible();

        await contains("button[name='15']").click();
        await animationFrame();
        expect(".o_main_navbar").not.toBeVisible();

        await contains(".breadcrumb li a").click();
        await animationFrame();
        expect(".o_main_navbar").not.toBeVisible();
    });

    test.tags("desktop")(
        'fullscreen on action change: back to another "current" action',
        async () => {
            defineActions([
                {
                    id: 6,
                    name: "Partner",
                    res_id: 2,
                    res_model: "partner",
                    target: "current",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
                {
                    id: 24,
                    name: "Partner",
                    res_id: 2,
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[666, "form"]],
                },
            ]);
            defineMenus([
                {
                    id: "root",
                    children: [{ id: 1, children: [], name: "MAIN APP", appID: 1, actionID: 6 }],
                    name: "root",
                    appID: "root",
                },
            ]);
            Partner._views["form,false"] = `
            <form>
                <button name="24" type="action" string="Execute action 24" class="oe_stat_button"/>
            </form>`;
            Partner._views["form,666"] = `
            <form>
                <button type="action" name="15" icon="fa-star" context="{'default_partner': id}" class="oe_stat_button"/>
            </form>`;

            await mountWithCleanup(WebClient);
            await animationFrame(); // wait for the load state (default app)
            await animationFrame(); // wait for the action to be mounted
            expect("nav .o_menu_brand").toHaveCount(1);
            expect("nav .o_menu_brand").toHaveText("MAIN APP");

            await contains("button[name='24']").click();
            await animationFrame(); // wait for the webclient template to be re-rendered
            expect("nav .o_menu_brand").toHaveCount(1);

            await contains("button[name='15']").click();
            await animationFrame(); // wait for the webclient template to be re-rendered
            expect("nav.o_main_navbar").toHaveCount(0);

            await contains(queryAll(".breadcrumb li a")[1]).click();
            await animationFrame(); // wait for the webclient template to be re-rendered
            expect("nav .o_menu_brand").toHaveCount(1);
            expect("nav .o_menu_brand").toHaveText("MAIN APP");
        }
    );
});

describe("main", () => {
    test.tags("desktop")('can execute act_window actions in target="main"', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction(1);
        expect(".o_kanban_view").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partners Action 1");

        await getService("action").doAction({
            name: "Another Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
            target: "main",
        });
        expect(".o_list_view").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Another Partner Action");
    });

    test.tags("desktop")('can switch view in an action in target="main"', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "main",
        });
        expect(".o_list_view").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partner Action");

        // open first record
        await contains(".o_data_row .o_data_cell").click();
        expect(".o_form_view").toHaveCount(1);
        expect("ol.breadcrumb").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partner Action\nFirst record");
    });

    test.tags("desktop")('can restore an action in target="main"', async () => {
        await mountWithCleanup(WebClient);
        await getService("action").doAction({
            name: "Partner Action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "main",
        });
        expect(".o_list_view").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partner Action");

        // open first record
        await contains(".o_data_row .o_data_cell").click();
        expect(".o_form_view").toHaveCount(1);
        expect("ol.breadcrumb").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partner Action\nFirst record");

        await getService("action").doAction(1);
        expect(".o_kanban_view").toHaveCount(1);
        expect("ol.breadcrumb").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);

        // go back to form view
        await contains("ol.breadcrumb .o_back_button").click();
        expect(".o_form_view").toHaveCount(1);
        expect("ol.breadcrumb").toHaveCount(1);
        expect(".o_breadcrumb span").toHaveCount(1);
        expect(".o_control_panel .o_breadcrumb").toHaveText("Partner Action\nFirst record");
    });
});
