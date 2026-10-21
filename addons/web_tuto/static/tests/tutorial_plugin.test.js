import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    test,
    waitFor,
    waitForNone,
} from "@odoo/hoot";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { pointerState } from "@web_tuto/tutorial_pointer/tutorial_pointer";

describe.current.tags("desktop");

class Partner extends models.Model {
    _name = "partner";
    name = fields.Char();
    email = fields.Char();

    _records = [{ id: 1, name: "Bob" }];

    _views = {
        list: `<list><field name="name"/></list>`,
        form: `
            <form>
                <header><button name="action_check" type="object" string="Check"/></header>
                <sheet>
                    <field name="name"/>
                    <field name="email"/>
                </sheet>
            </form>`,
    };

    action_check() {
        return false;
    }
}

class Contract extends models.Model {
    _name = "contract";
    name = fields.Char();

    _views = {
        form: `<form><field name="name"/></form>`,
    };
}

defineModels([Partner, Contract]);
defineActions([
    {
        id: 1,
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    },
    {
        id: 2,
        name: "New Contract",
        res_model: "contract",
        target: "new",
        views: [[false, "form"]],
    },
    {
        id: 3,
        name: "New Partner",
        res_model: "partner",
        target: "new",
        views: [[false, "form"]],
    },
]);

/**
 * The partner tutorial, as returned by the server: create a partner from the
 * list, then fill its name and email, and see where to check it.
 */
function getPartnerTutorial() {
    return {
        id: 1,
        name: "partner_tutorial",
        rainbowManMessage: "Well done",
        views: [
            {
                id: 1,
                type: "list",
                model: "partner",
                actions: [
                    {
                        id: 2,
                        kind: "verb",
                        verb: "new",
                        view_type: "list",
                        content: "Create a partner",
                    },
                ],
            },
            {
                id: 3,
                type: "form",
                model: "partner",
                actions: [
                    {
                        id: 4,
                        kind: "field",
                        name: "name",
                        scope: ".o_form_view",
                        label: "Name",
                        content: "Give it a name",
                    },
                    {
                        id: 5,
                        kind: "field",
                        name: "email",
                        scope: ".o_form_view",
                        label: "Email",
                    },
                    {
                        id: 6,
                        kind: "button",
                        name: "action_check",
                        scope: ".o_form_view",
                        label: "Check",
                        content: "Here you can check it",
                        hint: true,
                    },
                ],
            },
        ],
    };
}

/**
 * @param {number[]} ids
 */
function setDone(...ids) {
    for (const action of tutorial.views.flatMap((view) => view.actions)) {
        action.done = ids.includes(action.id);
    }
}

let tutorial;

async function waitForPointer(content) {
    await waitFor(`.o_tutorial_pointer_content:contains(${content})`);
}

beforeEach(() => {
    tutorial = getPartnerTutorial();
    patchWithCleanup(session, {
        tutorial_enabled: true,
        has_running_tutorials: true,
    });
    onRpc("has_group", () => true);
    onRpc("web_tuto.tutorial", "get_running_tutorials", () => [tutorial]);
    onRpc("web_tuto.step", "mark_done", ({ args }) => {
        expect.step(`mark_done ${args[0]}`);
        return true;
    });
    onRpc("web_tuto.step", "mark_undone", ({ args }) => {
        expect.step(`mark_undone ${args[0]}`);
        return true;
    });
    onRpc("web_tuto.tutorial", "consume", ({ args }) => {
        expect.step(`consume ${args[0]}`);
        return true;
    });
});

test("points the first action of the displayed view", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(document.querySelector(".o_list_button_add"));
    expect(".o_tutorial_next").toHaveCount(1);
    expect(".o_tutorial_skip").toHaveCount(1);
});

test("clicking the button of an action does it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Give it a name");
});

test("Next does the action for the user", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view");
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Give it a name");
    await contains(".o_tutorial_next").click();
    expect(".o_field_widget[name=name] input").toBeFocused();
    expect.verifySteps(["mark_done 4"]);
    await waitForPointer("Fill in the Email field.");
});

test("focusing a field does it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 2", "mark_done 4"]);
});

test("the actions can be done in any order", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=email] input").click();
    await animationFrame();
    expect(".o_tutorial_pointer_content").toHaveText(/Give it a name/);
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Here you can check it");
    expect.verifySteps(["mark_done 2", "mark_done 5", "mark_done 4"]);
});

test("a hint goes on with Next, and the tutorial is finished with its last view", async () => {
    setDone(4, 5);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Here you can check it");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 6", "consume 1"]);
    await waitFor(".o_reward_rainbow_man");
    await waitForNone(".o_tutorial_pointer_content");
});

test("the tutorial comes back to a view whose actions aren't done", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_back_button, .breadcrumb-item a").click();
    await waitForPointer("Create a partner");
    expect.verifySteps([]);
});

test("a tutorial can be skipped", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_skip").click();
    expect.verifySteps(["consume 1"]);
    await waitForNone(".o_tutorial_pointer_content");
});

test("a previous view proposes its last done action again, going on from there", async () => {
    setDone(2, 4);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_undone 4"]);
    await waitForPointer("Give it a name");
});

test("going back to a previous view keeps the progress", async () => {
    setDone(2, 4);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps([]);
});

test("no tutorial runs when they are disabled", async () => {
    patchWithCleanup(session, { tutorial_enabled: false });
    await mountWebClient();
    await getService("action").doAction(1);
    await animationFrame();
    expect(".o_tutorial_pointer_content").toHaveCount(0);
});

test("a dialog of another model isn't a view of the tutorial", async () => {
    setDone(2);
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(2);
    await waitFor(".modal .o_form_view");
    await waitForNone(".o_tutorial_pointer_content");
    await contains(".modal .o_field_widget[name=name] input").click();
    await animationFrame();
    expect.verifySteps([]);
});

test("a dialog of the model of the tutorial is a view of it", async () => {
    setDone(2);
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(3);
    await waitForPointer("Give it a name");
    await contains(".modal .o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_done 4"]);
});

test("the pointer goes back to the last done action that can be done again", async () => {
    // the email and the button can't be done anymore
    tutorial.views[1].actions[1].name = "missing_field";
    tutorial.views[1].actions[2].name = "missing_button";
    setDone(2, 4, 5);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_undone 5"]);
    await animationFrame();
    expect(".o_tutorial_pointer_content").toHaveText(/Give it a name/);
});

test("the pointer doesn't go back while an RPC is pending", async () => {
    setDone(2);
    const { promise, resolve } = Promise.withResolvers();
    onRpc("partner", "slow_method", () => promise);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    getService("orm").call("partner", "slow_method", []);
    await waitForNone(".o_tutorial_pointer_content");
    resolve(true);
    await waitForPointer("Create a partner");
    expect.verifySteps([]);
});
