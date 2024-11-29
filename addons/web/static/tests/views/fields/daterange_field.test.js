import { beforeEach, expect, test } from "@odoo/hoot";
import {
    click,
    queryAll,
    queryAllProperties,
    queryAllTexts,
    queryAllValues,
    queryFirst,
    queryValue,
    resize,
    select,
} from "@odoo/hoot-dom";
import { animationFrame, Deferred, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { getTimePickers } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    pagerNext,
} from "../../web_test_helpers";

function getPickerCell(expr) {
    return queryAll(`.o_datetime_picker .o_date_item_cell:contains(/^${expr}$/)`);
}

class Partner extends models.Model {
    date = fields.Date({ string: "A date", searchable: true });
    datetime = fields.Datetime({ string: "A datetime", searchable: true });
    datetime_end = fields.Datetime({ string: "Datetime End" });
    bool_field = fields.Boolean({ string: "A boolean" });
    _records = [
        {
            id: 1,
            date: "2017-02-03",
            datetime: "2017-02-08 10:00:00",
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

beforeEach(() => {
    // Date field should not have an offset as they are ignored.
    // However, in the test environement, a UTC timezone is set to run all tests. And if any code does not use the safe timezone method
    // provided by the framework (which happens in this case inside the date range picker lib), unexpected behavior kicks in as the timezone
    // of the dev machine collides with the timezone set by the test env.
    // To avoid failing test on dev's local machines, a hack is to apply an timezone offset greater than the difference between UTC and the dev's
    // machine timezone. For belgium, > 60 is enough. For India, > 5h30 is required, hence 330.
    mockTimeZone(+5.5);
});

test.tags("desktop");
test("Datetime field - interaction with the datepicker", async () => {
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
    });

    // Check date range picker initialization
    expect(".o_field_daterange").toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);

    // open the first one
    const daterange = queryFirst(".o_field_daterange");
    await contains("input[data-field=datetime]", { root: daterange }).click();

    expect(".o_datetime_picker").toBeDisplayed();

    expect(".o_date_item_cell.o_select_start").toHaveText("8");
    let [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
    expect(hourSelectStart).toHaveValue("15");
    expect(minuteSelectStart).toHaveValue("30");
    expect(".o_date_item_cell.o_select_end").toHaveText("13");
    let [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
    expect(hourSelectEnd).toHaveValue("5");
    expect(minuteSelectEnd).toHaveValue("30");
    expect(queryAll("option", { root: minuteSelectStart })).toHaveCount(12);
    // Close picker
    await contains(".o_form_view_container").click();
    expect(".o_datetime_picker").toHaveCount(0);

    // Try to check with end date
    await contains("input[data-field=datetime_end]", { root: daterange }).click();

    expect(".o_datetime_picker").toBeDisplayed();

    expect(".o_date_item_cell.o_select_start").toHaveText("8");
    [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
    expect(hourSelectStart).toHaveValue("15");
    expect(minuteSelectStart).toHaveValue("30");
    expect(".o_date_item_cell.o_select_end").toHaveText("13");
    [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
    expect(hourSelectEnd).toHaveValue("5");
    expect(minuteSelectEnd).toHaveValue("30");
    expect(queryAll("option", { root: minuteSelectStart })).toHaveCount(12);
    // Select a new range and check that inputs are updated
    await contains(getPickerCell("8").at(0)).click(); // 02/08/2017
    await contains(getPickerCell("9").at(0)).click(); // 02/09/2017

    // Save
    await clickSave();

    // Check date after save
    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("input[data-field=datetime_end]").toHaveValue("02/09/2017 05:30:00");
});

test.tags("desktop");
test("Date field - interaction with the datepicker", async () => {
    Partner._fields.date_end = fields.Date({ string: "Date end" });
    Partner._records[0].date_end = "2017-02-08";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </form>`,
    });

    // Check date range picker initialization
    expect(".o_field_daterange").toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);

    // open the first one
    await contains("input[data-field=date]").click();
    let datepicker = queryFirst(".o_datetime_picker");
    expect(datepicker).toBeDisplayed();
    expect(".o_select_start").toHaveText("3");
    expect(".o_select_end").toHaveText("8");

    // Change date
    await contains(getPickerCell("16").at(0)).click(); // 2017-02-16
    await contains(getPickerCell("12").at(1)).click(); // 2017-03-12

    // Close picker
    await contains(".o_form_view").click();

    // Check date after change
    expect(datepicker).not.toBeDisplayed();
    expect("input[data-field=date]").toHaveValue("02/16/2017");
    expect("input[data-field=date_end]").toHaveValue("03/12/2017");

    // Try to change range with end date
    await contains("input[data-field=date_end]").click();
    datepicker = queryFirst(".o_datetime_picker");

    expect(datepicker).toBeDisplayed();
    expect(".o_select_start").toHaveText("16");
    expect(".o_select_end").toHaveText("12");

    // Change date
    await contains(getPickerCell("13").at(0)).click();
    await contains(getPickerCell("18").at(1)).click();
    // Close picker
    await contains(".o_form_view").click();

    // Check date after change
    expect(datepicker).not.toBeDisplayed();
    expect("input[data-field=date]").toHaveValue("02/13/2017");
    expect("input[data-field=date_end]").toHaveValue("03/18/2017");

    // Save
    await clickSave();

    // Check date after save
    expect("input[data-field=date]").toHaveValue("02/13/2017");
    expect("input[data-field=date_end]").toHaveValue("03/18/2017");
});

test("date picker should still be present when scrolling outside of it", async () => {
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
    });

    await contains("input[data-field=datetime]").click();
    expect(".o_datetime_picker").toBeDisplayed();
    await contains(document.body).scroll({ top: 50 });
    expect(".o_datetime_picker").toBeDisplayed();
});

test("DateRangeField with label opens datepicker on click", async () => {
    Partner._fields.date_end = fields.Date({ string: "Date end" });
    Partner._records[0].date_end = "2017-02-08";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <label for="date" string="Daterange" />
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </form>`,
    });

    await contains("label.o_form_label").click();
    expect(".o_datetime_picker").toBeDisplayed();
});

test("Datetime field manually input value should send utc value to server", async () => {
    expect.assertions(4);

    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({
            datetime: "2017-02-08 06:00:00",
        });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    // check date display correctly in readonly
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange input:eq(1)").toHaveValue("03/13/2017 05:30:00");

    // update input for Datetime
    await contains("input[data-field=datetime]").edit("02/08/2017 11:30:00");
    // save form
    await clickSave();

    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 11:30:00");
});

test("Daterange field keyup should not erase end date", async () => {
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
        resId: 1,
    });

    // check date display correctly in readonly
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange input:eq(1)").toHaveValue("03/13/2017 05:30:00");

    // reveal the o_datetime_picker
    await contains("input[data-field=datetime]").click();

    // the keyup event should not be handled by o_datetime_picker
    await contains("input[data-field=datetime]").press("ArrowLeft");
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange input:eq(1)").toHaveValue("03/13/2017 05:30:00");
});

test("Render with initial empty value: date field", async () => {
    // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
    mockDate("22014-08-14 12:34:56", +0);
    Partner._fields.date_end = fields.Date({ string: "Date end" });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </form>`,
    });

    await contains("input[data-field=date]").click();
    expect(".o_datetime_picker").toHaveCount(1);

    // Select a value (today)
    await contains(".o_today").click();
    expect(".o_field_daterange input:eq(0)").toHaveValue("08/14/2014");

    // Add an end date
    await animationFrame();
    await contains(".o_add_date:enabled", { visible: false }).click();
    expect(".o_field_daterange input:eq(0)").toHaveValue(
        queryValue(".o_field_daterange input:eq(1)")
    );
});

test("Render with initial empty value: datetime field", async () => {
    // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
    mockDate("2014-08-14 12:34:56", +0);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
    });

    await contains("input[data-field=datetime]").click();

    expect(".o_datetime_picker").toHaveCount(1);
    expect(".o_add_date").toHaveCount(0);

    // Select a value (today)
    await contains(".o_today").click();

    expect(".o_field_daterange input:eq(0)").toHaveValue("08/14/2014 12:00:00");
    expect(".o_add_date").toBeVisible();

    expect(".o_add_date").toHaveText("Add end date");

    // Add an end date
    await contains(".o_add_date:enabled").click();

    expect(queryAllValues(".o_field_daterange input")).toEqual([
        "08/14/2014 12:00:00",
        "08/14/2014 13:00:00",
    ]);
});

test("Render with initial empty value and optional start date", async () => {
    mockDate("2014-08-14 12:34:56", +0);

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
    });

    await contains("input[data-field=datetime_end]").click();
    expect(".o_datetime_picker").toHaveCount(1);
    expect(".o_add_date").toHaveCount(0);

    // Select a value (today)
    await contains(".o_today").click();
    expect(".o_field_daterange input:eq(0)").toHaveValue("08/14/2014 13:00:00");
    expect(".o_add_date").toBeVisible();
    expect(".o_add_date").toHaveText("Add start date");

    // Add an end date
    await contains(".o_add_date:enabled").click();

    expect(queryAllValues(".o_field_daterange input")).toEqual([
        "08/14/2014 12:00:00",
        "08/14/2014 13:00:00",
    ]);
});

test("initial empty date with optional start date", async () => {
    mockDate("2014-08-14 12:34:56", +0);

    Partner._records[0].datetime = "2017-03-13 00:00:00";
    Partner._records[0].datetime_end = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_add_date").not.toBeVisible();
    contains(".o_field_daterange input").focus();
    await animationFrame();
    expect(".o_add_date").toBeVisible();
    expect(".o_datetime_picker").toHaveCount(0);
    expect(".o_add_date").toHaveText("Add end date");

    // Add an end date
    await contains(".o_add_date:enabled").click();

    expect(".o_datetime_picker").toHaveCount(1);
    expect(queryAllValues(".o_field_daterange input")).toEqual([
        "03/13/2017 00:00:00",
        "03/13/2017 01:00:00",
    ]);
});

test("initial empty date with optional end date", async () => {
    // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
    mockDate("2014-08-14 12:34:56", +0);

    Partner._records[0].datetime = false;
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_add_date").not.toBeVisible();
    await contains(".o_field_daterange input").focus();
    await animationFrame();
    expect(".o_add_date").toBeVisible();
    expect(".o_add_date").toHaveText("Add start date");

    // Add a start date
    await contains(".o_add_date:enabled").click();

    expect(queryAllValues(".o_field_daterange input")).toEqual([
        "03/12/2017 23:00:00",
        "03/13/2017 00:00:00",
    ]);
});

test.tags("desktop");
test("select a range in the month on the right panel", async () => {
    mockDate("2014-08-14 12:34:56", +0);

    Partner._records[0].datetime = false;
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_add_date").not.toBeVisible();
    await contains(".o_field_daterange input").focus();
    expect(".o_add_date").toBeVisible();
    expect(".o_add_date").toHaveText("Add start date");

    // Add a start date
    await contains(".o_add_date").click();

    expect(queryAllValues(".o_field_daterange input")).toEqual([
        "03/12/2017 23:00:00",
        "03/13/2017 00:00:00",
    ]);

    await contains(getPickerCell("19").at(1)).click();
    await contains(getPickerCell("9").at(1)).click();

    // verify that the panels are not shifted
    expect(queryAllTexts(".o_header_part")).toEqual(["March 2017", "April 2017"]);
});

test.tags("desktop");
test("Datetime field - open datepicker and switch page", async () => {
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";
    Partner._records.push({
        id: 2,
        date: "2017-03-04",
        datetime: "2017-03-10 11:00:00",
        datetime_end: "2017-04-15 00:00:00",
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        resIds: [1, 2],
        arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
    });

    // Check date range picker initialization
    expect(".o_field_daterange").toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);

    // open datepicker
    await contains("input[data-field=datetime]").click();

    let datepicker = queryFirst(".o_datetime_picker");
    expect(datepicker).toBeDisplayed();

    // Start date: id=1
    expect(".o_select_start").toHaveText("8");
    let [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
    expect(hourSelectStart).toHaveValue("15");
    expect(minuteSelectStart).toHaveValue("30");
    // End date: id=1
    expect(".o_select_end").toHaveText("13");
    let [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
    expect(hourSelectEnd).toHaveValue("5");
    expect(minuteSelectEnd).toHaveValue("30");

    // Close picker
    await contains(".o_form_view").click();
    expect(datepicker).not.toBeDisplayed();

    await pagerNext();

    // Check date range picker initialization
    expect(".o_field_daterange").toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);

    // open date range picker
    await contains("input[data-field=datetime]").click();

    datepicker = queryFirst(".o_datetime_picker");
    expect(datepicker).toBeDisplayed();

    // Start date: id=2
    expect(".o_select_start").toHaveText("10");
    [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
    expect(hourSelectStart).toHaveValue("16");
    expect(minuteSelectStart).toHaveValue("30");

    // End date id=2
    expect(".o_select_end").toHaveText("15");
    [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
    expect(hourSelectEnd).toHaveValue("5");
    expect(minuteSelectEnd).toHaveValue("30");
});

test("related end date, both start date and end date empty", async () => {
    Partner._records[0].datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");
    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_add_date").toHaveText("Add end date");
    await contains(".o_add_date:enabled").click();
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_add_date").toHaveCount(0);
});

test("required: related end date, both start date and end date empty", async () => {
    Partner._records[0].datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="bool_field"/>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}" required="bool_field"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_boolean input").click();
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(1)").edit("07/07/2023 13:00:00");
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").clear();
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_add_date").toHaveCount(0);

    // Open the picker, this checks that props validation for the picker isn't
    // broken by required being present
    await contains(".o_field_daterange input:eq(0)").click();
});

test("related start date, both start date and end date empty", async () => {
    Partner._records[0].datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
});

test("related end date, start date set and end date empty", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(queryFirst(".o_add_date").textContent.trim()).toBe("Add end date");
});

test("related start date, start date set and end date empty", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(queryFirst(".o_add_date").textContent.trim()).toBe("Add end date");
});

test("related end date, start date empty and end date set", async () => {
    const recordData = Partner._records[0];
    recordData.datetime_end = recordData.datetime;
    recordData.datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime_end");
    expect(queryFirst(".o_add_date").textContent.trim()).toBe("Add start date");
});

test("related start date, start date empty and end date set", async () => {
    const recordData = Partner._records[0];
    recordData.datetime_end = recordData.datetime;
    recordData.datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime_end");
    expect(queryFirst(".o_add_date").textContent.trim()).toBe("Add start date");
});

test("related end date, both start date and end date set", async () => {
    const recordData = Partner._records[0];
    recordData.datetime_end = recordData.datetime;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_add_date").toHaveCount(0);
});

test("related start date, both start date and end date set", async () => {
    const recordData = Partner._records[0];
    recordData.datetime_end = recordData.datetime;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").clear();
    expect(queryAll(".o_field_daterange input")).toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(queryFirst(".o_add_date").textContent.trim()).toBe("Add start date");
    await contains(".o_field_daterange input:eq(0)").clear();
    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
});

test("related start date, required, both start date and end date set", async () => {
    Partner._fields.date_end = fields.Date({ string: "Some Date" });
    const [firstRecord] = Partner._records;
    firstRecord.date_end = firstRecord.date;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="date" widget="daterange" options="{'start_date_field': 'date_end'}" required="1" />
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input:eq(0)").toHaveValue("02/03/2017");
    expect(".fa-long-arrow-right").toHaveCount(1);
    expect(".o_field_daterange input:eq(1)").toHaveValue("02/03/2017");
});

test("list daterange with start date and empty end date", async () => {
    Partner._fields.date_end = fields.Date({ string: "Some Date" });

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
            </list>`,
    });

    const arrowIcon = queryFirst(".fa-long-arrow-right");
    const textSiblings = [...arrowIcon.parentNode.childNodes]
        .map((node) => {
            if (node === arrowIcon) {
                return "->";
            } else if (node.nodeType === Node.TEXT_NODE) {
                return node.nodeValue.trim();
            } else {
                return node.innerText?.trim();
            }
        })
        .filter(Boolean);

    expect(textSiblings).toEqual(["02/03/2017", "->"]);
});

test("list daterange with empty start date and end date", async () => {
    Partner._fields.date_end = fields.Date({ string: "Some Date" });
    const [firstRecord] = Partner._records;
    [firstRecord.date, firstRecord.date_end] = [firstRecord.date_end, firstRecord.date];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
            </list>`,
    });

    const arrowIcon = queryFirst(".fa-long-arrow-right");
    const textSiblings = [...arrowIcon.parentNode.childNodes]
        .map((node) => {
            if (node === arrowIcon) {
                return "->";
            } else if (node.nodeType === Node.TEXT_NODE) {
                return node.nodeValue.trim();
            } else {
                return node.innerText?.trim();
            }
        })
        .filter(Boolean);

    expect(textSiblings).toEqual(["->", "02/03/2017"]);
});

test("list daterange: column widths", async () => {
    await resize({ width: 800 });

    Partner._fields.char_field = fields.Char();
    Partner._fields.date_end = fields.Date();
    Partner._records[0].date_end = "2017-02-04";
    Partner._records[0].datetime_end = "2017-02-09 17:00:00";

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}" />
                <field name="char_field" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(1);
    const columnWidths = queryAllProperties(".o_list_table thead th", "offsetWidth");
    expect(columnWidths).toEqual([40, 189, 304, 267]);
});

test("list daterange: column widths (no record)", async () => {
    await resize({ width: 800 });

    Partner._fields.char_field = fields.Char();
    Partner._fields.date_end = fields.Date();
    Partner._records = [];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}" />
                <field name="char_field" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(0);
    const columnWidths = queryAllProperties(".o_list_table thead th", "offsetWidth");
    expect(columnWidths).toEqual([40, 189, 304, 267]);
});

test("always range: related end date, both start date and end date empty", async () => {
    Partner._records[0].datetime = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end', 'always_range': '1'}"/>
        </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(1)").edit("07/07/2023 13:00:00");

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_add_date").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").clear();

    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_add_date").toHaveCount(0);
});

test("there is no arrow between the dates with option always_range if nothing is set and it is readonly", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end', 'always_range': 'true'}" />
            <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end', 'always_range': 'true'}" readonly="true" />
        </form>`,
    });

    expect(".fa-long-arrow-right").toHaveCount(1);
});

test("invalid empty date with optional end date", async () => {
    Partner._fields.date_end = fields.Date({ string: "Date end" });
    Partner._records[0].date_end = "2017-02-08";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <label for="date" string="Daterange" />
            <field name="date" widget="daterange" options="{'end_date_field': 'date_end','always_range': '1'}"  string="Planned Date" required="date_end"/>
            <field name="date_end" invisible="1" required="date"/>
        </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(2);
    await contains(".o_field_daterange input:eq(1)").click();
    await contains("input[data-field=date_end]").clear();
    await contains(".o_form_view").click();
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_field_daterange").toHaveClass("o_field_invalid");
});

test("invalid empty date with optional start date", async () => {
    Partner._fields.date_end = fields.Date({ string: "Date end" });
    Partner._records[0].date_end = "2017-02-08";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <label for="date_end" string="Daterange" />
            <field name="date" invisible="1" required="date_end"/>
            <field name="date_end" widget="daterange" options="{'start_date_field': 'date','always_range': '1'}" string="Planned Date" required="date"/>
        </form>`,
        resId: 1,
    });

    expect(".o_field_daterange input").toHaveCount(2);
    await contains(".o_field_daterange input:eq(0)").click();
    await contains("input[data-field=date]").clear();
    await contains(".o_form_view").click();
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange").toHaveClass("o_field_invalid");
});

test.tags("desktop");
test("date values are selected eagerly and do not flicker", async () => {
    Partner._onChanges.datetime = () => {};

    const def = new Deferred();
    onRpc("onchange", async () => {
        await def;
        expect.step("onchange");
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    await contains(".o_field_datetime input").click();
    await contains(getPickerCell("19")).click();
    await contains(".o_add_date:enabled").click();
    await contains(".btn:contains(Apply)").click();

    expect(queryAllValues(".o_field_datetime input")).toEqual([
        "02/19/2017 15:30:00",
        "02/19/2017 16:30:00",
    ]);
    expect.verifySteps([]);

    def.resolve();
    await animationFrame();

    expect(queryAllValues(".o_field_datetime input")).toEqual([
        "02/19/2017 15:30:00",
        "02/19/2017 16:30:00",
    ]);
    expect.verifySteps(["onchange"]);
});

test("update the selected input date after removing the existing date", async () => {
    Partner._fields.date_end = fields.Date({ string: "Date end" });
    Partner._records[0].date_end = "2017-02-08";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
       <form>
            <field name="date" widget="daterange" options="{'start_date_field': 'date_end'}" required="1" />
        </form>`,
        resId: 1,
    });
    await contains("input[data-field=date]").click();
    await contains("input[data-field=date]").press("Backspace");
    await contains(getPickerCell("12")).click();

    expect("input[data-field=date]").toHaveValue("02/12/2017");
});

test("daterange field in kanban with show_time option", async () => {
    mockTimeZone(+2);
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="datetime" widget="daterange" options="{'show_time': false, 'end_date_field': 'datetime_end'}"/>
                    </t>
                </templates>
            </kanban>`,
        resId: 1,
    });

    expect(queryAllTexts(".o_field_daterange span")).toEqual(["02/08/2017", "03/13/2017"]);
});

test("updating time keeps selected dates", async () => {
    Partner._records[0].datetime_end = "2017-03-13 00:02:00";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="datetime" options="{'end_date_field': 'datetime_end'}"/>
            </form>
        `,
    });

    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("input[data-field=datetime_end]").toHaveValue("03/13/2017 05:32:00");

    await contains("input[data-field=datetime_end]").click();

    expect(".o_time_picker:first .o_time_picker_select:last").toHaveValue("30");
    expect(".o_time_picker:last .o_time_picker_select:last").not.toHaveValue();

    await click(getPickerCell("16").at(-1));
    await animationFrame();
    await click(".o_time_picker:last .o_time_picker_select:last");
    await select("5");
    await animationFrame();

    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("input[data-field=datetime_end]").toHaveValue("03/16/2017 05:05:00");
    expect(".o_time_picker:first .o_time_picker_select:last").toHaveValue("30");
    expect(".o_time_picker:last .o_time_picker_select:last").toHaveValue("5");

    await click(".o_time_picker:first .o_time_picker_select:last");
    await select("35");
    await animationFrame();

    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:35:00");
    expect("input[data-field=datetime_end]").toHaveValue("03/16/2017 05:05:00");
    expect(".o_time_picker:first .o_time_picker_select:last").toHaveValue("35");
    expect(".o_time_picker:last .o_time_picker_select:last").toHaveValue("5");
});
