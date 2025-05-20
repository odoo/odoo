import { after, expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    queryAll,
    queryAllProperties,
    queryAllTexts,
    resize,
    select,
} from "@odoo/hoot-dom";
import { animationFrame, mockTimeZone } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    defineParams,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {
    getPickerApplyButton,
    getPickerCell,
    getTimePickers,
    zoomOut,
} from "@web/../tests/core/datetime/datetime_test_helpers";

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

    name = fields.Char();

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
        arch: '<form><field name="datetime"/></form>',
    });

    const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
    expect(".o_field_datetime input").toHaveValue(expectedDateString, {
        message: "the datetime should be correctly displayed",
    });

    // datepicker should not open on focus
    expect(".o_datetime_picker").toHaveCount(0);

    await click(".o_field_datetime input");
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
    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    await select("8", { target: hourSelect });
    await animationFrame();
    await select("25", { target: minuteSelect });
    await animationFrame();
    // Close the datepicker
    await click(".o_form_view_container");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(0, { message: "datepicker should be closed" });

    const newExpectedDateString = "04/22/2018 08:25:00";
    expect(".o_field_datetime input").toHaveValue(newExpectedDateString, {
        message: "the selected date should be displayed in the input",
    });

    // save
    await clickSave();
    expect(".o_field_datetime input").toHaveValue(newExpectedDateString, {
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

    await click(".o_field_datetime input");
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

    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    await select("8", { target: hourSelect });
    await animationFrame();
    await select("25", { target: minuteSelect });
    await animationFrame();

    expect.verifySteps([]);

    // Close the datepicker
    await click(document.body);
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(0);

    expect(".o_field_datetime input").toHaveValue("04/22/2018 08:25:00");
    expect.verifySteps(["onchange"]);
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
    expect(".o_field_datetime input").toHaveValue(expectedDateString, {
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

    const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
    expect("tr.o_data_row td:not(.o_list_record_selector):first").toHaveText(expectedDateString, {
        message: "the datetime should be correctly displayed",
    });

    // switch to edit mode
    await click(".o_data_row .o_data_cell");
    await animationFrame();
    expect(".o_field_datetime input").toHaveCount(1, {
        message: "the view should have a date input for editable mode",
    });
    expect(".o_field_datetime input").toBeFocused({
        message: "date input should have the focus",
    });

    expect(".o_field_datetime input").toHaveValue(expectedDateString, {
        message: "the date should be correct in edit mode",
    });

    expect(".o_datetime_picker").toHaveCount(0);

    await click(".o_field_datetime input");
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
    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    await select("8", { target: hourSelect });
    await animationFrame();
    await select("25", { target: minuteSelect });
    await animationFrame();
    // Apply changes

    await click(getPickerApplyButton());
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(0, { message: "datepicker should be closed" });

    const newExpectedDateString = "04/22/2018 08:25:00";

    expect(".o_field_datetime input:first").toHaveValue(newExpectedDateString, {
        message: "the date should be correct in edit mode",
    });
    // save

    await click(".o_list_button_save");
    await animationFrame();
    expect("tr.o_data_row td:not(.o_list_record_selector):first").toHaveText(
        newExpectedDateString,
        { message: "the selected datetime should be displayed after saving" }
    );
});
test.tags("desktop");
test("multi edition of DatetimeField in list view: edit date in input", async () => {
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

    expect(".o_field_datetime input").toHaveCount(1);

    await click(".o_field_datetime input");
    await edit("10/02/2019 09:00:00", { confirm: "Enter" });
    await animationFrame();

    expect(".modal").toHaveCount(1);

    await click(".modal .modal-footer .btn-primary");
    await animationFrame();

    expect(".o_data_row:first-child .o_data_cell:first").toHaveText("10/02/2019 09:00:00");
    expect(".o_data_row:nth-child(2) .o_data_cell:first").toHaveText("10/02/2019 09:00:00");
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

    expect(".o_field_datetime input").toHaveCount(1);

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

    expect(".o_field_datetime input:first").toHaveValue("02/08/2017 12:00:00", {
        message: "the date should be correct in edit mode",
    });

    await click(".o_field_datetime input");
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

test("DatetimeField with date/datetime widget (with day change) does not care about widget", async () => {
    mockTimeZone(-4);
    onRpc("has_group", () => true);

    Partner._records[0].p = [2];
    Partner._records[1].datetime = "2017-02-08 02:00:00"; // UTC

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list><field name="datetime" /></list>
                    <form><field name="datetime" widget="date" /></form>
                </field>
            </form>`,
    });

    const expectedDateString = "02/07/2017 22:00:00"; // local time zone
    expect(".o_field_widget[name='p'] .o_data_cell").toHaveText(expectedDateString, {
        message: "the datetime (datetime widget) should be correctly displayed in list view",
    });

    // switch to form view
    await click(".o_field_widget[name='p'] .o_data_cell");
    await animationFrame();
    expect(".modal .o_field_date[name='datetime'] input").toHaveValue("02/07/2017 22:00:00", {
        message: "the datetime (date widget) should be correctly displayed in form view",
    });
});

test("DatetimeField with date/datetime widget (without day change) does not care about widget", async () => {
    mockTimeZone(-4);

    Partner._records[0].p = [2];
    Partner._records[1].datetime = "2017-02-08 10:00:00"; // without timezone

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="p">
                    <list><field name="datetime" /></list>
                    <form><field name="datetime" widget="date" /></form>
                </field>
            </form>`,
    });

    const expectedDateString = "02/08/2017 06:00:00"; // with timezone
    expect(".o_field_widget[name='p'] .o_data_cell:first").toHaveText(expectedDateString, {
        message: "the datetime (datetime widget) should be correctly displayed in list view",
    });

    // switch to form view
    await click(".o_field_widget[name='p'] .o_data_cell");
    await animationFrame();
    expect(".modal .o_field_date[name='datetime'] input:first").toHaveValue("02/08/2017 06:00:00", {
        message: "the datetime (date widget) should be correctly displayed in form view",
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
    await click(".o_field_datetime input");
    await edit("01/08/22 14:30:40", { confirm: "Enter" });

    const datetimeValue = `01/08/2022 14:30:40`;

    expect(".o_field_datetime input:first").toHaveValue(datetimeValue);

    // Click outside the field to check that the field is not changed
    await click(document.body);
    expect(".o_field_datetime input:first").toHaveValue(datetimeValue);

    // Save and check that it's still ok
    await clickSave();

    expect(".o_field_datetime input:first").toHaveValue(datetimeValue);
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

    expect("[name=datetime] input:first").toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٠٠:٠٠");

    await click("[name=datetime] input");
    await animationFrame();
    await select(45, { target: getTimePickers()[0][1] });
    await animationFrame();
    expect("[name=datetime] input:first").toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٤٥:٠٠");
});

test("datetime field in list view with show_seconds option", async () => {
    mockTimeZone(+2);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="datetime" widget="datetime" options="{'show_seconds': false}" string="show_seconds as false"/>
                <field name="datetime" widget="datetime" string="show_seconds as true"/>
            </list>`,
    });

    expect(queryAllTexts(".o_data_row:first .o_field_datetime")).toEqual([
        "02/08/2017 12:00",
        "02/08/2017 12:00:00",
    ]);
});

test("edit a datetime field in form view with show_seconds option", async () => {
    mockTimeZone(+2);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="datetime" options="{'show_seconds': false}" string="show_seconds as false"/>
                <field name="datetime" widget="datetime" string="show_seconds as true"/>
            </form>`,
    });

    const [dateField1, dateField2] = queryAll(".o_input.cursor-pointer");
    await click(dateField1);
    await animationFrame();
    expect(".o_time_picker_select").toHaveCount(3); // 3rd 'o_time_picker_select' is for the seconds
    await edit("02/08/2017 11:00:00", { confirm: "Enter" });
    await animationFrame();

    expect(dateField1).toHaveValue("02/08/2017 11:00", {
        message: "seconds should be hidden for showSeconds false",
    });

    expect(dateField2).toHaveValue("02/08/2017 11:00:00", {
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

    expect(".o_kanban_record:first").toHaveText("02/08/2017");
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

    expect(dates[0]).toHaveText("02/08/2017", {
        message: "for date field only date should be visible with date widget",
    });
    expect(dates[1]).toHaveText("02/08/2017 12:00:00", {
        message: "for datetime field only date should be visible with date widget",
    });
    await click(dates[0]);
    await animationFrame();
    expect(".o_field_datetime input:first").toHaveValue("02/08/2017 12:00:00", {
        message: "for datetime field both date and time should be visible with datetime widget",
    });
});

test("datetime field in form view with condensed option", async () => {
    mockTimeZone(-2); // UTC-2

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime" options="{'condensed': true}"/>
                <field name="datetime" options="{'condensed': true}" readonly="1"/>
            </form>`,
    });

    const expectedDateString = "2/8/2017 8:00:00"; // 10:00:00 without timezone
    expect(".o_field_datetime input").toHaveValue(expectedDateString);
    expect(".o_field_datetime.o_readonly_modifier").toHaveText(expectedDateString);
});

test("datetime field in kanban view with condensed option", async () => {
    mockTimeZone(-2); // UTC-2

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="datetime" options="{'condensed': true}"/>
                    </t>
                </templates>
            </kanban>`,
    });

    const expectedDateString = "2/8/2017 8:00:00"; // 10:00:00 without timezone
    expect(".o_kanban_record:first").toHaveText(expectedDateString);
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

    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual(["02/08/2017", "partner,1"]);
    expect(queryAllProperties(".o_list_table thead th", "offsetWidth")).toEqual([40, 81, 679]);
});
