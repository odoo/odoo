import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { makeActionAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import {
    contains,
    defineModels,
    fields,
    getService,
    makeDialogMockEnv,
    models,
    mountActionHost,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class Thing extends models.Model {
    _name = "thing";
    name = fields.Char();
    _records = [{ id: 1, name: "one" }];
    _views = { form: `<form><field name="name"/></form>` };
}
defineModels([Thing]);

for (const save of [false, true]) {
    test(`awaitable form action settles after ${save ? "saving" : "canceling"} its dialog`, async () => {
        await mountActionHost();
        const pending = makeActionAwaitable(getService("action"), {
            type: "ir.actions.act_window",
            res_model: "thing",
            res_id: 1,
            views: [[false, "form"]],
            target: "new",
        });
        if (save) {
            await contains(".modal input").edit("changed");
            await contains(".modal .o_form_button_save").click();
        } else {
            await contains(".modal .o_form_button_cancel").click();
        }
        const record = await pending;
        expect(record?.resId).toBe(save ? 1 : undefined);
        await animationFrame();
        expect(".modal").toHaveCount(0);
    });
}

test("an inherited dialog-close failure reaches the caller after saving", async () => {
    await mountActionHost();
    const action = getService("action");
    const error = new Error("inherited close failed");
    const editor = {
        type: "ir.actions.act_window",
        res_model: "thing",
        res_id: 1,
        views: [[false, "form"]],
        target: "new",
    };
    await action.doAction(editor, {
        onClose: () => {
            throw error;
        },
    });
    await animationFrame();
    const pending = makeActionAwaitable(action, { ...editor }).catch(
        (reason) => reason,
    );
    await animationFrame();
    await animationFrame();
    await contains(".modal input").edit("changed");
    await contains(".modal .o_form_button_save").click();
    expect(await pending).toBe(error);
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

const API = [
    "doAction",
    "doActionButton",
    "switchView",
    "restore",
    "loadState",
    "loadAction",
    "pushState",
    "getCurrentAction",
];

test("the override leaves the whole action service reachable", async () => {
    await makeDialogMockEnv();
    const action = getService("action");
    expect(API.filter((name) => typeof action[name] !== "function")).toEqual([]);
    expect("currentController" in action).toBe(true);
});

test("an object button on a form still reaches doActionButton", async () => {
    onRpc("/web/dataset/call_button/thing/do_it", () => {
        expect.step("call_button");
        return { type: "ir.actions.act_window_close" };
    });
    await mountView({
        type: "form",
        resModel: "thing",
        resId: 1,
        arch: `<form>
                 <header><button name="do_it" type="object" string="Do it"/></header>
                 <field name="name"/>
               </form>`,
    });
    await click("button[name='do_it']");
    await animationFrame();
    expect.verifySteps(["call_button"]);
});

test("an action dispatched over a dialog is rerouted to a dialog", async () => {
    await makeDialogMockEnv();
    document.body.classList.add("modal-open");
    const seen = [];
    const action = getService("action");
    const request = { type: "ir.actions.client", tag: "__probe__", target: "current" };
    try {
        await action.doAction(request).catch(() => {});
        seen.push(request.target);
    } finally {
        document.body.classList.remove("modal-open");
    }
    expect(seen).toEqual(["new"]);
});
