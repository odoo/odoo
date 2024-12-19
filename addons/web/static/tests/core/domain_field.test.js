import { expect, getFixture, test } from "@odoo/hoot";
import { queryAllTexts, scroll } from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockDate } from "@odoo/hoot-mock";
import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import { SELECTORS } from "@web/../tests/core/domain_selector/domain_selector_helpers";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
    addNewRule,
    clearNotSupported,
    clickOnButtonDeleteNode,
    editValue,
    getConditionText,
    getCurrentPath,
    getCurrentValue,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

import { WebClient } from "@web/webclient/webclient";

class PartnerType extends models.Model {
    name = fields.Char({ string: "Partner Type" });
    color = fields.Integer({ string: "Color index" });

    _records = [
        { id: 12, name: "gold", color: 2 },
        { id: 14, name: "silver", color: 5 },
    ];
}

defineModels([Partner, Product, Team, Player, Country, Stage, PartnerType]);

test("The domain editor should not crash the view when given a dynamic filter", async function () {
    // dynamic filters (containing variables, such as uid, parent or today)
    // are handled by the domain editor
    Partner._records[0].foo = `[("int", "=", uid)]`;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="foo" widget="domain" options="{'model': 'partner'}" />
                    <field name="int" invisible="1" />
                </form>`,
    });

    expect(getCurrentValue()).toBe("uid", {
        message: "The widget should show the dynamic filter.",
    });
});

test("The domain editor should not crash the view when given a dynamic filter ( datetime )", async function () {
    Partner._fields.datetime = fields.Datetime({ string: "A date" });
    Partner._records[0].foo = `[("datetime", "=", context_today())]`;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="foo" widget="domain" options="{'model': 'partner'}" />
                </form>`,
    });

    expect(getCurrentValue()).toBe("context_today()");

    await clearNotSupported();

    // Change the date in the datepicker
    await contains(".o_datetime_input").click();
    // Select a date in the datepicker
    await contains(getPickerCell("15")).click();
    // Close the datepicker
    await contains(document.body).click();
    await contains(".o_form_button_cancel").click();

    // Open the datepicker again
    expect(getCurrentValue()).toBe("context_today()");
});

test("basic domain field usage is ok", async function () {
    Partner._records[0].foo = "[]";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner.type'}" />
                    </group>
                </sheet>
            </form>`,
    });

    // As the domain is empty, there should be a button to add a new rule
    expect(SELECTORS.addNewRule).toHaveCount(1);

    // Clicking on the button should add the [["id", "=", "1"]] domain, so
    // there should be a field selector in the DOM
    await addNewRule();
    expect(".o_model_field_selector").toHaveCount(1, {
        message: "there should be a field selector",
    });

    // Focusing the field selector input should open the field selector
    // popover
    await contains(".o_model_field_selector").click();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(".o_model_field_selector_popover_search input").toHaveCount(1);

    // The popover should contain the list of partner.type fields and so
    // there should be the "Color index" field
    expect(".o_model_field_selector_popover_item_name:first").toHaveText("Color index");

    // Clicking on this field should close the popover, then changing the
    // associated value should reveal one matched record
    await contains(".o_model_field_selector_popover_item_name").click();

    await editValue(2);

    expect(".o_domain_show_selection_button").toHaveText("1 record(s)", {
        message: "changing color value to 2 should reveal only one record",
    });

    // Saving the form view should show a readonly domain containing the
    // "color" field
    await contains(".o_form_button_save").click();
    expect(getCurrentPath()).toBe("Color index");
});

test("using binary field in domain widget", async function () {
    Partner._fields.image = fields.Binary({ string: "Picture" });
    Partner._records[0].foo = "[]";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner'}" />
                    </group>
                </sheet>
            </form>`,
    });

    await addNewRule();
    await contains(".o_model_field_selector").click();
    await contains(".o_model_field_selector_popover_item[data-name='image'] button").click();
    expect(getCurrentPath()).toBe("Picture");
});

test("domain field is correctly reset on every view change", async function () {
    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: `[("id", "=", 1)]`,
            bar: "product",
        },
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="bar" />
                        <field name="foo" widget="domain" options="{'model': 'bar'}" />
                    </group>
                </sheet>
            </form>`,
    });

    // As the domain is equal to [["id", "=", 1]] there should be a field
    // selector to change this
    expect(".o_field_domain .o_model_field_selector").toHaveCount(1, {
        message: "there should be a field selector",
    });

    // Focusing its input should open the field selector popover
    await contains(".o_model_field_selector").click();
    expect(".o_model_field_selector_popover").toHaveCount(1, {
        message: "field selector popover should be visible",
    });

    // As the value of the "bar" field is "product", the field selector
    // popover should contain the list of "product" fields
    expect(".o_model_field_selector_popover_item").toHaveCount(7, {
        message: "field selector popover should contain only one non-default field",
    });
    expect(".o_model_field_selector_popover_item:last").toHaveText("Product Team", {
        message: "field selector popover should contain 'Product Team' field",
    });

    // Now change the value of the "bar" field to "partner.type"
    await contains(".o_field_widget[name='bar'] input").edit("partner.type");

    // Refocusing the field selector input should open the popover again
    await contains(".o_model_field_selector").click();
    expect(".o_model_field_selector_popover").toHaveCount(1, {
        message: "field selector popover should be visible",
    });

    // Now the list of fields should be the ones of the "partner.type" model
    expect(".o_model_field_selector_popover_item").toHaveCount(6, {
        message: "field selector popover should contain two non-default fields",
    });
    expect(".o_model_field_selector_popover_item:first").toHaveText("Color index", {
        message: "field selector popover should contain 'Color index' field",
    });
});

test("domain field can be reset with a new domain (from onchange)", async function () {
    Partner._fields.name = fields.Char({
        onChange: (obj) => {
            obj.foo = `[("id", "=", 1)]`;
        },
    });
    Partner._records[0].foo = "[]";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="name" />
                    <field name="foo" widget="domain" options="{'model': 'partner'}" />
                </form>`,
    });

    expect(".o_domain_show_selection_button").toHaveText("3 record(s)", {
        message: "the domain being empty, there should be 3 records",
    });

    // update name to trigger the onchange and reset foo
    await contains(".o_field_widget[name='name'] input").edit("new value");
    await animationFrame();
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)", {
        message: "the domain has changed, there should be only 1 record",
    });
});

test("domain field: handle false domain as []", async function () {
    expect.assertions(3);

    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: false,
            bar: "product",
        },
    ];

    onRpc("search_count", ({ args }) => {
        expect(args[0]).toEqual([], { message: "should send a valid domain" });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="bar" />
                        <field name="foo" widget="domain" options="{'model': 'bar'}" />
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_field_widget[name='foo']:not(.o_field_empty)").toHaveCount(1);
    expect(".o_field_widget[name='foo'] .text-warning").toHaveCount(0);
});

test.tags("desktop");
test("basic domain field: show the selection", async function () {
    Partner._records[0].foo = "[]";
    PartnerType._views = {
        list: `<list><field name="name" /></list>`,
        search: `<search><field name="name" string="Name" /></search>`,
    };
    onRpc("has_group", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner.type'}" />
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_domain_show_selection_button").toHaveText("2 record(s)", {
        message: "selection should contain 2 records",
    });

    // open the selection
    await contains(".o_domain_show_selection_button").click();
    expect(".modal .o_list_view .o_data_row").toHaveCount(2, {
        message: "should have open a list view with 2 records in a dialog",
    });

    // click on a record -> should not open the record
    // we don't actually check that it doesn't open the record because even
    // if it tries to, it will crash as we don't define an arch in this test
    await contains(".modal .o_list_view .o_data_row .o_data_cell[data-tooltip='gold']").click();
});

test.tags("desktop");
test("field context is propagated when opening selection", async function () {
    Partner._records[0].foo = "[]";
    PartnerType._views = {
        list: `<list><field name="name" /></list>`,
        search: `<search><field name="name" string="Name" /></search>`,
        [["list", 3]]: `<list><field name="id" /></list>`,
    };
    onRpc("has_group", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="foo" widget="domain" options="{'model': 'partner.type'}" context="{'list_view_ref': 3}"/>
            </form>`,
    });

    await contains(".o_domain_show_selection_button").click();
    expect(queryAllTexts(".modal .o_data_row")).toEqual(["12", "14"], {
        message: "should have picked the correct list view",
    });
});

test("domain field: manually edit domain with textarea", async function () {
    serverState.debug = true;

    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: false,
            bar: "product",
        },
    ];

    Partner._views = {
        form: `
            <form>
                <field name="bar"/>
                <field name="foo" widget="domain" options="{'model': 'bar'}"/>
            </form>`,
        search: `<search />`,
    };

    onRpc("search_count", ({ args }) => expect.step(args[0]));
    onRpc("/web/domain/validate", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "test",
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    expect.verifySteps([[]]);

    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");

    await contains(SELECTORS.debugArea).edit("[['id', '<', 40]]");
    // the count should not be re-computed when editing with the textarea
    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");
    expect.verifySteps([]);

    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)");
    expect.verifySteps([[["id", "<", 40]]]);
});

test("domain field: manually set an invalid domain with textarea", async function () {
    serverState.debug = true;

    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: false,
            bar: "product",
        },
    ];

    Partner._views = {
        form: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
        search: `<search />`,
    };

    onRpc("/web/domain/validate", async (request) => {
        const { params } = await request.json();
        return JSON.stringify(params.domain) === '[["abc","=",1]]';
    });

    onRpc(({ args, method }) => {
        if (method === "search_count") {
            expect.step(args[0]);
        }
        if (method === "write") {
            throw new Error("should not save");
        }
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "test",
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    expect.verifySteps([[]]);

    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");

    await contains(SELECTORS.debugArea).edit("[['abc', '=', 1]]");
    await animationFrame();
    // the count should not be re-computed when editing with the textarea
    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");
    expect.verifySteps([]);

    await contains(SELECTORS.debugArea).edit("[['abc']]");
    await animationFrame();
    expect.verifySteps([]);

    await contains(".o_form_button_save").click();
    expect(".o_field_domain").toHaveClass("o_field_invalid", {
        message: "the field is marked as invalid",
    });
    expect(".o_form_view .o_form_editable").toHaveCount(1, {
        message: "the view is still in edit mode",
    });
    expect.verifySteps([]);
});

test("domain field: reload count by clicking on the refresh button", async function () {
    serverState.debug = true;

    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: "[]",
            bar: "product",
        },
    ];

    Partner._views = {
        form: `
                <form>
                    <field name="bar"/>
                    <field name="foo" widget="domain" options="{'model': 'bar'}"/>
                </form>`,
        search: `<search />`,
    };

    onRpc("/web/domain/validate", () => true);
    onRpc("search_count", ({ args }) => expect.step(args[0]));
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "test",
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    expect.verifySteps([[]]);

    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");

    await contains(SELECTORS.debugArea).edit("[['id', '<', 40]]");
    // the count should not be re-computed when editing with the textarea
    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");

    // click on the refresh button
    await contains(".o_refresh_count").click();
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)");
    expect.verifySteps([[["id", "<", 40]]]);
});

test("domain field: does not wait for the count to render", async function () {
    Partner._fields.bar = fields.Char();
    Partner._records = [
        {
            foo: "[]",
            bar: "product",
        },
    ];

    const def = new Deferred();
    onRpc("search_count", () => def);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="bar"/>
                <field name="foo" widget="domain" options="{'model': 'bar'}"/>
            </form>`,
    });

    expect(".o_field_domain_panel .fa-circle-o-notch.fa-spin").toHaveCount(1);
    expect(".o_field_domain_panel .o_domain_show_selection_button").toHaveCount(0);

    def.resolve();
    await animationFrame();

    expect(".o_field_domain_panel .fa-circle-o-notch .fa-spin").toHaveCount(0);
    expect(".o_field_domain_panel .o_domain_show_selection_button").toHaveCount(1);
    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");
});

test("domain field: edit domain with dynamic content", async function () {
    expect.assertions(3);

    serverState.debug = true;

    Partner._fields.bar = fields.Char();
    let rawDomain = `[("date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -365), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`;
    Partner._records = [
        {
            foo: rawDomain,
            bar: "product",
        },
    ];

    Partner._views = {
        form: `
            <form>
                <field name="bar"/>
                <field name="foo" widget="domain" options="{'model': 'bar'}"/>
            </form>`,
        search: `<search />`,
    };

    onRpc("web_save", ({ args }) => {
        expect(args[1].foo).toBe(rawDomain);
    });
    onRpc("/web/domain/validate", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "test",
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    expect(SELECTORS.debugArea).toHaveValue(rawDomain);

    rawDomain = `[("date", ">=", datetime.datetime.combine(context_today() + relativedelta(days = -1), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))]`;
    await contains(SELECTORS.debugArea).edit(rawDomain);
    expect(SELECTORS.debugArea).toHaveValue(rawDomain);

    await contains(".o_form_button_save").click();
});

test("domain field: edit through selector (dynamic content)", async function () {
    serverState.debug = true;
    mockDate("2020-09-05 00:00:00");

    Partner._fields.bar = fields.Char();
    let rawDomain = `[("date", ">=", context_today())]`;
    Partner._records = [
        {
            foo: rawDomain,
            bar: "partner",
        },
    ];

    Partner._views = {
        form: `
            <form>
                <field name="bar"/>
                <field name="foo" widget="domain" options="{'model': 'bar'}"/>
            </form>`,
        search: `<search />`,
    };

    onRpc(({ method }) => expect.step(method));

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "test",
        res_id: 1,
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    expect.verifySteps(["get_views", "web_read", "search_count", "fields_get"]);

    expect(SELECTORS.debugArea).toHaveValue(rawDomain);

    await clearNotSupported();
    rawDomain = `[("date", ">=", "2020-09-05")]`;
    expect(".o_datetime_input").toHaveCount(1, { message: "there should be a datepicker" });
    expect.verifySteps(["search_count"]);

    // Open and close the datepicker
    await contains(".o_datetime_input").click();
    expect(".o_datetime_picker").toHaveCount(1);
    await scroll(getFixture(), { top: 10 });
    expect(".o_datetime_picker").toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveValue(rawDomain);
    expect.verifySteps([]);

    // Manually input a date
    rawDomain = `[("date", ">=", "2020-09-09")]`;
    await contains(".o_datetime_input").edit("09/09/2020");
    expect.verifySteps(["search_count"]);
    expect(SELECTORS.debugArea).toHaveValue(rawDomain);

    // Save
    await contains(".o_form_button_save").click();
    expect.verifySteps(["web_save", "search_count"]);
    expect(SELECTORS.debugArea).toHaveValue(rawDomain);
});

test("domain field without model", async function () {
    Partner._fields.model_name = fields.Char({ string: "Model name" });

    onRpc("search_count", ({ model }) => {
        expect.step(model);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="model_name"/>
                <field name="name" widget="domain" options="{'model': 'model_name'}"/>
            </form>`,
    });

    expect('.o_field_widget[name="name"]').toHaveText("Select a model to add a filter.", {
        message: "should contain an error message saying the model is missing",
    });
    expect.verifySteps([]);

    await contains(".o_field_widget[name=model_name] input").edit("partner");
    await animationFrame();
    expect('.o_field_widget[name="name"] .o_field_domain_panel').toHaveText("3 record(s)");
    expect.verifySteps(["partner"]);
});

test.tags("desktop");
test("domain field in kanban view", async function () {
    Partner._records[0].foo = "[]";
    PartnerType._views = {
        list: `<list><field name="name" /></list>`,
        search: `<search><field name="name" string="Name" /></search>`,
    };
    onRpc("has_group", () => true);
    await mountView({
        type: "kanban",
        resModel: "partner",
        resId: 1,
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="domain" options="{'model': 'partner.type'}" />
                    </t>
                </templates>
            </kanban>`,
        selectRecord: (resId) => {
            expect.step(`open record ${resId}`);
        },
    });

    expect(".o_read_mode:first").toHaveText("Match all records");

    await contains(".o_domain_show_selection_button").click();
    expect(".o_dialog .o_list_view").toHaveCount(1, {
        message: "selected records are listed in a dialog",
    });

    await contains(".o_domain_selector").click();
    expect.verifySteps(["open record 1"]);
});

test("domain field with 'inDialog' options", async function () {
    onRpc("/web/domain/validate", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner', 'in_dialog': True}"/>
            </form>`,
    });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(".modal").toHaveCount(0);
    await contains(".o_field_domain_dialog_button").click();
    expect(".modal").toHaveCount(1);
    await contains(`.modal ${SELECTORS.addNewRule}`).click();
    await contains(".modal-footer .btn-primary").click();
    expect(SELECTORS.condition).toHaveCount(1);
    expect(getConditionText()).toBe("Id is equal 1");
});

test("invalid value in domain field with 'inDialog' options", async function () {
    Partner._fields.name.default = "[]";
    serverState.debug = true;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner', 'in_dialog': True}"/>
            </form>`,
    });
    expect(SELECTORS.condition).toHaveCount(0);
    expect(".modal").toHaveCount(0);
    expect(".o_field_domain .text-warning").toHaveCount(0);

    await contains(".o_field_domain_dialog_button").click();
    expect(".modal").toHaveCount(1);

    await contains(`.modal ${SELECTORS.addNewRule}`).click();
    await contains(SELECTORS.debugArea).edit("[(0, '=', expr)]");
    await contains(".modal-footer .btn-primary").click();
    expect(".modal").toHaveCount(1, { message: "the domain is invalid: the dialog is not closed" });
});

test("edit domain button is available even while loading records count", async function () {
    Partner._fields.name.default = "[]";
    serverState.debug = true;
    const searchCountDeffered = new Deferred();
    onRpc("/web/domain/validate", () => true);
    onRpc("search_count", () => searchCountDeffered);
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner', 'in_dialog': True}"/>
            </form>`,
    });
    expect(".modal").toHaveCount(0);
    expect(".o_field_domain_dialog_button").toHaveCount(1);
    await contains(".o_field_domain_dialog_button").click();
    searchCountDeffered.resolve();
    expect(".modal").toHaveCount(1);
    await contains(".modal-footer .btn-primary").click();
    expect(".modal").toHaveCount(0);
    expect(".o_domain_show_selection_button").toHaveText("3 record(s)");
});

test("debug input editing sets the field as dirty even without a focus out", async function () {
    Partner._fields.name.default = "[]";
    serverState.debug = true;
    onRpc("/web/domain/validate", () => {
        expect.step("validate domain");
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner'}"/>
            </form>`,
    });
    await contains(".o_form_button_save").click();
    await contains(SELECTORS.debugArea).edit("[['id', '=', False]]", { confirm: false });
    expect(".o_form_button_save").toHaveCount(1);
    await contains(".o_form_button_save").click();
    expect.verifySteps(["validate domain"]);
});

test("debug input corrections don't need a focus out to be saved", async function () {
    Partner._fields.name.default = "[]";
    serverState.debug = true;
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner'}"/>
            </form>`,
    });
    await contains(".o_form_button_save").click();
    await contains(SELECTORS.debugArea).edit("[", { confirm: false });
    await contains(".o_form_button_save").click();
    expect(".o_field_domain").toHaveClass("o_field_invalid");
    await contains(SELECTORS.debugArea).edit("[('id', '=', 1)]", { confirm: false });
    expect(".o_form_status_indicator span i.fa-warning").toHaveCount(0);
    expect(".o_form_button_save[disabled]").toHaveCount(0);
    expect(".o_form_button_save").toHaveCount(1);
});

test("quick check on save if domain has been edited via the debug input", async function () {
    serverState.debug = true;
    Partner._fields.name = fields.Char({ default: "[['id', '=', False]]" });
    onRpc("/web/domain/validate", async (request) => {
        const { params } = await request.json();
        expect.step("validate model");
        expect(params).toEqual({
            domain: [["id", "!=", false]],
            model: "partner",
        });
        return true;
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="name" widget="domain" options="{'model': 'partner'}"/>
            </form>`,
    });
    expect(".o_domain_show_selection_button").toHaveText("0 record(s)");
    await contains(SELECTORS.debugArea).edit("[['id', '!=', False]]");
    await contains("button.o_form_button_save").click();
    await animationFrame();
    expect.verifySteps(["validate model", "validate model"]);
    expect(".o_domain_show_selection_button").toHaveText("4 record(s)");
});
test("domain field can be foldable", async function () {
    Partner._records[0].foo = "[]";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner.type', 'foldable': true}" />
                    </group>
                </sheet>
            </form>`,
    });

    // As the domain is empty, the "Match all records" span should be visible
    expect(".o_field_domain span").toHaveText("Match all records");

    // Unfold the domain
    await contains(".o_field_domain > div > div").click();

    // There should be a button to add a new rule
    expect(SELECTORS.addNewRule).toHaveCount(1);

    // Clicking on the button should add the [["id", "=", "1"]] domain, so
    // there should be a field selector in the DOM
    await addNewRule();
    expect(".o_model_field_selector").toHaveCount(1);

    // Focusing the field selector input should open the field selector
    // popover
    await contains(".o_model_field_selector").click();
    expect(".o_model_field_selector_popover").toHaveCount(1);
    expect(".o_model_field_selector_popover_search input").toHaveCount(1);

    // The popover should contain the list of partner.type fields and so
    // there should be the "Color index" field
    expect(".o_model_field_selector_popover_item_name:first").toHaveText("Color index");

    // Clicking on this field should close the popover, then changing the
    // associated value should reveal one matched record
    await contains(".o_model_field_selector_popover_item_name").click();

    await editValue(2);

    expect(".o_domain_show_selection_button").toHaveText("1 record(s)", {
        message: "changing color value to 2 should reveal only one record",
    });

    // Saving the form view should show a readonly domain containing the
    // "color" field
    await contains(".o_form_button_save").click();
    expect(getCurrentPath()).toBe("Color index");

    // Fold domain selector
    await contains(".o_field_domain a i").click();

    expect(".o_field_domain .o_facet_values:contains('Color index is equal 2')").toHaveCount(1);
});

test("add condition in empty foldable domain", async function () {
    serverState.debug = true;
    Partner._records[0].foo = '[("id", "=", 1)]';

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner.type', 'foldable': true}" />
                    </group>
                </sheet>
            </form>`,
    });
    // As the domain is not empty, the "Add condition" button should not be available
    expect(".o_domain_add_first_node_button").toHaveCount(0);

    // Unfold the domain and delete the condition
    await contains(".o_field_domain > div > div").click();
    await clickOnButtonDeleteNode();

    // Fold domain selector
    await contains(".o_field_domain a i").click();

    // As the domain is empty, the "Add condition" button should now be available
    expect(".o_domain_add_first_node_button").toHaveCount(1);

    // Click on "Add condition"
    await contains(".o_domain_add_first_node_button").click();
    // Domain is now unfolded with the default condition
    expect(".o_model_field_selector").toHaveCount(1);
    expect(SELECTORS.debugArea).toHaveValue('[("id", "=", 1)]');
});

test("foldable domain field unfolds and hides caret when domain is invalid", async function () {
    Partner._records[0].foo = "[";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner.type', 'foldable': true}" />
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_field_domain span").toHaveText("Invalid domain");
    expect(".fa-caret-down").toHaveCount(0);
    expect(".o_domain_selector_row").toHaveText("This domain is not supported.\nReset domain");
    await contains(".o_domain_selector_row button").click();
    expect(".o_field_domain span:first").toHaveText("Match all records");
});

test("folded domain field with any operator", async function () {
    Partner._fields.company_id = fields.Many2one({ relation: "partner" });
    Partner._records[0].foo = "[('company_id', 'any', [('id', '=', 1)])]";
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner', 'foldable': true}" />
                    </group>
                </sheet>
            </form>`,
    });
    expect(`.o_field_domain .o_facet_values`).toHaveText("Company matches ( Id is equal 1 )");
});

test("folded domain field with withinh operator", async function () {
    Partner._fields.company_id = fields.Many2one({ relation: "partner" });
    Partner._records[0].foo = `[
        "&",
        ("datetime", ">=", datetime.datetime.combine(context_today(), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S")),
        ("datetime", "<=", datetime.datetime.combine(context_today() + relativedelta(months = 2), datetime.time(0, 0, 0)).to_utc().strftime("%Y-%m-%d %H:%M:%S"))
    ]`;
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" widget="domain" options="{'model': 'partner', 'foldable': true}" />
                    </group>
                </sheet>
            </form>`,
    });
    expect(`.o_field_domain .o_facet_values`).toHaveText("Datetime is within 2 months");
});
