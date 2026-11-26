import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    keyDown,
    keyUp,
    queryOne,
    runAllTimers,
    test,
    waitFor,
    waitForNone,
    waitUntil,
} from "@odoo/hoot";
import { xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    getService,
    models,
    mountWebClient,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { redirect } from "@web/core/utils/urls";
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
const ACTIONS = [
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
];
defineActions(ACTIONS);


/**
 * @param {number} id
 * @param {string} fieldName
 * @param {string} message
 * @returns {TutorialStepDefinition}
 */
function getFieldStep(id, fieldName, message) {
    return getButtonStep(id, "field", fieldName, message);
}

/**
 * @param {number} id
 * @param {"dialog"|"generic_button"|"menu_item"|"method"|"server_action"|"field"} type
 * @param {string} name
 * @param {string} message
 * @returns {TutorialStepDefinition}
 */
function getButtonStep(id, type, name, message) {
    return { action_name: "", id, menu_section: "", message, name, skippable: false, type };
}

/**
 * @param {number|false} actionId
 * @param {TutorialStepDefinition[]} steps
 * @param {string[]} [viewTypes]
 * @param {string} [resModel] the model of its views, the one of the action if
 *   any
 * @returns {TutorialStepDefinition[]} the steps, in the views of the action
 *   (its forms, unless given other view types)
 */
function getChapter(actionId, steps, viewTypes = ["form"], resModel) {
    const res_model = resModel || ACTIONS.find(({ id }) => id === actionId).res_model;
    return steps.map((step) => ({ ...step, action_id: actionId, res_model, view_types: viewTypes }));
}

/**
 * @param {number} actionId
 * @returns {TutorialStepDefinition[][]} the partner tutorial, in the views of
 *   the action
 */
function getPartnerChaptersOf(actionId) {
    return getPartnerChapters().map((steps) =>
        steps.map((step) => ({ ...step, action_id: actionId }))
    );
}

/**
 * The partner tutorial: create a partner from the list, fill its name and
 * email, and see where to check it.
 * @returns {TutorialStepDefinition[][]} its steps by chapter
 */
function getPartnerChapters() {
    return [
        getChapter(1, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(1, [
            getFieldStep(2, "name", "Give it a name"),
            getFieldStep(3, "email", "Fill in the Email field."),
            { ...getButtonStep(4, "method", "action_check", "Here you can check it"), skippable: true },
        ]),
    ];
}

/**
 * @returns {number[]} the ids of the steps of the tutorial, in order
 */
function getIds() {
    return chapters.flat().map((step) => step.id);
}

/**
 * Replaces the chapters of the tutorial
 * @param {TutorialStepDefinition[][]} newChapters the steps by chapter
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
/** @type {() => Object[]} the running tutorials of the lazy session */
let runningTutorials;

/**
 * @returns {Object} the tutorial as returned by the server
 */
function getTutorial() {
    return {
        done_steps: doneNumbers.map((number) => getIds()[number - 1]),
        id: 1,
        title: "Partners",
        end_message: "Well done\n<b>Partners</b>",
        steps: chapters.flat(),
    };
}

/**
 * Waits for the pointer to show the given content, then hovers its ball to
 * open its bubble
 * @param {string} content
 */
async function waitForPointer(content) {
    await waitUntil(() => pointerState.trigger && String(pointerState.content) === content);
    await animationFrame();
    await contains(".o_tutorial_pointer_tip").hover();
    await waitFor(`.o_tutorial_pointer_content:contains(${content})`);
}

beforeEach(() => {
    setChapters(getPartnerChapters());
    doneNumbers = [];
    patchWithCleanup(pointerState, { trigger: undefined, content: "" });
    runningTutorials = () => [getTutorial()];
    onRpc("lazy_session_info", () => ({ running_tutorials: runningTutorials() }));
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

test("the New button of a list is a step, opening the form of the next steps", async () => {
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

test("a form opened without New goes on with its fields, New only being of a list or kanban view", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    expect(pointerState.trigger).toBe(queryOne(".o_field_widget[name=name] input"));
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
    chapters[1][2] = {
        ...chapters[1][2],
        ...getButtonStep(4, "generic_button", "Delete", "Delete it"),
    };
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
    chapters[0][0] = {
        ...chapters[0][0],
        ...getButtonStep(1, "generic_button", "Delete", "Delete it"),
    };
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
    chapters[1][2] = {
        ...chapters[1][2],
        ...getButtonStep(4, "generic_button", "Delete", "Delete it"),
    };
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
    chapters[1][2] = {
        ...chapters[1][2],
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

/**
 * The partner tutorial going on with the cards of the partners, opened from
 * their menu in the Configuration section of the navbar
 */
function setMenuChapters() {
    defineMenus([
        {
            id: 1,
            name: "Partners",
            children: [
                {
                    id: 2,
                    name: "Configuration",
                    xmlid: "partner.menu_config",
                    children: [{ id: 3, name: "Cards", xmlid: "partner.menu_cards", actionID: 10 }],
                },
            ],
        },
    ]);
    setChapters([
        getChapter(
            1,
            [
                {
                    ...getButtonStep(1, "menu_item", "partner.menu_cards", "Open the cards"),
                    menu_section: "partner.menu_config",
                },
            ],
            ["list", "kanban"]
        ),
        getChapter(10, [getButtonStep(2, "generic_button", "New", "Create a card")], ["list", "kanban"]),
    ]);
}

test("a menu of the navbar is a step, its section pointed until open", async () => {
    setMenuChapters();
    await mountWebClient();
    getService("menu").setCurrentMenu(1);
    await getService("action").doAction(1);
    await waitForPointer("Open the cards");
    const section = ".o_menu_sections button[data-menu-xmlid='partner.menu_config']";
    expect(pointerState.trigger).toBe(queryOne(section));
    await contains(section).click();
    const menu = ".o-dropdown--menu a[data-menu-xmlid='partner.menu_cards']";
    await waitUntil(() => pointerState.trigger === queryOne(menu));
    expect.verifySteps([]);
    await contains(menu).click();
    await waitForPointer("Create a card");
    expect.verifySteps(["mark_done 1"]);
});

test("Next opens the section of the navbar and clicks the menu of the step", async () => {
    setMenuChapters();
    await mountWebClient();
    getService("menu").setCurrentMenu(1);
    await getService("action").doAction(1);
    await waitForPointer("Open the cards");
    await contains(".o_tutorial_next").click();
    await waitFor(".o_kanban_view");
    await waitForPointer("Create a card");
    expect.verifySteps(["mark_done 1"]);
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
    expect(String(pointerState.content)).toBe("Give it a name");
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

test("a skippable step goes on with Next, and the tutorial is finished with its last view", async () => {
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitFor(".o_tutorial_pointer_content:contains(Here you can check it)");
    await contains(".o_tutorial_next").click();
    expect.verifySteps(["tutorial done 1"]);
    await waitFor(".o_reward_rainbow_man");
    expect(".o_reward_msg_content br").toHaveCount(1);
    expect(".o_reward_msg_content b").toHaveCount(0);
    await waitForNone(".o_tutorial_pointer_content");
});

test("the message ending a tutorial on a field stays shown after the click focusing it", async () => {
    setChapters(getPartnerChapters().map((steps) => steps.filter((step) => step.type !== "method")));
    setDone(1, 2);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Fill in the Email field.");
    await contains(".o_field_widget[name=email] input").click();
    expect.verifySteps(["tutorial done 1"]);
    await runAllTimers();
    await waitFor(".o_reward_msg_container");
    await animationFrame();
    expect(".o_reward_msg_container").toHaveCount(1);
});

test("a dialog step shows its message in the middle of the screen, going on with Next", async () => {
    setChapters([
        getChapter(1, [
            getButtonStep(1, "dialog", "", "<h3 class='o_test_welcome'>Welcome aboard</h3>"),
            getFieldStep(2, "name", "Give it a name"),
        ]),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitFor(".o_tutorial_centered .o_test_welcome:contains(Welcome aboard)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    expect(".o_tutorial_centered .o_tutorial_progress").toHaveText("Step 1/2");

    await contains(".o_tutorial_centered .o_tutorial_next").click();
    await waitForPointer("Give it a name");
    expect(".o_tutorial_centered").toHaveCount(0);
    expect.verifySteps(["mark_done 1"]);
});

test("a dialog step goes on with the step of its chapter in the same view", async () => {
    setChapters([
        getChapter(
            6,
            [
                getButtonStep(1, "dialog", "", "<h3>Welcome aboard</h3>"),
                getButtonStep(2, "generic_button", "New", "Create a partner"),
            ],
            ["list", "kanban"]
        ),
    ]);
    await mountWebClient();
    await getService("action").doAction(6);
    await waitFor(".o_tutorial_centered h3:contains(Welcome aboard)");
    await contains(".o_tutorial_centered .o_tutorial_next").click();
    await waitForPointer("Create a partner");
    expect.verifySteps(["mark_done 1"]);
});

test("a done chapter of all views goes on with the next chapter shown in the same view", async () => {
    setChapters([
        getChapter(
            6,
            [getButtonStep(1, "dialog", "", "<h3>Welcome aboard</h3>")],
            []
        ),
        getChapter(6, [getButtonStep(2, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
    ]);
    await mountWebClient();
    await getService("action").doAction(6);
    await waitFor(".o_tutorial_centered h3:contains(Welcome aboard)");
    await contains(".o_tutorial_centered .o_tutorial_next").click();
    await waitForPointer("Create a partner");
    expect.verifySteps(["mark_done 1"]);
});

test("a done chapter doesn't go on with a later chapter shown in the same view, but not right after it", async () => {
    setChapters([
        getChapter(1, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(1, [getFieldStep(2, "name", "Give it a name")]),
        getChapter(1, [getButtonStep(3, "generic_button", "New", "Create another one")], ["list", "kanban"]),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    expect.verifySteps(["mark_done 1"]);
    await contains(".breadcrumb-item a").click();
    await waitFor(".o_list_view");
    await waitForPointer("Create a partner");
});

test("a done dialog step isn't shown again when going back to its chapter", async () => {
    setChapters([
        getChapter(1, [getButtonStep(1, "dialog", "", "<h3>Welcome aboard</h3>")], []),
        getChapter(1, [getFieldStep(2, "name", "Give it a name")]),
        getChapter(4, [getFieldStep(3, "description", "Describe it")]),
    ]);
    setDone(1, 2);
    await mountWebClient();
    await getService("action").doAction(4);
    await waitForPointer("Describe it");
    await getService("action").doAction(1);
    await waitFor(".o_list_view");
    await animationFrame();
    expect(".o_tutorial_centered").toHaveCount(0);
});

test("the tooltip of the steps of a tutorial expanding its messages is open, without the ball", async () => {
    runningTutorials = () => [{ ...getTutorial(), expand_messages: true }];
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
    await contains(".o_list_button_add").click();
    expect.verifySteps(["mark_done 1"]);
    await waitFor(".o_tutorial_pointer_content:contains(Give it a name)");
});

test("a tutorial switched to expand its messages shows them without reloading", async () => {
    onRpc("web_tutorial.tutorial", "web_save", () => [{ id: 1 }]);
    onRpc("web_tutorial.tutorial", "read", ({ args }) => {
        expect.step(`read ${args[0]}`);
        return [{ id: 1, expand_messages: true }];
    });
    await mountWebClient();
    await getService("action").doAction(1);
    await waitUntil(() => String(pointerState.content) === "Create a partner");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(1);
    expect(".o_tutorial_pointer_content").toHaveCount(0);

    await getService("orm").webSave("web_tutorial.tutorial", [1], { expand_messages: true });
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
        getChapter(1, [
            getFieldStep(1, "name", "Give it a name"),
            getFieldStep(2, "email", "Fill in the Email field."),
        ]),
        getChapter(4, [
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
    runningTutorials = () => [];
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_list_view");
    await animationFrame();
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
});

test("a link with a tutorial key starts it, the key leaving the URL", async () => {
    runningTutorials = () => [];
    redirect("/odoo/action-1?tutorial=partner_tutorial");
    onRpc("web_tutorial.tutorial", "start_from_key", ({ args }) => {
        expect.step(`start ${args.join(" ")}`);
        return false;
    });
    await mountWebClient();
    await waitFor(".o_list_view");
    expect.verifySteps(["start partner_tutorial false"]);
    await animationFrame();
    expect(location.search).not.toInclude("tutorial");
});

test("starting a tutorial runs it without reloading, on its action in the app of its menu", async () => {
    runningTutorials = () => [];
    patchWithCleanup(location, { reload: () => expect.step("reload") });
    defineMenus([{ id: 7, name: "Partners", actionID: 1 }]);
    await mountWebClient();
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "web_tutorial.start",
        params: { action_id: 1, menu_id: 7, running_tutorials: [getTutorial()] },
    });
    await waitForPointer("Create a partner");
    expect(".o_list_view").toHaveCount(1);
    expect(getService("menu").getCurrentApp().id).toBe(7);
    expect.verifySteps([]);
});

test("a link can start a tutorial with the tooltips of its steps open", async () => {
    runningTutorials = () => [];
    redirect("/odoo/action-1?tutorial=partner_tutorial&expand_messages=1");
    onRpc("web_tutorial.tutorial", "start_from_key", ({ args }) => {
        expect.step(`start ${args.join(" ")}`);
        return false;
    });
    await mountWebClient();
    await waitFor(".o_list_view");
    expect.verifySteps(["start partner_tutorial true"]);
});

test("the tooltips of the steps are open for a user who opened them from a link", async () => {
    runningTutorials = () => [{ ...getTutorial(), user_expand_messages: true }];
    await mountWebClient();
    await getService("action").doAction(1);
    await waitFor(".o_tutorial_pointer_content:contains(Create a partner)");
    expect(".o_tutorial_pointer_tip").toHaveCount(0);
});

test("a chapter of an action is only shown in the views of this action", async () => {
    await mountWebClient();
    await getService("action").doAction(9);
    await waitFor(".o_list_view");
    await animationFrame();
    expect(pointerState.trigger).toBe(undefined);

    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitForPointer("Give it a name");
    expect.verifySteps(["mark_done 1"]);
});

test("a dialog of another action isn't a view of the tutorial", async () => {
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(2);
    await waitFor(".modal .o_form_view");
    await waitUntil(() => !pointerState.trigger);
    await contains(".modal .o_field_widget[name=name] input").click();
    await animationFrame();
    expect.verifySteps([]);
});

test("a dialog of the action of a chapter is a view of it", async () => {
    setChapters([
        getChapter(1, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(3, [getFieldStep(2, "name", "Give it a name")]),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await getService("action").doAction(3);
    await waitForPointer("Give it a name");
    await contains(".modal .o_field_widget[name=name] input").click();
    expect.verifySteps(["tutorial done 1"]);
});

test("the pointer goes back to the last done step that can be done again", async () => {
    chapters[1][1].name = "missing_field";
    chapters[1][2].name = "missing_button";
    setDone(1, 2, 3);
    await mountWebClient();
    await getService("action").doAction(1);
    await contains(".o_data_row .o_data_cell").click();
    await waitForPointer("Give it a name");
    await contains(".o_field_widget[name=name] input").click();
    expect.verifySteps(["mark_undone 3"]);
    await animationFrame();
    expect(String(pointerState.content)).toBe("Give it a name");
});

test("the pointer doesn't go back while an RPC is pending", async () => {
    chapters[1][2].name = "missing_button";
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
        getChapter(5, [
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
    setChapters([getChapter(5, [getFieldStep(1, "line_ids", "Add your first line")])]);
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
    setChapters([getChapter(5, [getFieldStep(1, "line_ids", "Add your first line")])]);
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
        getChapter(5, [
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

test("a chapter of several records is shown in the list and kanban views of its action", async () => {
    setChapters(getPartnerChaptersOf(10));
    await mountWebClient();
    await getService("action").doAction(10);
    await waitForPointer("Create a partner");
    expect(pointerState.trigger).toBe(queryOne(".o_control_panel .o-kanban-button-new"));

    await contains(".o_control_panel .o-kanban-button-new").click();
    expect.verifySteps(["mark_done 1"]);
    await waitForPointer("Give it a name");
});

test("a chapter without action is shown in the views of its model", async () => {
    setChapters([
        getChapter(1, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(false, [getFieldStep(2, "email", "Fill in the Email field.")], ["form"], "partner"),
    ]);
    await mountWebClient();
    await getService("action").doAction(10);
    await contains(".o_control_panel .o-kanban-button-new").click();
    await waitForPointer("Fill in the Email field.");
    expect(pointerState.trigger).toBe(queryOne(".o_field_widget[name=email] input"));
});

test("a chapter without view types is shown in all the views of its action", async () => {
    setChapters([
        getChapter(
            1,
            [
                getButtonStep(1, "generic_button", "New", "Create a partner"),
                getFieldStep(2, "email", "Fill in the Email field."),
            ],
            []
        ),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitForPointer("Fill in the Email field.");
    expect.verifySteps(["mark_done 1"]);
});

test("a kanban chapter is done in its quick create, until Edit opens its form", async () => {
    setChapters([
        getChapter(
            6,
            [
                getButtonStep(1, "generic_button", "New", "Create a partner"),
                getFieldStep(2, "display_name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            ["list", "kanban"]
        ),
        getChapter(6, [getFieldStep(4, "email", "Fill in the Email field.")]),
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

test("the steps without action join the chapter of the same model and views before them", async () => {
    setChapters([
        getChapter(6, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(
            false,
            [
                getFieldStep(2, "display_name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            ["list", "kanban"],
            "partner"
        ),
        getChapter(false, [getFieldStep(4, "email", "Fill in the Email field.")], ["form"], "partner"),
    ]);
    await mountWebClient();
    await getService("action").doAction(6);
    await waitForPointer("Create a partner");
    await contains(".o_control_panel .o-kanban-button-new").click();
    await waitForPointer("Name it");
    expect(pointerState.trigger).toBe(
        queryOne(".o_kanban_quick_create .o_field_widget[name=display_name] input")
    );
    expect.verifySteps(["mark_done 1"]);

    await contains(".o_tutorial_next").click();
    await waitForPointer("Open its form");
    expect.verifySteps(["mark_done 2"]);
    await contains(".o_kanban_renderer").click();
    await waitFor(".o_kanban_view:not(:has(.o_kanban_quick_create))");
    await waitForPointer("Create a partner");
});

test("the fields of a kanban chapter are the ones of its form without action when opened without quick create", async () => {
    setChapters([
        getChapter(1, [getButtonStep(1, "generic_button", "New", "Create a partner")], ["list", "kanban"]),
        getChapter(
            false,
            [
                getFieldStep(2, "name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            ["list", "kanban"],
            "partner"
        ),
        getChapter(false, [getFieldStep(4, "email", "Fill in the Email field.")], ["form"], "partner"),
    ]);
    await mountWebClient();
    await getService("action").doAction(1);
    await waitForPointer("Create a partner");
    await contains(".o_list_button_add").click();
    await waitForPointer("Name it");
    expect(".o_tutorial_progress").toHaveText("Step 2/4");
    expect.verifySteps(["mark_done 1"]);
});

test("the fields of a kanban chapter are the ones of its form when opened without quick create", async () => {
    setChapters([
        getChapter(
            1,
            [
                getButtonStep(1, "generic_button", "New", "Create a partner"),
                getFieldStep(2, "name", "Name it"),
                getButtonStep(3, "generic_button", "Edit", "Open its form"),
            ],
            ["list", "kanban"]
        ),
        getChapter(1, [getFieldStep(4, "email", "Fill in the Email field.")]),
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
            10,
            [
                getButtonStep(1, "method", "action_check", "Check Bob"),
                getButtonStep(2, "generic_button", "New", "Create a partner"),
            ],
            ["list", "kanban"]
        ),
        getChapter(10, [getFieldStep(3, "name", "Give it a name")]),
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
    setChapters(getPartnerChaptersOf(7));
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
    setChapters(getPartnerChaptersOf(7));
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
    setChapters([getChapter(5, [getFieldStep(1, "name", "Name the invoice")])]);
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
