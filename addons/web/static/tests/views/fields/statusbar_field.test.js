import { expect, test } from "@odoo/hoot";
import {
    click,
    Deferred,
    edit,
    press,
    queryAll,
    queryAllTexts,
    queryAttribute,
    queryFirst,
} from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    contains,
    clickSave,
    defineActions,
    defineModels,
    fields,
    getDropdownMenu,
    getService,
    models,
    mockService,
    mountView,
    mountWithCleanup,
    onRpc,
    serverState,
    pagerNext,
    pagerPrevious,
} from "@web/../tests/web_test_helpers";
import { EventBus } from "@odoo/owl";
import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean({ default: true });
    int_field = fields.Integer();
    qux = fields.Float({ digits: [16, 1] });
    p = fields.One2many({
        relation: "partner",
        relation_field: "trululu",
    });
    trululu = fields.Many2one({ relation: "partner" });
    product_id = fields.Many2one({ relation: "product" });
    color = fields.Selection({
        selection: [
            ["red", "Red"],
            ["black", "Black"],
        ],
        default: "red",
    });
    user_id = fields.Many2one({ relation: "users" });

    _records = [
        {
            id: 1,
            name: "first record",
            bar: true,
            foo: "yop",
            int_field: 10,
            qux: 0.44,
            p: [],
            trululu: 4,
            user_id: 17,
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            qux: 13,
            p: [],
            trululu: 1,
            product_id: 37,
            user_id: 17,
        },
        { id: 4, name: "aaa", bar: false },
    ];
}

class Product extends models.Model {
    name = fields.Char();

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

class Users extends models.Model {
    name = fields.Char();
    partner_ids = fields.One2many({
        relation: "partner",
        relation_field: "user_id",
    });

    _records = [
        { id: 17, name: "Aline", partner_ids: [1, 2] },
        { id: 19, name: "Christine" },
    ];
}

defineModels([Partner, Product, Users]);

test("static statusbar widget on many2one field", async () => {
    Partner._fields.trululu = fields.Many2one({
        relation: "partner",
        domain: "[('bar', '=', True)]",
    });
    Partner._records[1].bar = false;

    onRpc("search_read", ({ kwargs }) => expect.step(kwargs.fields.toString()));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" />
                </header>
            </form>
        `,
    });
    // search_read should only fetch field display_name
    expect.verifySteps(["display_name"]);
    expect(".o_statusbar_status button:not(.dropdown-toggle)").toHaveCount(2);
    expect(".o_statusbar_status button:disabled").toHaveCount(5);
    expect('.o_statusbar_status button[data-value="4"]').toHaveClass("o_arrow_button_current");
});

test("folded statusbar widget on selection field has selected value in the toggler", async () => {
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: true,
        });
        return {
            bus: new EventBus(),
            size: 0,
            isSmall: true,
        };
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="color" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status button.dropdown-toggle:contains(Red)").toHaveCount(1);
});

test("static statusbar widget on many2one field with domain", async () => {
    expect.assertions(1);

    serverState.userId = 17;

    onRpc("search_read", ({ kwargs }) => {
        expect(kwargs.domain).toEqual(["|", ["id", "=", 4], ["user_id", "=", 17]], {
            message: "search_read should sent the correct domain",
        });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" domain="[('user_id', '=', uid)]" />
                </header>
            </form>
        `,
    });
});

test("clickable statusbar widget on many2one field", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': 1}" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status button[data-value='4']").toHaveClass("o_arrow_button_current");
    expect(".o_statusbar_status button[data-value='4']").not.toBeEnabled();

    expect(
        ".o_statusbar_status button.btn:not(.dropdown-toggle):not(:disabled):not(.o_arrow_button_current)"
    ).toHaveCount(2);

    await click(
        ".o_statusbar_status button.btn:not(.dropdown-toggle):not(:disabled):not(.o_arrow_button_current):eq(1)"
    );
    await animationFrame();

    expect(".o_statusbar_status button[data-value='1']").toHaveClass("o_arrow_button_current");
    expect(".o_statusbar_status button[data-value='1']").not.toBeEnabled();
});

test("statusbar with no status", async () => {
    Partner._records[1].product_id = false;
    Product._records = [];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status").not.toHaveClass("o_field_empty");
    expect(".o_statusbar_status > :not(.d-none)").toHaveCount(0, {
        message: "statusbar widget should be empty",
    });
});

test("statusbar with tooltip for help text", async () => {
    Partner._fields.product_id = fields.Many2one({
        relation: "product",
        help: "some info about the field",
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status").not.toHaveClass("o_field_empty");
    expect(".o_field_statusbar").toHaveAttribute("data-tooltip-info");
    const tooltipInfo = JSON.parse(queryAttribute(".o_field_statusbar", "data-tooltip-info"));
    expect(tooltipInfo.field.help).toBe("some info about the field", {
        message: "tooltip text is present on the field",
    });
});

test("statusbar with required modifier", async () => {
    mockService("notification", {
        add() {
            expect.step("Show error message");
            return () => {};
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" required="1"/>
                </header>
            </form>
        `,
    });

    await click(".o_form_button_save");
    await animationFrame();

    expect(".o_form_editable").toHaveCount(1, { message: "view should still be in edit" });
    // should display an 'invalid fields' notificationaveCount(1, { message: "view should still be in edit" });
    expect.verifySteps(["Show error message"]);
});

test.tags("desktop");
test("statusbar with no value in readonly on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status").not.toHaveClass("o_field_empty");
    expect(".o_statusbar_status button:visible").toHaveCount(2);
});

test.tags("mobile");
test("statusbar with no value in readonly on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status").not.toHaveClass("o_field_empty");
    expect(".o_statusbar_status .dropdown-toggle:visible").toHaveCount(1);
});

test("statusbar with domain but no value (create mode)", async () => {
    Partner._fields.trululu = fields.Many2one({
        relation: "partner",
        domain: "[('bar', '=', True)]",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status button:disabled").toHaveCount(5);
});

test("clickable statusbar should change m2o fetching domain in edit mode", async () => {
    Partner._fields.trululu = fields.Many2one({
        relation: "partner",
        domain: "[('bar', '=', True)]",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': 1}" />
                </header>
            </form>
        `,
    });

    expect(".o_statusbar_status button:not(.dropdown-toggle)").toHaveCount(3);
    await click(".o_statusbar_status button:not(.dropdown-toggle):eq(-1)");
    await animationFrame();
    expect(".o_statusbar_status button:not(.dropdown-toggle)").toHaveCount(2);
});

test.tags("desktop");
test("statusbar fold_field option and statusbar_visible attribute on desktop", async () => {
    Partner._records[0].bar = false;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'fold_field': 'bar'}" />
                    <field name="color" widget="statusbar" statusbar_visible="red" />
                </header>
            </form>
        `,
    });

    await click(".o_statusbar_status .dropdown-toggle:not(.d-none)");
    await animationFrame();

    expect(".o_statusbar_status:first button:visible").toHaveCount(3);
    expect(".o_statusbar_status:last button:visible").toHaveCount(1);
    expect(".o_statusbar_status button").not.toBeEnabled({
        message: "no status bar buttons should be enabled",
    });
});

test.tags("mobile");
test("statusbar fold_field option and statusbar_visible attribute on mobile", async () => {
    Partner._records[0].bar = false;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'fold_field': 'bar'}" />
                    <field name="color" widget="statusbar" statusbar_visible="red" />
                </header>
            </form>
        `,
    });

    await click(".o_statusbar_status .dropdown-toggle:not(.d-none)");
    await animationFrame();

    expect(".o_statusbar_status:first .dropdown-toggle:visible").toHaveCount(1);
    expect(".o_statusbar_status:last .dropdown-toggle:visible").toHaveCount(1);
    expect(".o_statusbar_status button").not.toBeEnabled({
        message: "no status bar buttons should be enabled",
    });
});

test.tags("desktop");
test("statusbar: choose an item from the folded menu on desktop", async () => {
    Partner._records[0].bar = false;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': '1', 'fold_field': 'bar'}" />
                </header>
            </form>
        `,
    });

    expect("[aria-checked='true']").toHaveText("aaa", {
        message: "default status is 'aaa'",
    });

    expect(".o_statusbar_status .dropdown-toggle.o_arrow_button").toHaveText("...", {
        message: "button has the correct text",
    });

    await click(".o_statusbar_status .dropdown-toggle:not(.d-none)");
    await animationFrame();
    await click(".o-dropdown--menu .dropdown-item");
    await animationFrame();

    expect("[aria-checked='true']").toHaveText("second record", {
        message: "status has changed to the selected dropdown item",
    });
});

test.tags("mobile");
test("statusbar: choose an item from the folded menu on mobile", async () => {
    Partner._records[0].bar = false;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': '1', 'fold_field': 'bar'}" />
                </header>
            </form>
        `,
    });

    expect("[aria-checked='true']").toHaveText("aaa", {
        message: "default status is 'aaa'",
    });

    expect(".o_statusbar_status .dropdown-toggle:visible").toHaveText("aaa", {
        message: "button has the correct text",
    });

    await click(".o_statusbar_status .dropdown-toggle:not(.d-none)");
    await animationFrame();
    await click(".o-dropdown--menu .dropdown-item:nth-child(2)");
    await animationFrame();

    expect("[aria-checked='true']").toHaveText("second record", {
        message: "status has changed to the selected dropdown item",
    });
});

test("statusbar with dynamic domain", async () => {
    Partner._fields.trululu = fields.Many2one({
        relation: "partner",
        domain: "[('int_field', '>', qux)]",
    });
    Partner._records[2].int_field = 0;
    onRpc("search_read", () => {
        rpcCount++;
    });
    let rpcCount = 0;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" />
                </header>
                <field name="qux" />
                <field name="foo" />
            </form>
        `,
    });

    expect(".o_statusbar_status button:disabled").toHaveCount(6);
    expect(rpcCount).toBe(1, { message: "should have done 1 search_read rpc" });
    await click(".o_field_widget[name='qux'] input");
    await edit(9.5, { confirm: "enter" });
    await runAllTimers();
    await animationFrame();
    expect(".o_statusbar_status button:disabled").toHaveCount(5);
    expect(rpcCount).toBe(2, { message: "should have done 1 more search_read rpc" });
    await edit("hey", { confirm: "enter" });
    await animationFrame();
    expect(rpcCount).toBe(2, { message: "should not have done 1 more search_read rpc" });
});

test(`statusbar edited by the smart action "Move to stage..."`, async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': '1'}"/>
                </header>
            </form>
        `,
        resId: 1,
    });

    expect(".o_field_widget").toHaveCount(1);

    await press(["control", "k"]);
    await animationFrame();
    await click(`.o_command:contains("Move to Trululu")`);
    await animationFrame();
    expect(queryAllTexts(".o_command")).toEqual(["first record", "second record", "aaa"]);
    await click("#o_command_2");
    await animationFrame();
});

test("smart actions are unavailable if readonly", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" readonly="1"/>
                </header>
            </form>
        `,
        resId: 1,
    });

    expect(".o_field_widget").toHaveCount(1);
    await press(["control", "k"]);
    await animationFrame();
    const moveStages = queryAllTexts(".o_command");
    expect(moveStages).not.toInclude("Move to Trululu\nALT + SHIFT + X");
    expect(moveStages).not.toInclude("Move to next\nALT + X");
});

test("hotkeys are unavailable if readonly", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" readonly="1"/>
                </header>
            </form>
        `,
        resId: 1,
    });

    expect(".o_field_widget").toHaveCount(1);
    await press(["alt", "shift", "x"]); // Move to stage...
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "command palette should not open" });

    await press(["alt", "x"]); // Move to next
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "command palette should not open" });
});

test("auto save record when field toggled", async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': 1}" />
                </header>
            </form>
        `,
    });

    await click(
        ".o_statusbar_status button.btn:not(.dropdown-toggle):not(:disabled):not(.o_arrow_button_current):eq(-1)"
    );
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test("For the same record, a single rpc is done to recover the specialData", async () => {
    Partner._views = {
        "list,3": '<list><field name="display_name"/></list>',
        "search,9": `<search></search>`,
        form: `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" readonly="1"/>
                </header>
            </form>
        `,
    };
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
    ]);
    onRpc("has_group", () => true);
    onRpc("search_read", () => expect.step("search_read"));

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect.verifySteps(["search_read"]);

    await click(".o_back_button");
    await animationFrame();
    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect.verifySteps([]);
});

test("open form with statusbar, leave and come back to another one with other domain", async () => {
    Partner._views = {
        "list,3": '<list><field name="display_name"/></list>',
        "search,9": `<search/>`,
        form: `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" domain="[['id', '>', id]]" readonly="1"/>
                </header>
            </form>
        `,
    };
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
    ]);
    onRpc("has_group", () => true);
    onRpc("search_read", () => expect.step("search_read"));

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // open first record
    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect.verifySteps(["search_read"]);

    // go back and open second record
    await click(".o_back_button");
    await animationFrame();
    await click(".o_data_row:eq(1) .o_data_cell");
    await animationFrame();
    expect.verifySteps(["search_read"]);
});

test.tags("desktop");
test("clickable statusbar with readonly modifier set to false is editable on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': true}" readonly="False"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status button:visible").toHaveCount(2);
    expect(".o_statusbar_status button[disabled][aria-checked='false']:visible").toHaveCount(0);
});

test.tags("mobile");
test("clickable statusbar with readonly modifier set to false is editable on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': true}" readonly="False"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status .dropdown-toggle:visible").toHaveCount(1);
    expect(".o_statusbar_status button[disabled][aria-checked='false']:visible").toHaveCount(0);
    await click(".o_statusbar_status .dropdown-toggle:visible");
    await animationFrame();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(2);
});

test.tags("desktop");
test("clickable statusbar with readonly modifier set to true is not editable on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': true}" readonly="True"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status button[disabled]:visible").toHaveCount(2);
});

test.tags("mobile");
test("clickable statusbar with readonly modifier set to true is not editable on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': true}" readonly="True"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status .dropdown-toggle[disabled]:visible").toHaveCount(1);
});

test.tags("desktop");
test("non-clickable statusbar with readonly modifier set to false is not editable on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': false}" readonly="False"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status button[disabled]:visible").toHaveCount(2);
});

test.tags("mobile");
test("non-clickable statusbar with readonly modifier set to false is not editable on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" options="{'clickable': false}" readonly="False"/>
                </header>
            </form>
        `,
    });
    expect(".o_statusbar_status .dropdown-toggle[disabled]:visible").toHaveCount(1);
});

test.tags("desktop");
test("last status bar button have a border radius (no arrow shape) on the right side when a prior folded stage gets selected", async () => {
    class Stage extends models.Model {
        name = fields.Char();
        folded = fields.Boolean({ default: false });

        _records = [
            { id: 1, name: "New" },
            { id: 2, name: "In Progress", folded: true },
            { id: 3, name: "Done" },
        ];
    }

    class Task extends models.Model {
        status = fields.Many2one({ relation: "stage" });

        _records = [
            { id: 1, status: 1 },
            { id: 2, status: 2 },
            { id: 3, status: 3 },
        ];
    }

    defineModels([Stage, Task]);

    await mountView({
        type: "form",
        resModel: "task",
        resId: 3,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="status" widget="statusbar" options="{'clickable': true, 'fold_field': 'folded'}" />
                </header>
            </form>
        `,
    });
    await click(".o_statusbar_status .dropdown-toggle:not(.d-none)");
    await animationFrame();
    await click(
        queryFirst(".dropdown-item", {
            root: getDropdownMenu(".o_statusbar_status .dropdown-toggle:not(.d-none)"),
        })
    );
    await animationFrame();

    expect(".o_statusbar_status button[data-value='3']").not.toHaveStyle({
        borderTopRightRadius: "0px",
    });
    expect(".o_statusbar_status button[data-value='3']").toHaveClass("o_first");
});

test.tags("desktop");
test("correctly load statusbar when dynamic domain changes", async () => {
    class Stage extends models.Model {
        name = fields.Char();
        folded = fields.Boolean({ default: false });
        project_ids = fields.Many2many({ relation: "project" });

        _records = [
            { id: 1, name: "Stage Project 1", project_ids: [1] },
            { id: 2, name: "Stage Project 2", project_ids: [2] },
        ];
    }

    class Project extends models.Model {
        display_name = fields.Char();

        _records = [
            { id: 1, display_name: "Project 1" },
            { id: 2, display_name: "Project 2" },
        ];
    }

    class Task extends models.Model {
        status = fields.Many2one({ relation: "stage" });
        project_id = fields.Many2one({ relation: "project" });

        _records = [{ id: 1, project_id: 1, status: 1 }];
    }
    Task._onChanges.project_id = (obj) => {
        obj.status = obj.project_id === 1 ? 1 : 2;
    };

    defineModels([Stage, Project, Task]);

    onRpc("search_read", ({ kwargs }) => expect.step(kwargs.domain));
    await mountView({
        type: "form",
        resModel: "task",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="status" widget="statusbar" domain="[('project_ids', 'in', project_id)]" />
                </header>
                <field name="project_id"/>
            </form>
        `,
    });
    expect(queryAllTexts(".o_statusbar_status button:not(.d-none)")).toEqual(["Stage Project 1"]);
    expect.verifySteps([["|", ["id", "=", 1], ["project_ids", "in", 1]]]);
    await click(`[name="project_id"] .dropdown input`);
    await animationFrame();
    await click(`[name="project_id"] .dropdown .dropdown-menu .ui-menu-item:contains("Project 2")`);
    await animationFrame();

    expect(queryAllTexts(".o_statusbar_status button:not(.d-none)")).toEqual(["Stage Project 2"]);
    expect.verifySteps([["|", ["id", "=", 2], ["project_ids", "in", 2]]]);
    await clickSave();
    expect(queryAllTexts(".o_statusbar_status button:not(.d-none)")).toEqual(["Stage Project 2"]);
    expect.verifySteps([]);
});

test.tags("mobile");
test("statusbar is rendered correctly on small devices", async () => {
    Partner._records = [
        { id: 1, name: "first record", trululu: 4 },
        { id: 2, name: "second record", trululu: 1 },
        { id: 3, name: "third record" },
        { id: 4, name: "aaa" },
    ];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" options="{'clickable': 1}" />
                </header>
                <field name="name" />
            </form>
        `,
    });
    expect(
        queryAll(".o_statusbar_status .o_arrow_button.dropdown-toggle", { visible: true })
    ).toHaveCount(1);
    expect(".o_statusbar_status .o_arrow_button.o_first:visible").toHaveCount(1);
    expect(".o-dropdown--menu").toHaveCount(0, { message: "dropdown should be hidden" });
    expect(".o_statusbar_status button.dropdown-toggle:visible").toHaveText("aaa");

    // open the dropdown
    await contains(".o_statusbar_status .dropdown-toggle").click();

    expect(".o-dropdown--menu").toHaveCount(1, { message: "dropdown should be visible" });
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(4);
});

test.tags("mobile");
test("statusbar with no status on extra small screens", async () => {
    Partner._records = [
        { id: 1, name: "first record", trululu: 4 },
        { id: 2, name: "second record", trululu: 1 },
        { id: 3, name: "third record" },
        { id: 4, name: "aaa" },
    ];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 4,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="trululu" widget="statusbar" />
                </header>
            </form>
        `,
    });

    expect(".o_field_statusbar").not.toHaveClass("o_field_empty", {
        message: "statusbar widget should have class o_field_empty in edit",
    });
    expect(".o_statusbar_status button.dropdown-toggle:visible:disabled").toHaveCount(1);
    expect(".o_statusbar_status button.dropdown-toggle:visible:disabled").toHaveText("More");
});

test.tags("mobile");
test("clickable statusbar widget on mobile view", async () => {
    Partner._records = [
        { id: 1, name: "first record", trululu: 4 },
        { id: 2, name: "second record", trululu: 1 },
        { id: 3, name: "third record" },
        { id: 4, name: "aaa" },
    ];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <header>
                        <field name="trululu" widget="statusbar" options="{'clickable': '1'}" />
                    </header>
                </form>
            `,
    });

    // Open dropdown
    click(queryFirst(".o_statusbar_status .dropdown-toggle", { visible: true }));
    await animationFrame();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(4);

    click(".o-dropdown--menu .dropdown-item");
    await animationFrame();

    expect(".o_arrow_button_current").toHaveText("first record");
    expect(
        queryAll(".o_statusbar_status .o_arrow_button.dropdown-toggle", { visible: true })
    ).toHaveCount(1);

    // Open second dropdown
    click(queryFirst(".o_statusbar_status .dropdown-toggle", { visible: true }));
    await animationFrame();

    expect(".o-dropdown--menu .dropdown-item").toHaveCount(4);
});

test('"status" with no stages does not crash command palette', async () => {
    class Stage extends models.Model {
        name = fields.Char();
        _records = []; // no stages
    }

    class Task extends models.Model {
        status = fields.Many2one({ relation: "stage" });
        _records = [{ id: 1, status: false }];
    }

    defineModels([Stage, Task]);

    await mountView({
        type: "form",
        resModel: "task",
        resId: 1,
        arch: /* xml */ `
            <form>
                <header>
                    <field name="status" widget="statusbar" options="{'withCommand': true, 'clickable': true}"/>
                </header>
            </form>
        `,
    });

    // Open the command palette (Ctrl+K)
    await press(["control", "k"]);
    await animationFrame();

    const commands = queryAllTexts(".o_command");

    expect(commands).not.toInclude("Move to next Stage");
});

test.tags("desktop");
test("cache: update current status if it changed", async () => {
    class Stage extends models.Model {
        name = fields.Char();
        _records = [
            { id: 1, name: "Stage 1" },
            { id: 2, name: "Stage 2" },
        ];
    }
    Partner._fields.stage_id = fields.Many2one({ relation: "stage" });
    Partner._records = [
        {
            id: 1,
            name: "first record",
            stage_id: 1,
        },
        {
            id: 2,
            name: "second record",
            stage_id: 2,
        },
        {
            id: 3,
            name: "third record",
            stage_id: 2,
        },
    ];
    defineModels([Stage]);

    Partner._views = {
        kanban: `
            <kanban default_group_by="stage_id">
                <templates>
                    <t t-name="card">
                        <field name="display_name"/>
                    </t>
                </templates>
            </kanban>`,
        form: `
            <form>
                <header>
                    <field name="stage_id" widget="statusbar" />
                </header>
            </form>`,
        search: `<search></search>`,
    };

    onRpc("has_group", () => true);
    let def;
    onRpc("web_read", () => def);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        id: 1,
        name: "Partners",
        res_model: "partner",
        type: "ir.actions.act_window",
        cache: true,
        views: [
            [false, "kanban"],
            [false, "form"],
        ],
    });

    // populate the cache by visiting the 3 records
    await contains(".o_kanban_record").click();
    expect(".o_last_breadcrumb_item").toHaveText("first record");
    await pagerNext();
    expect(".o_last_breadcrumb_item").toHaveText("second record");
    await pagerNext();
    expect(".o_last_breadcrumb_item").toHaveText("third record");

    // go back to kanban and drag the first record of stage 2 on top of stage 1 column
    await contains(".o_breadcrumb .o_back_button").click();
    const dragActions = await contains(".o_kanban_record:contains(second record)").drag();
    await dragActions.moveTo(".o_kanban_record:contains(first record)");
    await dragActions.drop();
    expect(queryAllTexts(".o_kanban_record")).toEqual([
        "second record",
        "first record",
        "third record",
    ]);

    // re-open last record and use to pager to reach the record we just moved
    await contains(".o_kanban_record:contains(third record)").click();
    await pagerPrevious();
    def = new Deferred();
    await pagerPrevious();
    // retrieved from the cache => former value
    expect(".o_last_breadcrumb_item").toHaveText("second record");
    expect('.o_statusbar_status button[data-value="2"]').toHaveClass("o_arrow_button_current");
    def.resolve();
    await animationFrame();
    // updated when the rpc returns
    expect(".o_last_breadcrumb_item").toHaveText("second record");
    expect('.o_statusbar_status button[data-value="1"]').toHaveClass("o_arrow_button_current");
});
