import { after, expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    queryAll,
    queryAllProperties,
    queryAllTexts,
    queryRect,
    resize,
} from "@odoo/hoot-dom";
import { animationFrame, mockTimeZone } from "@odoo/hoot-mock";
import {
    editTime,
    getPickerCell,
    zoomOut,
} from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickSave,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    onRpc,
    contains,
} from "@web/../tests/web_test_helpers";
import { resetDateFieldWidths } from "@web/views/list/column_width_hook";

class Partner extends models.Model {
    date = fields.Date({ string: "A date", searchable: true });
    datetime = fields.Datetime({ string: "A datetime", searchable: true });
    p = fields.One2many({
        string: "one2many field",
        relation: "partner",
        searchable: true,
    });
    _records = [
        {
            id: 1,
            date: "2017-02-03",
            datetime: "2017-02-08 10:00:00",
            p: [],
        },
        {
            id: 2,
            date: false,
            datetime: false,
        },
    ];
}
class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
defineModels([Partner, User]);

test("DatetimeField in form view", async () => {
    mockTimeZone(+2); // UTC+2

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form>
            <field name="datetime"/>
            <field name="datetime" readonly="1"/>
        </form>`,
    });

    const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
    expect(".o_field_datetime button").toHaveValue(expectedDateString, {
        message: "the datetime should be correctly displayed",
    });
    expect(".o_field_datetime button").toHaveAttribute("data-tooltip", expectedDateString);
    expect(".o_field_datetime span").toHaveAttribute("data-tooltip", expectedDateString);

    // datepicker should not open on focus
    expect(".o_datetime_picker").toHaveCount(0);

    await click(".o_field_datetime button");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    // select 22 April 2018 at 8:25
    await zoomOut();
    await zoomOut();
    await click(getPickerCell("2018"));
    await animationFrame();
    await click(getPickerCell("Apr"));
    await animationFrame();
    await click(getPickerCell("22"));
    await animationFrame();
    await editTime("8:25");
    // Close the datepicker
    await click(".o_form_view_container");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(0, { message: "datepicker should be closed" });

    const newExpectedDateString = "04/22/2018 08:25:00";
    expect(".o_field_datetime button").toHaveValue(newExpectedDateString, {
        message: "the selected date should be displayed in the input",
    });

    // save
    await clickSave();
    expect(".o_field_datetime button").toHaveValue(newExpectedDateString, {
        message: "the selected date should be displayed after saving",
    });
});

test("DatetimeField only triggers fieldChange when a day is picked and when an hour/minute is selected", async () => {
    mockTimeZone(+2);

    Partner._onChanges.datetime = () => {};

    onRpc("onchange", () => expect.step("onchange"));

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form><field name="datetime"/></form>',
    });

    await click(".o_field_datetime button");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(1);
    // select 22 April 2018 at 8:25
    await zoomOut();
    await zoomOut();
    await click(getPickerCell("2018"));
    await animationFrame();
    await click(getPickerCell("Apr"));
    await animationFrame();
    await click(getPickerCell("22"));
    await animationFrame();

    expect.verifySteps([]);

    await editTime("8:25");

    expect.verifySteps([]);

    // Close the datepicker
    await click(document.body);
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(0);

    expect(".o_field_datetime button").toHaveValue("04/22/2018 08:25:00");
    expect.verifySteps(["onchange"]);
});

test("DatetimeField edit hour/minute and click away", async () => {
    mockTimeZone(0);

    onRpc("web_save", ({ args }) => {
        expect(args[1].datetime).toBe("2017-02-08 08:30:00", {
            message: "the correct value should be saved",
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form><field name="datetime"/></form>',
    });

    // Open the datepicker
    await click(".o_field_datetime button");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    // Manually change the time without { confirm: "enter" }
    await click(`.o_time_picker_input:eq(0)`);
    await animationFrame();
    await edit("8:30");
    await animationFrame();
    expect(".o_field_datetime input").toHaveValue("02/08/2017 10:00:00", {
        message: "Input value shouldn't be updated yet",
    });

    // Close the datepicker
    await click(document.body);
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(0);

    expect(".o_field_datetime button").toHaveValue("02/08/2017 08:30:00");
    await clickSave();
});

test("DatetimeField with datetime formatted without second", async () => {
    mockTimeZone(0);

    Partner._fields.datetime = fields.Datetime({
        string: "A datetime",
        searchable: true,
        default: "2017-08-02 12:00:05",
        required: true,
    });

    defineParams({
        lang_parameters: {
            date_format: "%m/%d/%Y",
            time_format: "%H:%M",
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="datetime"/></form>',
    });

    const expectedDateString = "08/02/2017 12:00";
    expect(".o_field_datetime button").toHaveValue(expectedDateString, {
        message: "the datetime should be correctly displayed",
    });

    await click(".o_form_button_cancel");
    expect(".modal").toHaveCount(0, { message: "there should not be a Warning dialog" });
});

test("DatetimeField in editable list view", async () => {
    mockTimeZone(+2);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="bottom"><field name="datetime"/></list>`,
    });

    expect("tr.o_data_row td:not(.o_list_record_selector):first").toHaveText(
        "Feb 8, 2017, 12:00 PM",
        {
            message: "the datetime should be correctly displayed",
        }
    );

    // switch to edit mode
    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect(".o_field_datetime button").toHaveCount(1, {
        message: "the view should have a date input for editable mode",
    });

    expect(".o_field_datetime button").toBeFocused({
        message: "date input should have the focus",
    });

    expect(".o_field_datetime button").toHaveValue("02/08/2017 12:00:00", {
        message: "the date should be correct in edit mode",
    });

    expect(".o_datetime_picker").toHaveCount(0);

    await click(".o_field_datetime button");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(1);

    // select 22 April 2018 at 8:25
    await zoomOut();
    await zoomOut();
    await click(getPickerCell("2018"));
    await animationFrame();
    await click(getPickerCell("Apr"));
    await animationFrame();
    await click(getPickerCell("22"));
    await animationFrame();
    await editTime("8:25");
    await animationFrame();

    expect(".o_field_datetime input").toHaveValue("04/22/2018 08:25:00", {
        message: "the date should be correct in edit mode",
    });
    // save

    await click(".o_list_button_save");
    await animationFrame();
    expect("tr.o_data_row td:not(.o_list_record_selector):first").toHaveText(
        "Apr 22, 2018, 8:25 AM",
        { message: "the selected datetime should be displayed after saving" }
    );
});

test("DatetimeField input in editable list view keeps its parent's width when empty", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list editable="bottom"><field name="datetime"/></list>`,
    });
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    expect(".o_data_row:eq(1) .o_data_cell input").toHaveRect(
        queryRect(".o_data_row:eq(1) .o_data_cell .o_field_datetime"),
        { message: "input should have the same size as its parent when empty" }
    );
});

test.tags("desktop");
test("multi edition of DatetimeField in list view: edit date in input", async () => {
    mockTimeZone(0);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list multi_edit="1"><field name="datetime"/></list>',
    });

    // select two records and edit them
    await click(".o_data_row:eq(0) .o_list_record_selector input");
    await animationFrame();
    await click(".o_data_row:eq(1) .o_list_record_selector input");
    await animationFrame();

    await click(".o_data_row:eq(0) .o_data_cell");
    await animationFrame();

    expect(".o_field_datetime button").toHaveCount(1);

    await click(".o_field_datetime button");
    await animationFrame();
    await click(".o_field_datetime input");
    await animationFrame();
    await edit("10/02/2019 09:00:00", { confirm: "Enter" });
    await animationFrame();

    expect(".modal").toHaveCount(1);

    await click(".modal .modal-footer .btn-primary");
    await animationFrame();

    expect(".o_data_row:first-child .o_data_cell:first").toHaveText("Oct 2, 9:00 AM");
    expect(".o_data_row:nth-child(2) .o_data_cell:first").toHaveText("Oct 2, 9:00 AM");
});

test.tags("desktop");
test("multi edition of DatetimeField in list view: clear date in input", async () => {
    Partner._records[1].datetime = "2017-02-08 10:00:00";
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: '<list multi_edit="1"><field name="datetime"/></list>',
    });

    // select two records and edit them
    await click(".o_data_row:eq(0) .o_list_record_selector input");
    await animationFrame();
    await click(".o_data_row:eq(1) .o_list_record_selector input");
    await animationFrame();
    await click(".o_data_row:eq(0) .o_data_cell");
    await animationFrame();

    expect(".o_field_datetime button").toHaveCount(1);

    await click(".o_field_datetime button");
    await animationFrame();
    await click(".o_field_datetime input");
    await animationFrame();
    await edit("", { confirm: "Enter" });
    await animationFrame();

    expect(".modal").toHaveCount(1);

    await click(".modal .modal-footer .btn-primary");
    await animationFrame();

    expect(".o_data_row:first-child .o_data_cell:first").toHaveText("");
    expect(".o_data_row:nth-child(2) .o_data_cell:first").toHaveText("");
});

test("DatetimeField remove value", async () => {
    expect.assertions(4);

    mockTimeZone(+2);

    onRpc("web_save", ({ args }) => {
        expect(args[1].datetime).toBe(false, { message: "the correct value should be saved" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ '<form><field name="datetime"/></form>',
    });

    expect(".o_field_datetime button").toHaveValue("02/08/2017 12:00:00", {
        message: "the date should be correct in edit mode",
    });

    await click(".o_field_datetime button");
    await animationFrame();
    await click(".o_field_datetime input");
    await animationFrame();
    await edit("");
    await animationFrame();
    await click(document.body);
    await animationFrame();

    expect(".o_field_datetime input:first").toHaveValue("", {
        message: "should have an empty input",
    });

    // save
    await clickSave();
    expect(".o_field_datetime:first").toHaveText("", {
        message: "the selected date should be displayed after saving",
    });
});

test("datetime field: hit enter should update value", async () => {
    // This test verifies that the field datetime is correctly computed when:
    //     - we press enter to validate our entry
    //     - we click outside the field to validate our entry
    //     - we save
    mockTimeZone(+2);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="datetime"/></form>',
        resId: 1,
    });

    // Enter a beginning of date and press enter to validate
    await click(".o_field_datetime button");
    await animationFrame();
    await click(".o_field_datetime input");
    await animationFrame();
    await edit("01/08/22 14:30", { confirm: "Enter" });

    const datetimeValue = `01/08/2022 14:30:00`;

    expect(".o_field_datetime input:first").toHaveValue(datetimeValue);

    // Click outside the field to check that the field is not changed
    await click(document.body);
    await animationFrame();
    expect(".o_field_datetime button").toHaveValue(datetimeValue);

    // Save and check that it's still ok
    await clickSave();

    expect(".o_field_datetime button").toHaveValue(datetimeValue);
});

test("DateTimeField with label opens datepicker on click", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <label for="datetime" string="When is it" />
                    <field name="datetime" />
                </form>`,
    });

    await click("label.o_form_label");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1, { message: "datepicker should be opened" });
});

test("datetime field: use picker with arabic numbering system", async () => {
    defineParams({ lang: "ar_001" }); // Select Arab language

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form string="Partners"><field name="datetime" /></form>`,
    });

    expect("[name=datetime] button").toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٠٠:٠٠");

    await click("[name=datetime] button");
    await animationFrame();
    await editTime("11:45");
    expect("[name=datetime] input").toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٤٥:٠٠");
});

test("datetime field in list view with show_seconds option", async () => {
    mockTimeZone(+2);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="datetime" widget="datetime" string="show_seconds as false"/>
                <field name="datetime" widget="datetime" options="{'show_seconds': true}" string="show_seconds as true"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:first .o_field_datetime")).toEqual([
        "Feb 8, 2017, 12:00 PM",
        "Feb 8, 2017, 12:00:00 PM",
    ]);
});

test("edit a datetime field in form view with show_seconds option", async () => {
    mockTimeZone(+2);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="datetime" string="show_seconds as false"/>
                <field name="datetime" widget="datetime" options="{'show_seconds': true}"  string="show_seconds as true"/>
            </form>`,
    });

    await contains(".o_input:eq(0)").click();
    await animationFrame();
    expect(".o_time_picker_input").toHaveValue("11:00");
    await edit("02/08/2017 11:00:00", { confirm: "Enter" });
    await animationFrame();

    expect(".o_input:eq(0)").toHaveValue("02/08/2017 11:00:00", {
        message: "seconds should be hidden for showSeconds false",
    });

    await contains(".o_input:eq(1)").click();
    await animationFrame();
    expect(".o_time_picker_input").toHaveValue("11:00:00");
    await edit("02/08/2017 11:00:30", { confirm: "Enter" });
    await animationFrame();

    expect(".o_input:eq(1)").toHaveValue("02/08/2017 11:00:30", {
        message: "seconds should be visible for showSeconds true",
    });
});

test("datetime field (with widget) in kanban with show_time option", async () => {
    mockTimeZone(+2);

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="datetime" widget="datetime" options="{'show_time': false}"/>
                    </t>
                </templates>
            </kanban>`,
        resId: 1,
    });

    expect(".o_kanban_record:first").toHaveText("Feb 8, 2017");
});

test("datetime field in list with show_time option", async () => {
    mockTimeZone(+2);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: `
            <list editable="bottom">
                <field name="datetime" options="{'show_time': false}"/>
                <field name="datetime" />
            </list>
        `,
    });

    const dates = queryAll(".o_field_cell");

    expect(dates[0]).toHaveText("Feb 8, 2017", {
        message: "for date field only date should be visible with date widget",
    });
    expect(dates[1]).toHaveText("Feb 8, 2017, 12:00 PM", {
        message: "for datetime field only date should be visible with date widget",
    });
    await contains(dates[0]).click();
    await animationFrame();
    expect(".o_field_datetime input:first").toHaveValue("02/08/2017 12:00:00", {
        message: "for datetime field both date and time should be visible with datetime widget",
    });
});

test("placeholder_field shows as placeholder (char)", async () => {
    Partner._fields.char = fields.Char({
        default: "My Placeholder",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="char"/>
                <field name="datetime" options="{'placeholder_field': 'char'}"/>
            </form>`,
    });
    await contains("div[name='datetime'] .o_input").click();
    expect("div[name='datetime'] .o_input").toHaveAttribute("placeholder", "My Placeholder", {
        message: "placeholder_field should be the placeholder",
    });
});

test("placeholder_field shows as placeholder (datetime)", async () => {
    mockTimeZone(0);

    defineParams({
        lang_parameters: {
            date_format: "%d/%m/%Y",
            time_format: "%H:%M",
        },
    });

    Partner._fields.datetime_example = fields.Datetime({
        string: "A datetime",
        searchable: true,
        default: "2025-04-01 09:11:11",
        required: true,
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime_example"/>
                <field name="datetime" options="{'placeholder_field': 'datetime_example'}"/>
            </form>`,
    });
    await contains("div[name='datetime'] button").click();
    expect("div[name='datetime'] input").toHaveAttribute("placeholder", "Apr 1, 2025, 9:11 AM", {
        message: "placeholder_field should be the placeholder",
    });
});

test("list datetime: column widths (show_time=false)", async () => {
    await resize({ width: 800 });
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="datetime" widget="datetime" options="{'show_time': false }" />
                <field name="display_name" />
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual(["Feb 8, 2017", "partner,1"]);
    expect(queryAllProperties(".o_list_table thead th", "offsetWidth")).toEqual([40, 99, 661]);
});

test("list datetime: column widths (numeric format)", async () => {
    await resize({ width: 800 });
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="datetime" widget="datetime" options="{'numeric': true }" />
                <field name="display_name" />
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual([
        "02/08/2017 11:00:00",
        "partner,1",
    ]);
    expect(queryAllProperties(".o_list_table thead th", "offsetWidth")).toEqual([40, 144, 616]);
});
