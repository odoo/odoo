import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    keyDown,
    keyUp,
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
import { pointerState } from "@web_tutorial/pointer/pointer_state";

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
        "kanban,5": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                        <button name="action_check" type="object" string="Check"/>
                    </t>
                </templates>
            </kanban>`,
        "form,10": `
            <form>
                <header>
                    <button name="action_check" type="object" string="Check"/>
                </header>
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

    _toolbar = {
        action: [{ id: 2, name: "New Contract", res_model: "contract", type: "ir.actions.act_window" }],
        print: [],
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
                <field name="description"/>
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
                        <control>
                            <create string="Add a line"/>
                            <create string="Add a section" context="{'default_name': 'Section'}"/>
                        </control>
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
        id: 10,
        name: "Partner Cards",
        res_model: "partner",
        views: [
            [5, "kanban"],
            [false, "form"],
        ],
    },
]);


/**
 * @param {number} id
 * @param {string} fieldName
 * @param {string} content
 * @returns {TutorialStepDefinition}
 */
function getFieldStep(id, fieldName, content) {
    return getButtonStep(id, "field", fieldName, content);
}

/**
 * @param {number} id
 * @param {"generic_button"|"method"|"server_action"|"field"} type
 * @param {string} name
 * @param {string} content
 * @returns {TutorialStepDefinition}
 */
function getButtonStep(id, type, name, content) {
    return { action_name: "", content, hint: false, id, name, type };
}

/**
 * @param {string} model
 * @param {TutorialStepDefinition[]} steps
 * @param {Partial<TutorialChapterDefinition>} [values]
 * @returns {TutorialChapterDefinition} a form chapter, unless given another
 *   view type
 */
function getChapter(model, steps, values = {}) {
    return {
        context: {},
        id: steps[0].id,
        model,
        steps,
        view_type: "form",
        ...values,
    };
}

/**
 * The partner tutorial: create a partner from the list, fill its name and
 * email, and see where to check it.
 * @returns {TutorialChapterDefinition[]}
 */
function getPartnerChapters() {
    return [
        getChapter("partner", [getButtonStep(1, "generic_button", "New", "Create a partner")], {
            view_type: "list",
        }),
        getChapter("partner", [
            getFieldStep(2, "name", "Give it a name"),
            getFieldStep(3, "email", "Fill in the Email field."),
            { ...getButtonStep(4, "method", "action_check", "Here you can check it"), hint: true },
        ]),
    ];
}

/**
 * @returns {number[]} the ids of the steps of the tutorial, in order
 */
function getIds() {
    return chapters.flatMap((chapter) => chapter.steps.map((step) => step.id));
}

/**
 * Replaces the chapters of the tutorial
 * @param {TutorialChapterDefinition[]} newChapters
 */
function setChapters(newChapters) {
    chapters = newChapters;
}

/**
 * @param {...number} numbers the numbers of the steps the user did, from 1
 */
function setDone(...numbers) {
    doneNumbers = numbers;
}

/**
 * @param {number[]} ids
 * @returns {string} the numbers of the steps, e.g. "1,2"
 */
function toNumbers(ids) {
    return ids.map((id) => getIds().indexOf(id) + 1).join();
}

let chapters;
let doneNumbers;

/**
 * @returns {Object} the tutorial as returned by the server
 */
function getTutorial() {
    return {
        chapters,
        done_steps: doneNumbers.map((number) => getIds()[number - 1]),
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
    patchWithCleanup(pointerState, { trigger: undefined, content: "" });
    patchWithCleanup(session, {
        get running_tutorials() {
            return [getTutorial()];
        },
    });
    onRpc("has_group", () => true);
    onRpc("web_tutorial.tutorial", "mark_steps_done", ({ args }) => {
        expect.step(`mark_done ${toNumbers(args[1])}`);
        return true;
    });
    onRpc("web_tutorial.tutorial", "mark_steps_undone", ({ args }) => {
        expect.step(`mark_undone ${toNumbers(args[1])}`);
        return true;
    });
    onRpc("web_tutorial.tutorial", "mark_done", ({ args }) => {
        expect.step(`tutorial done ${args[0]}`);
        return true;
    });
});

test("the New button of a list is a step, opening the form of the next chapter", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    expect(".o_tutorial_progress").toHaveText("Step 1/4");
    expect(pointerState.trigger).toBe(queryOne(".o_list_button_add"));
    expect(".o_tutorial_next").toHaveCount(1);
    expect(".o_tutorial_skip").toHaveCount(1);

    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
    expect(".o_tutorial_progress").toHaveText("Step 2/4");
    expect(pointerState).toMatchObject({ chapterSizes: "1,3", stepIndex: 1 });
});

test("clicking the button of a step does it", async () => {
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Here you can check it");
    expect(pointerState.trigger).toBe(queryOne("button[name=action_check]"));
    await contains("button[name=action_check]").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("a generic button of the actions menu points the menu until open, then its item", async () => {
    chapters[1].steps[2] = getButtonStep(4, "generic_button", "Delete", "Delete it");
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Delete it");
    expect(pointerState.trigger).toBe(queryOne(".o_cp_action_menus button[data-hotkey='u']"));

    await contains(".o_cp_action_menus button[data-hotkey='u']").click();
    await waitUntil(() => pointerState.trigger?.matches(".o-dropdown-item"));
    expect(pointerState.trigger).toBe(queryOne(".o-dropdown-item:has([data-icon='delete'])"));
    expect.verifySteps([]);

    await contains(".o-dropdown-item:has([data-icon='delete'])").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("an item of another dropdown with the icon of a step of the actions menu doesn't do it", async () => {
    chapters[0].steps[0] = getButtonStep(1, "generic_button", "Delete", "Delete it");
    const listView = registry.category("views").get("list");
    class OtherDropdownListController extends listView.Controller {
        static components = { ...listView.Controller.components, Dropdown, DropdownItem };
    }
    registry.category("views").add("tuto_template_list", {
        ...listView,
        Controller: OtherDropdownListController,
        buttonTemplate: xml`
            <Dropdown>
                <button class="btn btn-secondary o_other_toggle">Other</button>
                <t t-set-slot="content">
                    <DropdownItem class="'o_other_delete'"><i data-icon="delete"/>Remove</DropdownItem>
                </t>
            </Dropdown>`,
    });
    await mountWebClient();
    await getService("action").doAction(7);
    await contains(".o_other_toggle").click();
    await contains(".o_other_delete").click();
    await animationFrame();
    expect.verifySteps([]);
});

test("Next clicked again while doing a step is ignored", async () => {
    chapters[1].steps[2] = getButtonStep(4, "generic_button", "Delete", "Delete it");
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Delete it");
    queryOne(".o_tutorial_next").click();
    queryOne(".o_tutorial_next").click();
    await waitFor(".modal");
    await animationFrame();
    expect(".o_cp_action_menus button[data-hotkey='u']").toHaveAttribute("aria-expanded", "false");
    expect.verifySteps(["tutorial done 1"]);
});

test("Next runs the server action of a step from the actions menu", async () => {
    chapters[1].steps[2] = {
        ...getButtonStep(4, "server_action", "partner.action_contract", "Make a contract"),
        action_name: "New Contract",
    };
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Make a contract");
    await contains(".o_tutorial_next").click();
    await waitFor(".modal .o_form_view");
    expect.verifySteps(["tutorial done 1"]);
});

test("Next does the step for the user", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view");
    await waitForPointer("Give it a name");
    expect.verifySteps(["mark_done 1"]);
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

test("a started chapter goes on in the form opened again, keeping its done steps", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_back_button, .breadcrumb-item a").click();
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 2", "mark_done 1"]);
});

test("a hint goes on with Next, and the tutorial is finished with its last view", async () => {
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitFor(".o_tutorial_pointer_content:contains(Here you can check it)");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["tutorial done 1"]);
    await waitFor(".o_reward_rainbow_man");
    await waitForNone(".o_tutorial_pointer_content");
});

test("the tooltip of the steps of a tutorial always showing it is open, without the ball", async () => {
    patchWithCleanup(session, {
        get running_tutorials() {
            return [{ ...getTutorial(), always_show_tooltip: true }];
        },
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitFor(".o_tutorial_pointer_content:contains(Give it a name)");
});

test("a tutorial switched to always show its tooltip shows it without reloading", async () => {
    onRpc("web_tutorial.tutorial", "web_save", () => [{ id: 1 }]);
    onRpc("web_tutorial.tutorial", "read", ({ args }) => {
        expect.step(`read ${args[0]}`);
        return [{ id: 1, always_show_tooltip: true }];
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitUntil(() => pointerState.content === "Create a partner");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(1);
    expect(".o_tutorial_pointer_content").toHaveCount(0);

    await getService("orm").webSave("web_tutorial.tutorial", [1], { always_show_tooltip: true });
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    expect.verifySteps(["read 1"]);
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
    setChapters([
        getChapter("partner", [
            getFieldStep(1, "name", "Give it a name"),
            getFieldStep(2, "email", "Fill in the Email field."),
        ]),
        getChapter("note", [
            getFieldStep(3, "name", "Name the note"),
            getFieldStep(4, "description", "Describe it"),
        ]),
    ]);
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps([]);

    await contains(".o_field_widget[name=email] input").click();
    expect.verifySteps(["mark_undone 3"]);
    await getService("action").doAction(4);
    await waitForPointer("Name the note");
});

test("no tutorial runs when none is started", async () => {
    patchWithCleanup(session, { running_tutorials: [] });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_list_view");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
});

test("a chapter with a context is only shown in the views with its values", async () => {
    chapters[0].context = { tutorial_ctx: "customer" };
    await mountWebClient();
    await getService("action").doAction(1, { additionalContext: { tutorial_ctx: "vendor" } });
    await waitFor(".o_list_view");
    await animationFrame();
    expect(pointerState.trigger).toBe(undefined);
    await getService("action").doAction(1, { additionalContext: { tutorial_ctx: "customer" } });
    await waitForPointer("Create a partner");
});

test("a dialog of another model isn't a view of the tutorial", async () => {
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
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(3);
    await waitForPointer("Give it a name");
    await contains(".modal .o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_done 2"]);
});

test("the pointer goes back to the last done step that can be done again", async () => {
    chapters[1].steps[1].name = "missing_field";
    chapters[1].steps[2].name = "missing_button";
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
    chapters[1].steps[2].name = "missing_button";
    setDone(1, 2, 3);
    const { promise, resolve } = Promise.withResolvers();
    onRpc("partner", "slow_method", () => promise);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Fill in the Email field.");
    getService("orm").call("partner", "slow_method", []);
    await waitForNone(".o_tutorial_pointer_content");
    resolve(true);
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps([]);
});

test("each save of the progress waits for the previous one, for the server to apply them in order", async () => {
    const { promise, resolve } = Promise.withResolvers();
    let previousSave = promise;
    onRpc("web_tutorial.tutorial", "mark_steps_done", async ({ args }) => {
        expect.step(`mark_done ${toNumbers(args[1])}`);
        await previousSave;
        previousSave = null;
        return true;
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_field_widget[name=email] input").click();
    await waitForPointer("Here you can check it");
    expect.verifySteps(["mark_done 2"]);
    resolve();
    await animationFrame();
    expect.verifySteps(["mark_done 3"]);
});

test("a failed save of the progress is ignored, the next ones going on", async () => {
    onRpc("web_tutorial.tutorial", "mark_steps_done", ({ args }) => {
        expect.step(`mark_done ${toNumbers(args[1])}`);
        if (toNumbers(args[1]) === "2") {
            throw new Error("Offline");
        }
        return true;
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_field_widget[name=email] input").click();
    await waitForPointer("Here you can check it");
    await animationFrame();
    expect.verifySteps(["mark_done 2", "mark_done 3"]);
    expect(".o_error_dialog").toHaveCount(0);
});

test("a field of the lines of a x2many field is done in its line", async () => {
    setChapters([
        getChapter("invoice", [
            getFieldStep(1, "line_ids", "Add your first line"),
            getFieldStep(2, "line_ids.label", "Describe what you sell"),
        ]),
    ]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(pointerState.trigger).toBe(queryOne(".o_field_x2many_list_row_add button:first-of-type"));

    await contains(".o_field_x2many_list_row_add button:first-of-type").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Describe what you sell");
    expect(pointerState.trigger).toBe(queryOne(".o_data_row [name=label] input"));

    await contains(".o_data_row [name=label] input").edit("Consulting");
    expect.verifySteps(["tutorial done 1"]);
});

test("only adding a line does the step of a x2many field, not a section", async () => {
    setChapters([getChapter("invoice", [getFieldStep(1, "line_ids", "Add your first line")])]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Add your first line");
    expect(pointerState.trigger).toBe(queryOne(".o_field_x2many_list_row_add button:first-of-type"));

    await contains(".o_field_widget[name=line_ids] th[data-name=name]").click();
    await animationFrame();
    expect.verifySteps([]);

    await contains(".o_field_x2many_list_row_add button:contains(Add a section)").click();
    await animationFrame();
    expect.verifySteps([]);

    await contains(".o_field_x2many_list_row_add button:first-of-type").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("an invalid field is pointed until filled in, to go on with the tutorial", async () => {
    setChapters([getChapter("invoice", [getFieldStep(1, "line_ids", "Add your first line")])]);
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
        getChapter("invoice", [
            getFieldStep(1, "line_ids", "Add your first line"),
            getFieldStep(2, "line_ids.label", "Describe what you sell"),
        ]),
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
    await getService("action").doAction(10);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(queryOne(".o_control_panel .o-kanban-button-new"));

    await contains(".o_control_panel .o-kanban-button-new").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
});

test("a kanban chapter is done in its quick create, until Edit opens its form", async () => {
    setChapters([
        getChapter(
            "partner",
            [
                getButtonStep(1, "generic_button", "New", "Create a partner"),
                getFieldStep(2, "display_name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            { view_type: "kanban" }
        ),
        getChapter("partner", [getFieldStep(4, "email", "Fill in the Email field.")]),
    ]);
    await mountWebClient();
    await getService("action").doAction(6);
    await waitForPointer("Create a partner");
    await contains(".o_control_panel .o-kanban-button-new").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Name it");
    const nameInput = queryOne(".o_kanban_quick_create .o_field_widget[name=display_name] input");
    expect(pointerState.trigger).toBe(nameInput);

    await contains(".o_tutorial_next").click();
    expect(nameInput).toBeFocused();
    expect.verifySteps(["mark_done 2"]);
    await contains(nameInput).edit("Alice", { confirm: false });
    await waitForPointer("Open its form");
    expect(pointerState.trigger).toBe(queryOne(".o_kanban_quick_create .o_kanban_edit"));

    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view:not(.o_kanban_quick_create_form)");
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 3"]);
});

test("the fields of a kanban chapter are the ones of its form when opened without quick create", async () => {
    setChapters([
        getChapter(
            "partner",
            [
                getButtonStep(1, "generic_button", "New", "Create a partner"),
                getFieldStep(2, "name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            { view_type: "kanban" }
        ),
        getChapter("partner", [getFieldStep(4, "email", "Fill in the Email field.")]),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitForPointer("Name it");
    expect(pointerState.trigger).toBe(queryOne(".o_field_widget[name=name] input"));
    expect(".o_tutorial_progress").toHaveText("Step 2/4");

    await contains(".o_field_widget[name=name] input").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 1", "mark_done 2"]);
});

test("a method of a kanban card is a step", async () => {
    setChapters([
        getChapter(
            "partner",
            [
                getButtonStep(1, "method", "action_check", "Check Bob"),
                getButtonStep(2, "generic_button", "New", "Create a partner"),
            ],
            { view_type: "kanban" }
        ),
        getChapter("partner", [getFieldStep(3, "name", "Give it a name")]),
    ]);
    await mountWebClient();
    await getService("action").doAction(10);
    await waitForPointer("Check Bob");
    expect(".o_tutorial_progress").toHaveText("Step 1/3");
    await contains(".o_kanban_record button[name=action_check]").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitForPointer("Give it a name");
    expect(".o_tutorial_progress").toHaveText("Step 3/3");
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

test("a New button opening a dropdown is done by opening it", async () => {
    defineTemplateListView();
    await mountWebClient();
    await getService("action").doAction(7);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await contains(".o_new_partner").click();
    await waitForPointer("Give it a name");
    expect.verifySteps(["mark_done 1"]);
});

test("Next picks the first item of the dropdown of a New button", async () => {
    defineTemplateListView();
    await mountWebClient();
    await getService("action").doAction(7);
    await waitForPointer("Create a partner");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_form_view");
    await waitForPointer("Give it a name");
    expect.verifySteps(["mark_done 1"]);
});

test("a field autofocused while a key is held isn't done", async () => {
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
    setChapters([getChapter("invoice", [getFieldStep(1, "name", "Name the invoice")])]);
    await mountWebClient();
    await getService("action").doAction(5);
    await waitForPointer("Name the invoice");
    await contains(".o_field_x2many_list_row_add button:first-of-type").click();
    await contains(".o_data_row [name=name] input").click();
    await animationFrame();
    expect.verifySteps([]);
    expect(pointerState.trigger).toBe(
        queryOne(".o_field_widget[name=name]:not(.o_data_row *) input")
    );
});

test("a disabled New button isn't pointed", async () => {
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

test("Next doesn't wait for the saves of the progress", async () => {
    onRpc("web_tutorial.tutorial", "mark_steps_done", () => new Promise(() => {}));
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    await contains(".o_tutorial_next").click();
    expect(".o_field_widget[name=name] input").toBeFocused();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_tutorial_next").click();
    expect(".o_field_widget[name=email] input").toBeFocused();
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
