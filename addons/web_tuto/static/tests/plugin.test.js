import {
    advanceTime,
    animationFrame,
    beforeEach,
    describe,
    expect,
    keyDown,
    keyUp,
    leave,
    manuallyDispatchProgrammaticEvent,
    queryOne,
    test,
    waitFor,
    waitForNone,
    waitUntil,
} from "@odoo/hoot";
import { xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineModels,
    fields,
    getService,
    MockServer,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { router } from "@web/core/browser/router";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { pointerState } from "@web_tuto/pointer/pointer_state";
import { getStepKeys } from "@web_tuto/plugin";

describe.current.tags("desktop");

class Stage extends models.Model {
    _name = "stage";
    name = fields.Char();

    _records = [
        { id: 1, name: "New" },
        { id: 2, name: "Done" },
    ];
}

class Partner extends models.Model {
    _name = "partner";
    name = fields.Char();
    email = fields.Char();
    stage_id = fields.Many2one({ relation: "stage" });

    _records = [{ id: 1, name: "Bob", stage_id: 1 }];

    _views = {
        list: `<list><field name="name"/></list>`,
        "list,2": `<list js_class="tuto_template_list"><field name="name"/></list>`,
        kanban: `
            <kanban on_create="quick_create">
                <templates><t t-name="card"><field name="name"/></t></templates>
            </kanban>`,
        "kanban,3": `
            <kanban default_group_by="stage_id">
                <templates><t t-name="card"><field name="name"/></t></templates>
            </kanban>`,
        "form,10": `
            <form>
                <header><button name="action_check" type="object" string="Check"/></header>
                <sheet>
                    <field name="name"/>
                    <field name="email"/>
                </sheet>
            </form>`,
        "form,13": `
            <form>
                <field name="name"/>
                <field name="email"/>
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

class Note extends models.Model {
    _name = "note";
    name = fields.Char();
    description = fields.Char();

    _views = {
        "form,11": `
            <form>
                <field name="name"/>
                <div style="height: 2000px"/>
                <field name="description"/>
                <div style="height: 2000px"/>
            </form>`,
    };
}

class Invoice extends models.Model {
    _name = "invoice";
    name = fields.Char();
    line_ids = fields.One2many({
        relation: "invoice.line",
        relation_field: "invoice_id",
    });

    _views = {
        "form,12": `
            <form>
                <group><field name="name" required="1"/></group>
                <field name="line_ids">
                    <list editable="bottom">
                        <field name="name"/>
                        <field name="label"/>
                    </list>
                </field>
            </form>`,
    };
}

class InvoiceLine extends models.Model {
    _name = "invoice.line";
    name = fields.Char();
    label = fields.Char();
    invoice_id = fields.Many2one({ relation: "invoice" });
}

defineModels([Stage, Partner, Contract, Note, Invoice, InvoiceLine]);
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
    {
        id: 4,
        name: "New Note",
        res_model: "note",
        views: [[false, "form"]],
    },
    {
        id: 6,
        name: "Partners Pipeline",
        res_model: "partner",
        context: { group_by: ["name"] },
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
    },
    {
        id: 5,
        name: "New Invoice",
        res_model: "invoice",
        views: [[false, "form"]],
    },
    {
        id: 7,
        name: "Partners From Templates",
        res_model: "partner",
        views: [
            [2, "list"],
            [false, "form"],
        ],
    },
    {
        id: 9,
        name: "Partners With Another Form",
        res_model: "partner",
        views: [
            [false, "list"],
            [13, "form"],
        ],
    },
    {
        id: 8,
        name: "Partners By Stage",
        res_model: "partner",
        views: [
            [3, "kanban"],
            [false, "form"],
        ],
    },
]);

/**
 * The partner tutorial: create a partner from the list, then fill its name
 * and email, and see where to check it.
 * @returns {TutorialChapterDefinition[]}
 */
function getPartnerChapters() {
    return [
        {
            model: "partner",
            steps: [
                {
                    action: "click",
                    content: "Create a partner",
                    trigger:
                        ".o_control_panel :is(.o_list_button_add, .o-kanban-button-new), .o_kanban_quick_add",
                    type: "action",
                },
            ],
            viewType: "list",
        },
        {
            model: "partner",
            steps: [
                { content: "Give it a name", name: "name", type: "field" },
                { content: "Fill in the Email field.", name: "email", type: "field" },
                {
                    action: "click",
                    content: "Here you can check it",
                    hint: true,
                    trigger: "button[name='action_check']",
                    type: "action",
                },
            ],
            viewType: "form",
        },
    ];
}

/**
 * @returns {string[]} the keys of the steps of the tutorial, in order
 */
function getKeys() {
    return getStepKeys(chapters).flat();
}

/**
 * Replaces the chapters of the tutorial
 * @param {TutorialChapterDefinition[]} newChapters
 */
function setChapters(newChapters) {
    chapters = newChapters;
    registry.category("web_tuto.tutorials").add("partner_tutorial", chapters, { force: true });
}

/**
 * @param {...number} numbers the numbers of the steps the user did, from 1
 */
function setDone(...numbers) {
    doneNumbers = numbers;
}

/**
 * @param {string[]} keys
 * @returns {string} the numbers of the steps, e.g. "1,2"
 */
function toNumbers(keys) {
    return keys.map((key) => getKeys().indexOf(key) + 1).join();
}

let chapters;
let doneNumbers;
let resumeUrls;

/**
 * @returns {Object} the tutorial as returned by the server
 */
function getTutorial() {
    return {
        done_steps: doneNumbers.map((number) => getKeys()[number - 1]),
        id: 1,
        name: "partner_tutorial",
        rainbow_man_message: "Well done",
    };
}

/**
 * Waits for the pointer to show the given content, then hovers its ball to
 * open its bubble
 * @param {string} content
 */
async function waitForPointer(content) {
    await waitUntil(() => pointerState.trigger && pointerState.content === content);
    await animationFrame();
    await contains(".o_tutorial_pointer_tip").hover();
    await waitFor(`.o_tutorial_pointer_content:contains(${content})`);
}

beforeEach(() => {
    setChapters(getPartnerChapters());
    doneNumbers = [];
    resumeUrls = [];
    patchWithCleanup(pointerState, { trigger: undefined, content: "" });
    patchWithCleanup(session, {
        tutorial_enabled: true,
        has_running_tutorials: true,
    });
    onRpc("has_group", () => true);
    onRpc("web_tuto.tutorial", "get_running_tutorials", () => [getTutorial()]);
    onRpc("web_tuto.tutorial", "mark_steps_done", ({ args }) => {
        expect.step(`mark_done ${toNumbers(args[1])}`);
        return true;
    });
    onRpc("web_tuto.tutorial", "mark_steps_undone", ({ args }) => {
        expect.step(`mark_undone ${toNumbers(args[1])}`);
        return true;
    });
    onRpc("web_tuto.tutorial", "mark_done", ({ args }) => {
        expect.step(`tutorial done ${args[0]}`);
        return true;
    });
    onRpc("web_tuto.tutorial", "save_resume_url", ({ args }) => {
        resumeUrls.push(args);
        return true;
    });
});

test("points the first step of the displayed view", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    expect(".o_tutorial_progress").toHaveText("Step 1/4");
    expect(pointerState.trigger).toBe(document.querySelector(".o_list_button_add"));
    expect(".o_tutorial_next").toHaveCount(1);
    expect(".o_tutorial_skip").toHaveCount(1);

    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
    expect(".o_tutorial_progress").toHaveText("Step 2/4");
});

test("the bubble is only open while the ball or the bubble is hovered, and shortly after", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitUntil(() => pointerState.content === "Create a partner");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(1);
    expect(".o_tutorial_pointer_content").toHaveCount(0);

    await contains(".o_tutorial_pointer_tip").hover();
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    await contains(".o_tutorial_pointer_content").hover();
    expect(".o_tutorial_pointer_content").toHaveCount(1);

    await leave();
    await advanceTime(200);
    expect(".o_tutorial_pointer_content").toHaveCount(1);
    await contains(".o_tutorial_pointer_tip").hover();
    await leave();
    await advanceTime(200);
    expect(".o_tutorial_pointer_content").toHaveCount(1);
    await advanceTime(100);
    await waitForNone(".o_tutorial_pointer_content");
});

test("the bubble is always open when the user always shows the tips", async () => {
    patchWithCleanup(session, { tutorial_tips_shown: true });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitUntil(() => pointerState.content === "Create a partner");
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    pointerState.tipsShown = false;
    await waitForNone(".o_tutorial_pointer_content");
});

test("the ball and its bubble are on the side of the trigger set by the step", async () => {
    chapters[0].steps[0].tooltipPosition = "right";
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    let triggerRect = document.querySelector(".o_list_button_add").getBoundingClientRect();
    let ballRect = document.querySelector(".o_tutorial_pointer_tip").getBoundingClientRect();
    let bubbleRect = queryOne(".o_tutorial_pointer_content").getBoundingClientRect();
    expect(".o_tutorial_pointer_tip").toHaveClass("o_right");
    expect(ballRect.left).toBeGreaterThan(triggerRect.right - 1);
    expect(bubbleRect.left).toBeGreaterThan(ballRect.right - 1);

    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
    triggerRect = document
        .querySelector(".o_field_widget[name=name] input")
        .getBoundingClientRect();
    ballRect = document.querySelector(".o_tutorial_pointer_tip").getBoundingClientRect();
    bubbleRect = queryOne(".o_tutorial_pointer_content").getBoundingClientRect();
    const arrowRect = queryOne(
        ".o_tutorial_pointer_content .popover-arrow"
    ).getBoundingClientRect();
    expect(".o_tutorial_pointer_tip").toHaveClass("o_bottom");
    expect(ballRect.top).toBeGreaterThan(triggerRect.bottom - 1);
    expect(bubbleRect.top).toBeGreaterThan(ballRect.bottom - 1);
    expect(Math.round(arrowRect.left + arrowRect.width / 2)).toBe(
        Math.round(ballRect.left + ballRect.width / 2)
    );
});

test("the ball waits on the edge of the scroll parent of a trigger out of view", async () => {
    setChapters([
        {
            model: "note",
            steps: [{ content: "Describe it", name: "description", type: "field" }],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(4);
    await waitUntil(() => pointerState.content === "Describe it");
    await waitFor(".o_tutorial_pointer_tip.o_top");
    const ballRect = queryOne(".o_tutorial_pointer_tip").getBoundingClientRect();
    expect(ballRect.bottom).toBeLessThan(queryOne(".o_content").getBoundingClientRect().bottom + 1);
    await contains(".o_tutorial_pointer_tip").hover();
    await waitFor(".o_tutorial_pointer_content:contains(Scroll down to reach the next step.)");
    expect(".o_tutorial_next").toHaveCount(0);

    await contains(".o_tutorial_pointer_content").click();
    await waitUntil(() => queryOne(".o_content").scrollTop > 0);
    pointerState.trigger.scrollIntoView({ block: "center" });
    await waitFor(".o_tutorial_pointer_content:contains(Describe it)");
    expect(".o_tutorial_pointer_tip").toHaveClass("o_bottom");
    expect(".o_tutorial_next").toHaveCount(1);

    queryOne(".o_content").scrollTop = queryOne(".o_content").scrollHeight;
    await waitFor(".o_tutorial_pointer_content:contains(Scroll up to reach the next step.)");
    expect(".o_tutorial_pointer_tip").toHaveClass("o_bottom");
    expect(".o_tutorial_next").toHaveCount(0);
});

test("clicking the button of a step does it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
});

test("Next does the step for the user", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view");
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
    await contains(".o_tutorial_next").click();
    expect(".o_field_widget[name=name] input").toBeFocused();
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Fill in the Email field.");
});

test("focusing a field does it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 1", "mark_done 2"]);
});

test("the steps can be done in any order", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=email] input").click();
    await animationFrame();
    expect(pointerState.content).toBe("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Here you can check it");
    expect.verifySteps(["mark_done 1", "mark_done 3", "mark_done 2"]);
});

test("Next keeps the steps done after it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_back_button").click();
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 2", "mark_done 1"]);
});

test("a hint goes on with Next, and the tutorial is finished with its last view", async () => {
    setDone(2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitFor(".o_tutorial_pointer_content:contains(Here you can check it)");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["tutorial done 1"]);
    await waitFor(".o_reward_rainbow_man");
    await waitForNone(".o_tutorial_pointer_content");
});

test("the tutorial comes back to a view whose steps aren't done", async () => {
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
    expect.verifySteps(["tutorial done 1"]);
    await waitForNone(".o_tutorial_pointer_content");
});

test("a previous view proposes its last done step again, going on from there", async () => {
    setDone(1, 2);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_undone 2"]);
    await waitForPointer("Give it a name");
});

test("going back to a previous view keeps the progress", async () => {
    setDone(1, 2);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps([]);
});

test("no tutorial runs when they are disabled", async () => {
    patchWithCleanup(session, { tutorial_enabled: false });
    onRpc("web_tuto.tutorial", "get_running_tutorials", () => {
        expect.step("get_running_tutorials");
        return [getTutorial()];
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_list_view");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    expect.verifySteps([]);
});

test("a dialog of another model isn't a view of the tutorial", async () => {
    setDone(1);
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(2);
    await waitFor(".modal .o_form_view");
    await waitUntil(() => !pointerState.trigger);
    await contains(".modal .o_field_widget[name=name] input").click();
    await animationFrame();
    expect.verifySteps([]);
});

test("a dialog of the model of the tutorial is a view of it", async () => {
    setDone(1);
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(3);
    await waitForPointer("Give it a name");
    await contains(".modal .o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_done 2"]);
});

test("the pointer goes back to the last done step that can be done again", async () => {
    chapters[1].steps[1].name = "missing_field";
    chapters[1].steps[2].trigger = "button[name='missing_button']";
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_undone 3"]);
    await animationFrame();
    expect(pointerState.content).toBe("Give it a name");
});

test("the pointer doesn't go back while an RPC is pending", async () => {
    setDone(1);
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

test("a field of the lines of a x2many field is done in its line", async () => {
    setChapters([
        {
            model: "invoice",
            steps: [
                { content: "Add your first line", name: "line_ids", type: "field" },
                {
                    content: "Describe what you sell",
                    name: "line_ids.label",
                    type: "field",
                },
            ],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(pointerState.trigger).toBe(queryOne(".o_field_x2many_list_row_add button"));

    await contains(".o_field_x2many_list_row_add button").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Describe what you sell");
    expect(pointerState.trigger).toBe(queryOne(".o_data_row [name=label] input"));

    await contains(".o_data_row [name=label] input").edit("Consulting");
    expect.verifySteps(["tutorial done 1"]);
});

test("only adding a line does the step of a x2many field", async () => {
    setChapters([
        {
            model: "invoice",
            steps: [{ content: "Add your first line", name: "line_ids", type: "field" }],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(pointerState.trigger).toBe(queryOne(".o_field_x2many_list_row_add button"));

    await contains(".o_field_widget[name=line_ids] th[data-name=name]").click();
    await animationFrame();
    expect.verifySteps([]);

    await contains(".o_field_x2many_list_row_add button").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("an invalid field is pointed until filled in, to go on with the tutorial", async () => {
    setChapters([
        {
            model: "invoice",
            steps: [{ content: "Add your first line", name: "line_ids", type: "field" }],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");

    await contains(".o_form_button_save").click();
    await waitFor(
        ".o_tutorial_pointer_content:contains(Fill in “Name” to go on with the tutorial.)"
    );
    expect(pointerState.trigger).toBe(queryOne(".o_field_widget[name=name] input"));
    expect(".o_tutorial_pointer_content").toHaveClass("o_tutorial_invalid");
    expect(".o_tutorial_next").toHaveCount(0);
    expect(".o_tutorial_progress").toHaveCount(0);

    await contains(".o_field_widget[name=name] input").edit("INV/001");
    await waitForPointer("Add your first line");
    expect.verifySteps([]);
});

test("Next adds a line to the x2many field of a step", async () => {
    setChapters([
        {
            model: "invoice",
            steps: [
                { content: "Add your first line", name: "line_ids", type: "field" },
                {
                    content: "Describe what you sell",
                    name: "line_ids.label",
                    type: "field",
                },
            ],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 1"]);
    expect(".o_data_row").toHaveCount(1);
    await waitForPointer("Describe what you sell");
    expect(".o_tutorial_progress").toHaveText("Step 2/2");
});

test("the URL of the view pointing a step to do is saved to resume the tutorial there", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await advanceTime(500);
    expect(resumeUrls).toEqual([[[1], "/odoo/action-1"]]);

    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await advanceTime(500);
    expect(resumeUrls.at(-1)).toEqual([[1], "/odoo/action-1/new"]);

    await contains(".o_field_widget[name=name] input").edit("Alice");
    await contains(".o_form_button_save").click();
    await waitUntil(() => typeof router.current.resId === "number");
    await animationFrame();
    await advanceTime(500);
    expect(resumeUrls.at(-1)).toEqual([[1], `/odoo/action-1/${router.current.resId}`]);
    expect.verifySteps(["mark_done 1", "mark_done 2"]);

    const count = resumeUrls.length;
    await getService("action").doAction(1);
    await waitUntil(() => pointerState.content === "Create a partner");
    await advanceTime(500);
    expect(resumeUrls).toHaveLength(count);
});

test("the pointer hides while its trigger is covered", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");

    const cover = document.createElement("div");
    cover.style.cssText = "position: fixed; inset: 0; z-index: 2000;";
    document.body.append(cover);
    await waitForNone(".o_tutorial_pointer_tip");

    cover.remove();
    await waitFor(".o_tutorial_pointer_tip");
});

test("a list chapter is shown in the kanban view of its model too", async () => {
    await mountWebClient();
    await getService("action").doAction(6);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(queryOne(".o_control_panel .o-kanban-button-new"));

    await contains(".o_control_panel .o-kanban-button-new").click();
    expect.verifySteps(["mark_done 1"]);
});

test("a new record of a quick create kanban is created with its New button", async () => {
    chapters[0].viewType = "kanban";
    await mountWebClient();
    await getService("action").doAction(6);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(queryOne(".o_control_panel .o-kanban-button-new"));

    await contains(".o_kanban_group .o_kanban_quick_add").click();
    expect.verifySteps(["mark_done 1"]);
});

/**
 * @returns {TutorialStepDefinition[]} the steps deleting the record from the
 *   actions menu
 */
function getDeleteSteps() {
    return [
        {
            action: "click",
            content: "Open the actions",
            trigger: ".o_cp_action_menus button[data-hotkey='u']",
            type: "action",
        },
        {
            action: "click",
            content: "Delete it",
            trigger: ".o-dropdown--menu .o_menu_item:has([data-icon='delete'])",
            type: "action",
        },
    ];
}

test("a New button opening a dropdown is done once clicked", async () => {
    const listView = registry.category("views").get("list");
    class TemplateListController extends listView.Controller {
        static components = { ...listView.Controller.components, Dropdown, DropdownItem };
    }
    registry.category("views").add("tuto_template_list", {
        ...listView,
        Controller: TemplateListController,
        buttonTemplate: xml`
            <Dropdown>
                <button class="btn btn-primary o_list_button_add">New</button>
                <t t-set-slot="content">
                    <DropdownItem class="'o_new_partner'" onSelected="() => this.onClickCreate()">New Partner</DropdownItem>
                </t>
            </Dropdown>`,
    });
    await mountWebClient();
    await getService("action").doAction(7);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);

    await contains(".o_new_partner").click();
    await waitForPointer("Give it a name");
});

test("an item of the actions menu is clicked once the menu is open", async () => {
    chapters[1].steps = getDeleteSteps();
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Open the actions");
    await contains(".o_cp_action_menus button[data-hotkey='u']").click();
    expect.verifySteps(["mark_done 2"]);
    await waitUntil(() => pointerState.trigger?.matches(".o_menu_item:has([data-icon='delete'])"));

    await contains(".o_menu_item:contains(Duplicate)").click();
    await animationFrame();
    expect.verifySteps([]);

    await contains(".o_cp_action_menus button[data-hotkey='u']").click();
    await contains(".o_menu_item:contains(Delete)").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("Next opens the actions menu, then clicks its Delete item", async () => {
    chapters[1].steps = getDeleteSteps();
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Open the actions");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Delete it");
    await contains(".o_tutorial_next").click();
    await waitFor(".modal:contains(Are you sure)");
    expect.verifySteps(["tutorial done 1"]);
});

test("Next adds a stage once named in the quick create opened by the previous step", async () => {
    setChapters([
        {
            model: "partner",
            steps: [
                {
                    action: "click",
                    content: "Open the quick create",
                    trigger: ".o_quick_create_folded .o_quick_create_button",
                    type: "action",
                },
                {
                    action: "click",
                    content: "Name a stage, then add it",
                    trigger: ".o_quick_create_unfolded .o_kanban_add",
                    type: "action",
                },
            ],
            viewType: "kanban",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(8);
    await waitForPointer("Open the quick create");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 1"]);
    await waitFor(".o_quick_create_unfolded input:focus");

    await waitForPointer("Name a stage, then add it");
    await contains(".o_quick_create_unfolded input").edit("To Do", { confirm: false });
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["tutorial done 1"]);
    await waitFor(".o_kanban_group:contains(To Do)");
});

/**
 * Opens a kanban view of the partners grouped by stage, with a tutorial
 * moving Bob to the stage "Done" (shown with its partner Alice)
 */
async function openDragAndDropTutorial() {
    setChapters([
        {
            model: "partner",
            steps: [
                {
                    action: "drag",
                    content: "Drag Bob",
                    trigger: ".o_kanban_record:contains(Bob)",
                    type: "action",
                },
                {
                    action: "drop",
                    content: "Drop him in Done",
                    trigger: ".o_kanban_group:contains(Done)",
                    type: "action",
                },
            ],
            viewType: "kanban",
        },
    ]);
    await mountWebClient();
    MockServer.env["partner"].create({ name: "Alice", stage_id: 2 });
    await getService("action").doAction(8);
    await waitForPointer("Drag Bob");
}

test("a drag is done once started, its drop being only pointed meanwhile", async () => {
    await openDragAndDropTutorial();
    expect(pointerState.trigger).toBe(queryOne(".o_kanban_record:contains(Bob)"));

    const { drop, moveTo } = await contains(".o_kanban_record:contains(Bob)").drag();
    expect.verifySteps(["mark_done 1"]);
    await moveTo(".o_kanban_group:contains(Done)");
    await waitUntil(() => pointerState.content === "Drop him in Done");
    await drop();
    expect.verifySteps(["tutorial done 1"]);
});

test("a cancelled drag stops pointing its drop", async () => {
    await openDragAndDropTutorial();
    await contains(".o_kanban_record:contains(Bob)").drag();
    expect.verifySteps(["mark_done 1"]);
    await waitUntil(() => pointerState.content === "Drop him in Done");

    manuallyDispatchProgrammaticEvent(document, "pointercancel");
    await waitUntil(() => pointerState.content === "Drag Bob");
    expect.verifySteps([]);
});

test("a drop elsewhere goes back to its drag", async () => {
    await openDragAndDropTutorial();
    await contains(".o_kanban_record:contains(Bob)").dragAndDrop(".o_kanban_group:contains(New)");
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Drag Bob");

    await contains(".o_kanban_record:contains(Bob)").dragAndDrop(".o_kanban_group:contains(Done)");
    expect.verifySteps(["tutorial done 1"]);
});

test("Next drags and drops the element of a drag onto the one of its drop", async () => {
    await openDragAndDropTutorial();
    await contains(".o_tutorial_next").click();
    await waitFor(".o_kanban_group:contains(Done) .o_kanban_record:contains(Bob)");
    expect.verifySteps(["mark_done 1", "tutorial done 1"]);
});

test("the web client doesn't wait for the tutorials to be rendered", async () => {
    onRpc("web_tuto.tutorial", "get_running_tutorials", () => new Promise(() => {}));
    await mountWebClient();
    await getService("action").doAction(1);
    expect(".o_list_view").toHaveCount(1);
});

test("a field autofocused while a key is held isn't done", async () => {
    setDone(1);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await keyDown("Shift");
    await animationFrame();
    queryOne(".o_field_widget[name=email] input").focus();
    await animationFrame();
    await keyUp("Shift");
    expect.verifySteps([]);
});

test("a field of the lines of a x2many field isn't the field of the form with its name", async () => {
    setChapters([
        {
            model: "invoice",
            steps: [{ content: "Name the invoice", name: "name", type: "field" }],
            viewType: "form",
        },
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Name the invoice");
    await contains(".o_field_x2many_list_row_add button").click();
    await contains(".o_data_row [name=name] input").click();
    await animationFrame();
    expect.verifySteps([]);
    expect(pointerState.trigger).toBe(
        queryOne(".o_field_widget[name=name]:not(.o_data_row *) input")
    );
});

test("a disabled button isn't pointed", async () => {
    const listView = registry.category("views").get("list");
    registry.category("views").add("tuto_template_list", {
        ...listView,
        buttonTemplate: xml`<button class="btn btn-primary o_list_button_add" disabled="">New</button>`,
    });
    await mountWebClient();
    await getService("action").doAction(7);
    await waitFor(".o_list_button_add:disabled");
    await animationFrame();
    expect(pointerState.trigger).toBe(undefined);
});

test("Next waits for the pending RPCs to do the step, the view not being ready", async () => {
    const { promise, resolve } = Promise.withResolvers();
    onRpc("partner", "slow_method", () => promise);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    getService("orm").call("partner", "slow_method", []);
    await contains(".o_tutorial_next").click();
    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps([]);

    resolve(true);
    await waitFor(".o_form_view");
    expect.verifySteps(["mark_done 1"]);
});

test("Next does the step once the responses of the pending RPCs are processed", async () => {
    const { promise, resolve } = Promise.withResolvers();
    onRpc("partner", "slow_method", () => promise);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    getService("orm")
        .call("partner", "slow_method", [])
        .then(() => queryOne(".o_list_button_add").setAttribute("disabled", ""));
    await contains(".o_tutorial_next").click();

    resolve(true);
    await animationFrame();
    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    expect.verifySteps([]);
});

test("Next doesn't do the step of a view left during the pending RPCs", async () => {
    const { promise, resolve } = Promise.withResolvers();
    onRpc("partner", "slow_method", () => promise);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    getService("orm").call("partner", "slow_method", []);
    await contains(".o_tutorial_next").click();
    await contains(".o_data_row .o_data_cell").click();

    resolve(true);
    await waitFor(".o_form_view");
    await animationFrame();
    expect(router.current.resId).toBe(1);
    expect.verifySteps([]);
});

test("the registry rejects a step not matching the shape of its type and action", async () => {
    patchWithCleanup(odoo, { debug: "1" });
    const tutorials = registry.category("web_tuto.tutorials");
    const addSteps = (...steps) =>
        tutorials.add("invalid_tutorial", [{ model: "partner", steps, viewType: "form" }], {
            force: true,
        });
    const drag = { action: "drag", content: "Drag it", trigger: ".o_card", type: "action" };
    const drop = { action: "drop", content: "Drop it", trigger: ".o_column", type: "action" };
    expect(() => addSteps({ content: "Do it", name: "name", type: "field" })).not.toThrow();
    expect(() => addSteps({ content: "Do it", trigger: ".o_button", type: "field" })).toThrow();
    expect(() => addSteps({ content: "Do it", trigger: ".o_button", type: "action" })).toThrow();
    expect(() =>
        addSteps({
            action: "click",
            content: "Do it",
            opener: ".o_menu",
            trigger: ".o_button",
            type: "action",
        })
    ).toThrow();
    expect(() => addSteps(drag, drop)).not.toThrow();
    expect(() => addSteps(drag)).toThrow(/drop/);
    expect(() => addSteps(drop)).toThrow(/drop/);
});
