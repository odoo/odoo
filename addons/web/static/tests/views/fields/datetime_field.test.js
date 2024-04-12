import { expect, test } from "@odoo/hoot";
import { click, edit, queryAll, queryFirst, select } from "@odoo/hoot-dom";
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
defineModels([Partner]);

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

    click(".o_field_datetime input");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    // select 22 April 2018 at 8:25
    zoomOut();
    await animationFrame();
    zoomOut();
    await animationFrame();
    click(getPickerCell("2018"));
    await animationFrame();
    click(getPickerCell("Apr"));
    await animationFrame();
    click(getPickerCell("22"));
    await animationFrame();
    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    select("8", { target: hourSelect });
    await animationFrame();
    select("25", { target: minuteSelect });
    await animationFrame();
    // Close the datepicker
    click(".o_form_view_container");
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

    click(".o_field_datetime input");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(1);
    // select 22 April 2018 at 8:25
    zoomOut();
    await animationFrame();
    zoomOut();
    await animationFrame();
    click(getPickerCell("2018"));
    await animationFrame();
    click(getPickerCell("Apr"));
    await animationFrame();
    click(getPickerCell("22"));
    await animationFrame();

    expect([]).toVerifySteps();

    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    select("8", { target: hourSelect });
    await animationFrame();
    select("25", { target: minuteSelect });
    await animationFrame();

    expect([]).toVerifySteps();

    // Close the datepicker
    click(document.body);
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(0);

    expect(".o_field_datetime input").toHaveValue("04/22/2018 08:25:00");
    expect(["onchange"]).toVerifySteps();
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

    click(".o_form_button_cancel");
    expect(".modal").toHaveCount(0, { message: "there should not be a Warning dialog" });
});

test("DatetimeField in editable list view", async () => {
    mockTimeZone(+2);
    onRpc("has_group", () => true);

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<tree editable="bottom"><field name="datetime"/></tree>`,
    });

    const expectedDateString = "02/08/2017 12:00:00"; // 10:00:00 without timezone
    expect(queryFirst("tr.o_data_row td:not(.o_list_record_selector)")).toHaveText(
        expectedDateString,
        { message: "the datetime should be correctly displayed" }
    );

    // switch to edit mode
    click(queryFirst(".o_data_row .o_data_cell"));
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

    click(".o_field_datetime input");
    await animationFrame();

    expect(".o_datetime_picker").toHaveCount(1);

    // select 22 April 2018 at 8:25
    zoomOut();
    await animationFrame();
    zoomOut();
    await animationFrame();
    click(getPickerCell("2018"));
    await animationFrame();
    click(getPickerCell("Apr"));
    await animationFrame();
    click(getPickerCell("22"));
    await animationFrame();
    const [hourSelect, minuteSelect] = getTimePickers().at(0);
    select("8", { target: hourSelect });
    await animationFrame();
    select("25", { target: minuteSelect });
    await animationFrame();
    // Apply changes

    click(getPickerApplyButton());
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(0, { message: "datepicker should be closed" });

    const newExpectedDateString = "04/22/2018 08:25:00";

    expect(queryFirst(".o_field_datetime input")).toHaveValue(newExpectedDateString, {
        message: "the date should be correct in edit mode",
    });
    // save

    click(".o_list_button_save");
    await animationFrame();
    expect(queryFirst("tr.o_data_row td:not(.o_list_record_selector)")).toHaveText(
        newExpectedDateString,
        {
            message: "the selected datetime should be displayed after saving",
        }
    );
});
test.tags("desktop")(
    "multi edition of DatetimeField in list view: edit date in input",
    async () => {
        onRpc("has_group", () => true);

        await mountView({
            type: "list",
            resModel: "partner",
            arch: '<tree multi_edit="1"><field name="datetime"/></tree>',
        });

        const rows = queryAll(".o_data_row");
        // select two records and edit them
        click(queryFirst(".o_list_record_selector input", { root: rows[0] }));
        await animationFrame();
        click(queryFirst(".o_list_record_selector input", { root: rows[1] }));
        await animationFrame();

        click(queryFirst(".o_data_cell", { root: rows[0] }));
        await animationFrame();

        expect(".o_field_datetime input").toHaveCount(1);

        click(".o_field_datetime input");
        edit("10/02/2019 09:00:00", { confirm: "Enter" });
        await animationFrame();
        expect(".modal").toHaveCount(1);

        click(".modal .modal-footer .btn-primary");
        await animationFrame();

        expect(queryFirst(".o_data_row:first-child .o_data_cell")).toHaveText(
            "10/02/2019 09:00:00"
        );
        expect(queryFirst(".o_data_row:nth-child(2) .o_data_cell")).toHaveText(
            "10/02/2019 09:00:00"
        );
    }
);

test.tags("desktop")(
    "multi edition of DatetimeField in list view: clear date in input",
    async () => {
        Partner._records[1].datetime = "2017-02-08 10:00:00";
        onRpc("has_group", () => true);

        await mountView({
            type: "list",
            resModel: "partner",
            arch: '<tree multi_edit="1"><field name="datetime"/></tree>',
        });

        const rows = queryAll(".o_data_row");

        // select two records and edit them
        click(queryFirst(".o_list_record_selector input", { root: rows[0] }));
        await animationFrame();
        click(queryFirst(".o_list_record_selector input", { root: rows[1] }));
        await animationFrame();
        click(queryFirst(".o_data_cell", { root: rows[0] }));
        await animationFrame();

        expect(".o_field_datetime input").toHaveCount(1);
        click(".o_field_datetime input");
        await animationFrame();
        edit("", { confirm: "Enter" });
        await animationFrame();

        expect(".modal").toHaveCount(1);

        click(".modal .modal-footer .btn-primary");
        await animationFrame();
        expect(queryFirst(".o_data_row:first-child .o_data_cell")).toHaveText("");
        expect(queryFirst(".o_data_row:nth-child(2) .o_data_cell")).toHaveText("");
    }
);

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

    expect(queryFirst(".o_field_datetime input")).toHaveValue("02/08/2017 12:00:00", {
        message: "the date should be correct in edit mode",
    });

    click(".o_field_datetime input");
    edit("");
    await animationFrame();
    click(document.body);
    await animationFrame();

    expect(queryFirst(".o_field_datetime input")).toHaveValue("", {
        message: "should have an empty input",
    });

    // save
    await clickSave();
    expect(queryFirst(".o_field_datetime")).toHaveText("", {
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
                    <tree><field name="datetime" /></tree>
                    <form><field name="datetime" widget="date" /></form>
                </field>
            </form>`,
    });

    const expectedDateString = "02/07/2017 22:00:00"; // local time zone
    expect(".o_field_widget[name='p'] .o_data_cell").toHaveText(expectedDateString, {
        message: "the datetime (datetime widget) should be correctly displayed in tree view",
    });

    // switch to form view
    click(".o_field_widget[name='p'] .o_data_cell");
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
                    <tree><field name="datetime" /></tree>
                    <form><field name="datetime" widget="date" /></form>
                </field>
            </form>`,
    });

    const expectedDateString = "02/08/2017 06:00:00"; // with timezone
    expect(queryFirst(".o_field_widget[name='p'] .o_data_cell")).toHaveText(expectedDateString, {
        message: "the datetime (datetime widget) should be correctly displayed in tree view",
    });

    // switch to form view
    click(".o_field_widget[name='p'] .o_data_cell");
    await animationFrame();
    expect(queryFirst(".modal .o_field_date[name='datetime'] input")).toHaveValue(
        "02/08/2017 06:00:00",
        {
            message: "the datetime (date widget) should be correctly displayed in form view",
        }
    );
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
    click(queryFirst(".o_field_datetime input"));
    edit("01/08/22 14:30:40", { confirm: "Enter" });

    const datetimeValue = `01/08/2022 14:30:40`;

    expect(queryFirst(".o_field_datetime input")).toHaveValue(datetimeValue);

    // Click outside the field to check that the field is not changed
    click(document.body);
    expect(queryFirst(".o_field_datetime input")).toHaveValue(datetimeValue);

    // Save and check that it's still ok
    await clickSave();

    expect(queryFirst(".o_field_datetime input")).toHaveValue(datetimeValue);
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

    click(queryFirst("label.o_form_label"));
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

    expect(queryFirst("[name=datetime] input")).toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٠٠:٠٠");

    click(queryFirst("[name=datetime] input"));
    await animationFrame();
    select(45, { target: getTimePickers()[0][1] });
    await animationFrame();
    expect(queryFirst("[name=datetime] input")).toHaveValue("٠٢/٠٨/٢٠١٧ ١١:٤٥:٠٠");
});
