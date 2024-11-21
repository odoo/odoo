import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    contains,
    defineActions,
    defineModels,
    findComponent,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";

import { formView } from "@web/views/form/form_view";
import { listView } from "@web/views/list/list_view";
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
                <group>
                    <field name="display_name"/>
                </group>
            </form>`,
        "kanban,1": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        "list,false": `<list><field name="display_name"/></list>`,
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
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        mobile_view_mode: "kanban",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [1, "kanban"],
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
]);

test("close the currently opened dialog", async () => {
    await mountWithCleanup(WebClient);
    // execute an action in target="new"
    await getService("action").doAction(5);
    expect(".o_technical_modal .o_form_view").toHaveCount(1);
    // execute an 'ir.actions.act_window_close' action
    await getService("action").doAction({
        type: "ir.actions.act_window_close",
    });
    expect(".o_technical_modal .o_form_view").toHaveCount(0);
});

test("close dialog by clicking on the header button", async () => {
    await mountWithCleanup(WebClient);
    // execute an action in target="new"
    function onClose() {
        expect.step("on_close");
    }
    await getService("action").doAction(5, { onClose });
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .modal-header button").click();
    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps(["on_close"]);

    // execute an 'ir.actions.act_window_close' action
    // should not call 'on_close' as it was already called.
    await getService("action").doAction({ type: "ir.actions.act_window_close" });
    expect.verifySteps([]);
});

test('execute "on_close" only if there is no dialog to close', async () => {
    await mountWithCleanup(WebClient);
    // execute an action in target="new"
    await getService("action").doAction(5);
    function onClose() {
        expect.step("on_close");
    }
    const options = { onClose };
    // execute an 'ir.actions.act_window_close' action
    // should not call 'on_close' as there is a dialog to close
    await getService("action").doAction({ type: "ir.actions.act_window_close" }, options);
    expect.verifySteps([]);
    // execute again an 'ir.actions.act_window_close' action
    // should call 'on_close' as there is no dialog to close
    await getService("action").doAction({ type: "ir.actions.act_window_close" }, options);
    expect.verifySteps(["on_close"]);
});

test("close action with provided infos", async () => {
    expect.assertions(1);

    await mountWithCleanup(WebClient);
    const options = {
        onClose: function (infos) {
            expect(infos).toBe("just for testing", {
                message: "should have the correct close infos",
            });
        },
    };
    await getService("action").doAction(
        {
            type: "ir.actions.act_window_close",
            infos: "just for testing",
        },
        options
    );
});

test("history back calls on_close handler of dialog action", async () => {
    const webClient = await mountWithCleanup(WebClient);
    function onClose() {
        expect.step("on_close");
    }
    // open a new dialog form
    await getService("action").doAction(5, { onClose });
    expect(".modal").toHaveCount(1);
    const form = findComponent(webClient, (c) => c instanceof formView.Controller);
    form.env.config.historyBack();
    expect.verifySteps(["on_close"]);
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test.tags("desktop")("history back called within on_close", async () => {
    let list;
    patchWithCleanup(listView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            list = this;
        },
    });
    await mountWithCleanup(WebClient);

    await getService("action").doAction(1);
    expect(".o_kanban_view").toHaveCount(1);
    await getService("action").doAction(3);
    expect(".o_list_view").toHaveCount(1);

    function onClose() {
        list.env.config.historyBack();
        expect.step("on_close");
    }
    // open a new dialog form
    await getService("action").doAction(5, { onClose });

    await contains(".modal-header button.btn-close").click();
    // await nextTick();
    expect(".modal").toHaveCount(0);
    expect(".o_list_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
    expect.verifySteps(["on_close"]);
});

test.tags("desktop");
test("history back calls onclose handler of dialog action with 2 breadcrumbs", async () => {
    let list;
    patchWithCleanup(listView.Controller.prototype, {
        setup() {
            super.setup(...arguments);
            list = this;
        },
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1); // kanban
    await getService("action").doAction(3); // list
    expect(".o_list_view").toHaveCount(1);
    function onClose() {
        expect.step("on_close");
    }
    // open a new dialog form
    await getService("action").doAction(5, { onClose });
    expect(".modal").toHaveCount(1);
    expect(".o_list_view").toHaveCount(1);
    list.env.config.historyBack();
    expect.verifySteps(["on_close"]);
    await animationFrame();
    expect(".o_list_view").toHaveCount(1);
    expect(".modal").toHaveCount(0);
});

test.tags("desktop")("web client is not deadlocked when a view crashes", async () => {
    expect.assertions(4);
    expect.errors(1);

    const readOnFirstRecordDef = new Deferred();
    onRpc("web_read", ({ args }) => {
        if (args[0][0] === 1) {
            return readOnFirstRecordDef;
        }
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(3);
    // open first record in form view. this will crash and will not
    // display a form view
    await contains(".o_list_view .o_data_cell").click();
    readOnFirstRecordDef.reject(new Error("not working as intended"));
    await animationFrame();
    expect.verifyErrors(["not working as intended"]);

    expect(".o_list_view").toHaveCount(1, { message: "there should still be a list view in dom" });
    // open another record, the read will not crash
    await contains(".o_list_view .o_data_row:eq(1) .o_data_cell").click();
    expect(".o_list_view").toHaveCount(0, { message: "there should not be a list view in dom" });
    expect(".o_form_view").toHaveCount(1, { message: "there should be a form view in dom" });
});
