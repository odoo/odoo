import { after, beforeEach, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    Deferred,
    edit,
    press,
    queryAll,
    queryAllProperties,
    queryAllTexts,
    queryAllValues,
    queryFirst,
    queryValue,
    resize,
} from "@odoo/hoot-dom";
import { disableAnimations, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { resetDateFieldWidths } from "@web/views/list/column_width_hook";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    pagerNext,
    patchWithCleanup,
} from "../../web_test_helpers";
import { _makeUser, user } from "@web/core/user";

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

    disableAnimations();
});

test("Datetime field without daterange widget", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime"/>
            </form>`,
    });

    await contains("button[data-field=datetime]").click();
    expect(".o_datetime_picker").toBeDisplayed();
    expect(".o_toggle_range").toHaveCount(0);
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
    await contains(".o_field_daterange:first button[data-field=datetime]").click();

    expect(".o_datetime_picker").toBeDisplayed();

    expect(".o_date_item_cell.o_select_start").toHaveText("8");
    await contains("button.o_next").click();
    expect(".o_date_item_cell.o_select_end").toHaveText("13");

    let [timeInputStart, timeInputEnd] = queryAll(".o_time_picker_input");
    expect(timeInputStart).toHaveValue("15:30");
    expect(timeInputEnd).toHaveValue("5:30");

    await click(timeInputStart);
    await animationFrame();
    expect(".o_time_picker_option").toHaveCount(24 * 4);
    // Close picker
    await contains(".o_form_view_container").click();
    expect(".o_datetime_picker").toHaveCount(0);

    // Try to check with end date
    await contains(".o_field_daterange:first button[data-field=datetime_end]").click();

    expect(".o_datetime_picker").toBeDisplayed();

    expect(".o_date_item_cell.o_select_end").toHaveText("13");
    await contains("button.o_previous").click();
    expect(".o_date_item_cell.o_select_start").toHaveText("8");

    [timeInputStart, timeInputEnd] = queryAll(".o_time_picker_input");
    expect(timeInputStart).toHaveValue("15:30");
    expect(timeInputEnd).toHaveValue("5:30");

    await click(timeInputStart);
    await animationFrame();
    expect(".o_time_picker_option").toHaveCount(24 * 4);

    // Select a new range and check that inputs are updated
    await contains(getPickerCell("8").at(0)).click(); // 02/08/2017
    await contains(getPickerCell("9").at(0)).click(); // 02/09/2017

    // Save
    await clickSave();

    // Check date after save
    expect("button[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("02/09/2017 05:30:00");
});

test("Datetime field - interaction with the datepicker (same initial dates)", async () => {
    Partner._records[0].datetime_end = "2017-02-08 15:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
    });
    expect("button[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("02/08/2017 20:30:00");
    await contains("button[data-field=datetime]").click();
    expect(".o_date_item_cell.o_select_start").toHaveText("8");
    expect(".o_date_item_cell.o_select_end").toHaveText("8");
    expect("input[data-field=datetime]").toBeFocused();
    await contains(getPickerCell("8").at(0)).click();
    await animationFrame();
    expect("input[data-field=datetime_end]").toBeFocused();
    await contains(getPickerCell("10").at(0)).click();
    await animationFrame();
    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("02/10/2017 20:30:00");
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
    await contains("button[data-field=date]").click();
    expect(".o_datetime_picker:first").toBeDisplayed();
    expect(".o_select_start").toHaveText("3");
    expect(".o_select_end").toHaveText("8");

    // Change date
    await contains(getPickerCell("16")).click(); // 2017-02-16
    await contains("button.o_next").click();
    await contains(getPickerCell("12")).click(); // 2017-03-12

    // Close picker
    await contains(".o_form_view").click();

    // Check date after change
    expect(".o_datetime_picker:first").not.toHaveCount();
    expect("button[data-field=date]").toHaveValue("02/16/2017");
    expect("button[data-field=date_end]").toHaveValue("03/12/2017");

    // Try to change range with end date
    await contains("button[data-field=date_end]").click();

    expect(".o_datetime_picker:first").toBeDisplayed();
    expect(".o_select_end").toHaveText("12");
    await contains("button.o_previous").click();
    expect(".o_select_start").toHaveText("16");

    // Change date
    await contains(getPickerCell("13")).click();
    await contains("button.o_next").click();
    await contains(getPickerCell("18")).click();
    // Close picker
    await contains(".o_form_view").click();

    // Check date after change
    expect(".o_datetime_picker:first").not.toHaveCount();
    expect("button[data-field=date]").toHaveValue("02/13/2017");
    expect("button[data-field=date_end]").toHaveValue("03/18/2017");

    // Save
    await clickSave();

    // Check date after save
    expect("button[data-field=date]").toHaveValue("02/13/2017");
    expect("button[data-field=date_end]").toHaveValue("03/18/2017");
});

test("Date field - interaction with the datepicker - empty dates", async () => {
    Partner._fields.date_start = fields.Date({ string: "Date end", required: true });
    Partner._fields.date_end = fields.Date({ string: "Date end", required: true });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="date_start" widget="daterange" options="{'end_date_field': 'date_end'}"/>
            </form>`,
    });

    // open the first one
    await contains("input[data-field=date_start]").click();

    expect(".o_select_start").not.toHaveCount();
    expect(".o_select_end").not.toHaveCount();

    // Change date
    await contains(getPickerCell("5")).click();
    await contains(getPickerCell("12")).click();

    expect(".o_select_start").toHaveText("5");
    expect(".o_select_end").toHaveText("12");
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

    await contains("button[data-field=datetime]").click();
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
    expect("button[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 05:30:00");

    // update input for Datetime
    await contains("button[data-field=datetime]").click();
    await contains("input[data-field=datetime]").edit("02/08/2017 11:30:00");
    // save form
    await clickSave();

    expect("button[data-field=datetime]").toHaveValue("02/08/2017 11:30:00");
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
    expect("button[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 05:30:00");

    // reveal the o_datetime_picker
    await contains("button[data-field=datetime]").click();

    // the keyup event should not be handled by o_datetime_picker
    await contains("input[data-field=datetime]").press("ArrowLeft");
    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 05:30:00");
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
    expect("button[data-field=date]").toHaveValue("08/14/2014");

    // Reopen the datepicker
    await contains("button[data-field=date]").click();

    // Add an end date
    await contains(".o_toggle_range").click();
    await press("Enter");
    await animationFrame();
    expect("button[data-field=date]").toHaveValue(queryValue("button[data-field=date_end]"));
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
    expect(".o_datetime_picker").toBeVisible();
    expect(".o_toggle_range").toBeVisible();

    // Select a value (today)
    await contains(".o_today").click();
    expect(".o_field_daterange input:eq(0)").toHaveValue("08/14/2014 12:00:00");

    // Add an end date
    await contains(".o_toggle_range").click();

    expect("input[data-field=datetime]").toHaveValue("08/14/2014 12:00:00");
    expect("button[data-field=datetime_end]").toHaveValue("08/14/2014 13:00:00");
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
    expect(".o_toggle_range").toHaveCount(1);

    // Select a value (today)
    await contains(".o_today").click();
    expect(".o_field_daterange input:eq(0)").toHaveValue("08/14/2014 13:00:00");
    expect(".o_toggle_range").toBeVisible();

    // Add an end date
    await contains(".o_toggle_range").click();

    expect("button[data-field=datetime]").toHaveValue("08/14/2014 12:00:00");
    expect("input[data-field=datetime_end]").toHaveValue("08/14/2014 13:00:00");
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

    await contains("button.o_daterange_start").click();
    expect(".o_datetime_picker").toHaveCount(1);

    // Add an end date
    await contains(".o_toggle_range").click();

    expect(".o_datetime_picker").toHaveCount(1);
    expect("input[data-field=datetime]").toHaveValue("03/13/2017 00:00:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 01:00:00");
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

    await contains("button.o_daterange_end").click();
    expect(".o_datetime_picker").toHaveCount(1);

    // Add a start date
    await contains(".o_toggle_range").click();

    expect("button[data-field=datetime]").toHaveValue("03/12/2017 23:00:00");
    expect("input[data-field=datetime_end]").toHaveValue("03/13/2017 00:00:00");
});

test("Datetime field - open datepicker and toggle range with optional end date", async () => {
    mockDate("2014-08-14 12:34:56", +0);

    Partner._records[0].datetime = "2017-03-13 00:00:00";
    Partner._records[0].datetime_end = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    await contains("button[data-field=datetime]").click();
    expect(".o_datetime_picker").toHaveCount(1);
    expect("input[data-field=datetime]").toHaveValue("03/13/2017 00:00:00");
    expect("button[data-field=datetime_end]").toHaveCount(0);
    expect(".o_time_picker_input").toHaveValue("0:00");

    // Range mode: on (add a end date)
    await contains(".o_toggle_range").click();
    await animationFrame();
    expect("input[data-field=datetime]").toHaveValue("03/13/2017 00:00:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 01:00:00");

    // Range mode: off
    await contains(".o_toggle_range").click();
    await animationFrame();
    expect("input[data-field=datetime]").toHaveValue("03/13/2017 00:00:00");
    expect("button[data-field=datetime_end]").toHaveCount(0);
    expect(".o_time_picker_input").toHaveValue("0:00");
});

test("Datetime field - open datepicker and toggle range with optional start date", async () => {
    mockDate("2014-08-14 12:34:56", +0);

    Partner._records[0].datetime = false;
    Partner._records[0].datetime_end = "2017-03-13 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
            </form>`,
        resId: 1,
    });

    await contains("button[data-field=datetime_end]").click();
    expect(".o_datetime_picker").toHaveCount(1);
    expect("button[data-field=datetime]").toHaveCount(0);
    expect("input[data-field=datetime_end]").toHaveValue("03/13/2017 00:00:00");
    expect(".o_time_picker_input").toHaveValue("0:00");

    // Range mode: on (add a end date)
    await contains(".o_toggle_range").click();
    await animationFrame();
    expect("input[data-field=datetime]").toHaveValue("03/12/2017 23:00:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 00:00:00");

    // Range mode: off
    await contains(".o_toggle_range").click();
    await animationFrame();
    expect("button[data-field=datetime]").toHaveCount(0);
    expect("input[data-field=datetime_end]").toHaveValue("03/13/2017 00:00:00");
    expect(".o_time_picker_input").toHaveValue("0:00");
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
    await contains("button[data-field=datetime]").click();

    expect(".o_datetime_picker:first").toBeDisplayed();

    // Start date: id=1
    expect(".o_select_start").toHaveText("8");
    // End date: id=1
    await contains("button.o_next").click();
    expect(".o_select_end").toHaveText("13");

    let [timePickerStart, timePickerEnd] = queryAll(".o_time_picker_input");
    expect(timePickerStart).toHaveValue("15:30");
    expect(timePickerEnd).toHaveValue("5:30");

    // Close picker
    await contains(".o_form_view").click();
    expect(".o_datetime_picker:first").not.toHaveCount();

    await pagerNext();

    // Check date range picker initialization
    expect(".o_field_daterange").toHaveCount(1);
    expect(".o_datetime_picker").toHaveCount(0);

    // open date range picker
    await contains("button[data-field=datetime]").click();

    expect(".o_datetime_picker:first").toBeDisplayed();

    // Start date: id=2
    expect(".o_select_start").toHaveText("10");
    // End date id=2
    await contains("button.o_next").click();
    expect(".o_select_end").toHaveText("15");

    [timePickerStart, timePickerEnd] = queryAll(".o_time_picker_input");
    expect(timePickerStart).toHaveValue("16:30");
    expect(timePickerEnd).toHaveValue("5:30");
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
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");
    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");

    await contains("input[data-field=datetime]").click();
    await contains(".o_toggle_range").click();

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange button").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button").toHaveValue("06/06/2023 13:00:00");

    await press("Enter");
    await animationFrame();
    expect(".o_toggle_range").toHaveCount(0);
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
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_boolean input").click();
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange input:eq(1)").edit("07/07/2023 13:00:00");
    expect(".o_field_daterange input").toHaveCount(0);
    expect(".o_field_daterange button").toHaveCount(2);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange button:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange button:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange button[data-field=datetime]").click();
    await contains(".o_field_daterange input[data-field=datetime]").clear();
    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input").toHaveValue("");
    expect(".o_field_daterange button").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button").toHaveValue("07/07/2023 13:00:00");
    expect(".o_toggle_range").toHaveCount(0);

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
    expect(".o_toggle_range").toHaveCount(0);
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

    expect(".o_field_daterange button").toHaveCount(1);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");

    // Open the datepicker
    await contains("button[data-field=datetime]").click();
    expect(".o_toggle_range").toBeVisible();
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

    expect(".o_field_daterange button").toHaveCount(1);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");

    // Open the datepicker
    await contains("button[data-field=datetime]").click();
    expect(".o_toggle_range").toBeVisible();
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

    expect(".o_field_daterange button").toHaveCount(1);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime_end");

    // Open the datepicker
    await contains("button[data-field=datetime_end]").click();
    expect(".o_toggle_range").toBeVisible();
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

    expect(".o_field_daterange button").toHaveCount(1);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime_end");

    // Open the datepicker
    await contains("button[data-field=datetime_end]").click();
    expect(".o_toggle_range").toBeVisible();
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

    expect(".o_field_daterange button").toHaveCount(2);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange button:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_toggle_range").toHaveCount(0);
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

    expect(".o_field_daterange button").toHaveCount(2);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange button:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange button:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button:eq(1)").toHaveValue("02/08/2017 15:30:00");
    await contains(".o_field_daterange button:eq(0)").click();
    await contains(".o_field_daterange input").clear();
    expect(".o_field_daterange button[data-field]").toHaveCount(1);
    expect(".o_field_daterange button[data-field]").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button[data-field]").toHaveValue("02/08/2017 15:30:00");
    await contains(".o_field_daterange button[data-field]").click();
    await contains(".o_field_daterange input").clear();
    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input").toHaveValue("");
    expect(".o_toggle_range").toHaveCount(0);
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

    expect(".o_field_daterange button:eq(0)").toHaveValue("02/03/2017");
    expect(".fa-long-arrow-right").toHaveCount(1);
    expect(".o_field_daterange button:eq(1)").toHaveValue("02/03/2017");
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

    expect(".o_field_daterange").toHaveText("Feb 3, 2017");
    expect(".o_field_daterange .fa-long-arrow-right").toHaveCount(0);
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

    expect(".o_field_daterange").toHaveText("Feb 3, 2017");
    expect(".o_field_daterange .fa-long-arrow-right").toHaveCount(0);
});

test("list daterange: column widths", async () => {
    await resize({ width: 800 });
    patchWithCleanup(user, _makeUser({ user_context: { lang: "fr" } }));
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);
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
    expect(columnWidths).toEqual([40, 220, 352, 188]);
});

test("list daterange: column widths (numeric format)", async () => {
    await resize({ width: 800 });
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    Partner._fields.char_field = fields.Char();
    Partner._fields.date_end = fields.Date();
    Partner._records[0].date_end = "2017-02-04";
    Partner._records[0].datetime_end = "2017-02-09 17:00:00";

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="date" widget="daterange" options="{'end_date_field': 'date_end', 'numeric': true}" />
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end', 'numeric': true}" />
                <field name="char_field" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts(".o_data_cell")).toEqual([
        "02/03/2017\n02/04/2017",
        "02/08/2017 15:30:00\n02/09/2017 22:30:00",
        "",
    ]);
    const columnWidths = queryAllProperties(".o_list_table thead th", "offsetWidth");
    expect(columnWidths).toEqual([40, 187, 310, 263]);
});

test("list daterange: column widths (show_time=false)", async () => {
    await resize({ width: 800 });
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);

    Partner._fields.char_field = fields.Char();
    Partner._fields.date_end = fields.Date();
    Partner._records[0].date_end = "2017-02-04";
    Partner._records[0].datetime_end = "2017-02-09 17:00:00";

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list>
                <field name="datetime" widget="daterange" options="{'show_time': false, 'end_date_field': 'datetime_end'}" />
                <field name="char_field" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(1);
    expect(queryAllTexts(".o_data_cell")).toEqual(["Feb 8, 2017\nFeb 9, 2017", ""]);
    const columnWidths = queryAllProperties(".o_list_table thead th", "offsetWidth");
    expect(columnWidths).toEqual([40, 219, 541]);
});

test("list daterange: column widths (no record)", async () => {
    await resize({ width: 800 });
    patchWithCleanup(user, _makeUser({ user_context: { lang: "fr" } }));
    document.body.style.fontFamily = "sans-serif";
    resetDateFieldWidths();
    after(resetDateFieldWidths);

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
    expect(columnWidths).toEqual([40, 220, 352, 188]);
});

test.tags("desktop");
test("list daterange: start date input width matches its span counterpart", async () => {
    Partner._records[0].datetime_end = "2017-02-09 17:00:00";

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list multi_edit="1">
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end', 'numeric': true}" />
            </list>`,
    });

    expect(".o_data_row").toHaveCount(1);
    await contains(".o_list_record_selector input").click();
    const initialWidth = queryFirst(".o_field_daterange span").offsetWidth;
    await contains(".o_field_daterange span:first").click();
    await animationFrame();
    expect(".o_field_daterange input").toHaveProperty("offsetWidth", initialWidth);
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
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange input:eq(0)").edit("06/06/2023 12:00:00");
    expect(".o_field_daterange input").toHaveCount(2);
    expect(".o_field_daterange input:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange input:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange input:eq(1)").toHaveValue("");
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange input:eq(1)").edit("07/07/2023 13:00:00");
    await animationFrame();

    expect(".o_field_daterange button").toHaveCount(2);
    expect(".o_field_daterange button:eq(0)").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange button:eq(0)").toHaveValue("06/06/2023 12:00:00");
    expect(".o_field_daterange button:eq(1)").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button:eq(1)").toHaveValue("07/07/2023 13:00:00");
    expect(".o_toggle_range").toHaveCount(0);
    await contains(".o_field_daterange button:eq(0)").click();
    await contains(".o_field_daterange input").clear();
    await animationFrame();

    expect(".o_field_daterange input").toHaveCount(1);
    expect(".o_field_daterange input").toHaveAttribute("data-field", "datetime");
    expect(".o_field_daterange input").toHaveValue("");
    expect(".o_field_daterange button").toHaveAttribute("data-field", "datetime_end");
    expect(".o_field_daterange button").toHaveValue("07/07/2023 13:00:00");
    expect(".o_toggle_range").toHaveCount(0);
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

    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(0);
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

    expect(".o_field_daterange button").toHaveCount(2);
    await contains(".o_field_daterange button:eq(1)").click();
    await contains("input[data-field=date_end]").clear();
    await contains(".o_form_view").click();
    expect(".o_field_daterange input").toHaveValue("");
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

    expect(".o_field_daterange button").toHaveCount(2);
    await contains(".o_field_daterange button:eq(0)").click();
    await contains("input[data-field=date]").clear();
    await contains(".o_form_view").click();
    expect(".o_field_daterange input").toHaveValue("");
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

    await contains(".o_field_datetime button").click();
    await contains(getPickerCell("19")).click();
    await contains(".o_toggle_range").click();
    await press("enter");

    expect(".o_field_datetime input").toHaveValue("02/19/2017 15:30:00");
    expect(".o_field_datetime button").toHaveValue("02/19/2017 16:30:00");
    expect.verifySteps([]);

    def.resolve();
    await animationFrame();

    expect(queryAllValues(".o_field_datetime button")).toEqual([
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
    await contains("button[data-field=date]").click();
    await contains("input[data-field=date]").press("Backspace");
    await contains(getPickerCell("12")).click();
    await animationFrame();

    expect("button[data-field=date]").toHaveValue("02/12/2017");
});

test("daterange with inverted start date and end date", async () => {
    Partner._records[0].datetime_end = "2017-02-01 00:00:00";

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
        resId: 1,
    });

    expect(".o_field_daterange button:eq(0)").toHaveValue("02/08/2017 15:30:00");
    expect(".o_field_daterange button:eq(1)").toHaveValue("02/01/2017 05:30:00");

    await contains("button[data-field=datetime]").click();

    expect(".o_selected").toHaveCount(8, {
        message: "should correctly display the range even if invalid",
    });
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

    expect(queryAllTexts(".o_field_daterange span")).toEqual(["Feb 8, 2017", "Mar 13, 2017"]);
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

    expect("button[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/13/2017 05:32:00");

    await contains("button[data-field=datetime_end]").click();

    expect(".o_time_picker:first .o_time_picker_input").toHaveValue("15:30");
    expect(".o_time_picker:last .o_time_picker_input").toHaveValue("5:32");

    await click(getPickerCell("16").at(-1));
    await animationFrame();
    await contains(".o_time_picker:eq(1) .o_time_picker_input").edit("5:05", { confirm: "Enter" });
    await animationFrame();

    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:30:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/16/2017 05:05:00");
    expect(".o_time_picker:first .o_time_picker_input").toHaveValue("15:30");
    expect(".o_time_picker:last .o_time_picker_input").toHaveValue("5:05");

    await contains(".o_time_picker:eq(0) .o_time_picker_input").click();
    await animationFrame();
    await edit("15:35", { confirm: "enter" });
    await animationFrame();

    expect("input[data-field=datetime]").toHaveValue("02/08/2017 15:35:00");
    expect("button[data-field=datetime_end]").toHaveValue("03/16/2017 05:05:00");
    expect(".o_time_picker:first .o_time_picker_input").toHaveValue("15:35");
    expect(".o_time_picker:last .o_time_picker_input").toHaveValue("5:05");
});

test("daterange in readonly with same dates but different hours", async () => {
    Partner._records[0].datetime_end = "2017-02-08 17:00:00";
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form edit="0">
                <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
            </form>`,
    });
    expect(".o_field_daterange").toHaveText("Feb 8, 2017, 3:30 PM\n10:30 PM", {
        message: "end date only shows time since it has the same day as start date",
    });
});

test("daterange in list view with missing first date", async () => {
    Partner._records[0].datetime_end = Partner._records[0].datetime;
    Partner._records[0].datetime = false;

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
            <list multi_edit="1">
                <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}" />
            </list>
        `,
    });

    expect(".o_field_daterange[name=datetime_end]").toHaveText("Feb 8, 2017, 3:30 PM");
});
