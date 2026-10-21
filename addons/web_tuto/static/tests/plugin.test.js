import {
    advanceTime,
    animationFrame,
    beforeEach,
    describe,
    expect,
    leave,
    queryOne,
    test,
    waitFor,
    waitForNone,
    waitUntil,
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
import { xml } from "@odoo/owl";
import { router } from "@web/core/browser/router";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { pointerState } from "@web_tuto/pointer/pointer_state";

describe.current.tags("desktop");

class Partner extends models.Model {
    _name = "partner";
    name = fields.Char();
    email = fields.Char();

    _records = [{ id: 1, name: "Bob" }];

    _views = {
        list: `<list><field name="name"/></list>`,
        "list,2": `<list js_class="tuto_template_list"><field name="name"/></list>`,
        kanban: `
            <kanban on_create="quick_create">
                <templates><t t-name="card"><field name="name"/></t></templates>
            </kanban>`,
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

class Note extends models.Model {
    _name = "note";
    name = fields.Char();
    description = fields.Char();

    _views = {
        form: `
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
    line_ids = fields.One2many({ relation: "invoice.line", relation_field: "invoice_id" });

    _views = {
        form: `
            <form>
                <group><field name="name" required="1"/></group>
                <field name="line_ids">
                    <list editable="bottom">
                        <field name="label"/>
                    </list>
                </field>
            </form>`,
    };
}

class InvoiceLine extends models.Model {
    _name = "invoice.line";
    label = fields.Char();
    invoice_id = fields.Many2one({ relation: "invoice" });
}

defineModels([Partner, Contract, Note, Invoice, InvoiceLine]);
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
        chapters: [
            {
                id: 1,
                view_type: "list",
                model: "partner",
                steps: [
                    {
                        id: 2,
                        type: "button",
                        name: "new",
                        content: "Create a partner",
                    },
                ],
            },
            {
                id: 3,
                view_type: "form",
                model: "partner",
                steps: [
                    {
                        id: 4,
                        type: "field",
                        name: "name",
                        scope: ".o_form_view",
                        content: "Give it a name",
                    },
                    {
                        id: 5,
                        type: "field",
                        name: "email",
                        scope: ".o_form_view",
                        content: "Fill in the Email field.",
                    },
                    {
                        id: 6,
                        type: "button",
                        name: "action_check",
                        scope: ".o_form_view",
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
    for (const step of tutorial.chapters.flatMap((chapter) => chapter.steps)) {
        step.done = ids.includes(step.id);
    }
}

let tutorial;
let resumeUrls;

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
    tutorial = getPartnerTutorial();
    resumeUrls = [];
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
    expect.verifySteps(["mark_done 2"]);
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
    tutorial.chapters[0].steps[0].tooltip_position = "right";
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
    expect.verifySteps(["mark_done 2"]);
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
    tutorial = {
        id: 2,
        name: "note_tutorial",
        chapters: [
            {
                id: 7,
                view_type: "form",
                model: "note",
                steps: [
                    {
                        id: 8,
                        type: "field",
                        name: "description",
                        scope: ".o_form_view",
                        content: "Describe it",
                    },
                ],
            },
        ],
    };
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
});

test("clicking the button of a step does it", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Give it a name");
});

test("Next does the step for the user", async () => {
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
    expect.verifySteps(["mark_done 2", "mark_done 5", "mark_done 4"]);
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
    expect.verifySteps(["mark_done 4", "mark_done 2"]);
});

test("a hint goes on with Next, and the tutorial is finished with its last view", async () => {
    setDone(4, 5);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitFor(".o_tutorial_pointer_content:contains(Here you can check it)");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 6", "tutorial done 1"]);
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

test("the pointer goes back to the last done step that can be done again", async () => {
    tutorial.chapters[1].steps[1].name = "missing_field";
    tutorial.chapters[1].steps[2].name = "missing_button";
    setDone(2, 4, 5);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_undone 5"]);
    await animationFrame();
    expect(pointerState.content).toBe("Give it a name");
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

test("a field of the lines of a x2many field is done in its line", async () => {
    tutorial = {
        id: 3,
        name: "invoice_tutorial",
        chapters: [
            {
                id: 8,
                view_type: "form",
                model: "invoice",
                steps: [
                    {
                        id: 9,
                        type: "field",
                        name: "line_ids",
                        scope: ".o_form_view",
                        content: "Add your first line",
                    },
                    {
                        id: 10,
                        type: "field",
                        name: "label",
                        x2many: "line_ids",
                        scope: ".o_form_view",
                        content: "Describe what you sell",
                    },
                ],
            },
        ],
    };
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(pointerState.trigger).toBe(queryOne(".o_field_x2many_list_row_add button"));

    await contains(".o_field_x2many_list_row_add button").click();
    expect.verifySteps(["mark_done 9"]);
    await waitForPointer("Describe what you sell");
    expect(pointerState.trigger).toBe(queryOne(".o_data_row [name=label] input"));

    await contains(".o_data_row [name=label] input").edit("Consulting");
    expect.verifySteps(["mark_done 10", "tutorial done 3"]);
});

test("an invalid field is pointed until filled in, to go on with the tutorial", async () => {
    tutorial = {
        id: 3,
        name: "invoice_tutorial",
        chapters: [
            {
                id: 8,
                view_type: "form",
                model: "invoice",
                steps: [
                    {
                        id: 9,
                        type: "field",
                        name: "line_ids",
                        scope: ".o_form_view",
                        content: "Add your first line",
                    },
                ],
            },
        ],
    };
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");

    await contains(".o_form_button_save").click();
    await waitFor(
        ".o_tutorial_pointer_content:contains(Fill in “Name” to go on with the tutorial.)"
    );
    expect(pointerState.trigger).toBe(queryOne(".o_field_widget[name=name] input"));
    expect(".o_tutorial_next").toHaveCount(0);
    expect(".o_tutorial_progress").toHaveCount(0);

    await contains(".o_field_widget[name=name] input").edit("INV/001");
    await waitForPointer("Add your first line");
    expect.verifySteps([]);
});

test("Next adds a line to the x2many field of a step", async () => {
    tutorial = {
        id: 3,
        name: "invoice_tutorial",
        chapters: [
            {
                id: 8,
                view_type: "form",
                model: "invoice",
                steps: [
                    {
                        id: 9,
                        type: "field",
                        name: "line_ids",
                        scope: ".o_form_view",
                        content: "Add your first line",
                    },
                    {
                        id: 10,
                        type: "field",
                        name: "label",
                        x2many: "line_ids",
                        scope: ".o_form_view",
                        content: "Describe what you sell",
                    },
                ],
            },
        ],
    };
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(".o_data_row").toHaveCount(0);

    await contains(".o_tutorial_next").click();
    expect.verifySteps(["mark_done 9"]);
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
    await advanceTime(500);
    expect(resumeUrls.at(-1)).toEqual([[1], `/odoo/action-1/${router.current.resId}`]);
    expect.verifySteps(["mark_done 2", "mark_done 4"]);

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
    expect.verifySteps(["mark_done 2"]);
});

test("a new record of a quick create kanban is created with its New button", async () => {
    Object.assign(tutorial.chapters[0], { view_type: "kanban" });
    await mountWebClient();
    await getService("action").doAction(6);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(queryOne(".o_control_panel .o-kanban-button-new"));

    await contains(".o_kanban_group .o_kanban_quick_add").click();
    expect.verifySteps(["mark_done 2"]);
});

function defineTemplateListView() {
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
                    <DropdownItem class="'o_from_template'" onSelected="() => {}">From Template</DropdownItem>
                </t>
            </Dropdown>`,
    });
}

test("a New button opening a dropdown is done by the first item of its menu", async () => {
    defineTemplateListView();
    await mountWebClient();
    await getService("action").doAction(7);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitUntil(() => pointerState.trigger === queryOne(".o_new_partner"));
    expect.verifySteps([]);

    await contains(".o_new_partner").click();
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Give it a name");
});

test("Next picks the first item of the menu of a New button opening a dropdown", async () => {
    defineTemplateListView();
    await mountWebClient();
    await getService("action").doAction(7);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view");
    expect.verifySteps(["mark_done 2"]);
    await waitForPointer("Give it a name");
});
