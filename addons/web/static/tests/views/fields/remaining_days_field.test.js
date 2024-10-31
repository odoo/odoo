import { beforeEach, expect, test } from "@odoo/hoot";
import { click, edit, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    date = fields.Date({ string: "A date", searchable: true });
    datetime = fields.Datetime({ string: "A datetime", searchable: true });
}
beforeEach(() => {
    onRpc("has_group", () => true);
});
defineModels([Partner]);

test("RemainingDaysField on a date field in list view", async () => {
    mockDate("2017-10-08 15:35:11");

    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
        { id: 2, date: "2017-10-09" }, // tomorrow
        { id: 3, date: "2017-10-07" }, // yesterday
        { id: 4, date: "2017-10-10" }, // + 2 days
        { id: 5, date: "2017-10-05" }, // - 3 days
        { id: 6, date: "2018-02-08" }, // + 4 months (diff >= 100 days)
        { id: 7, date: "2017-06-08" }, // - 4 months (diff >= 100 days)
        { id: 8, date: false },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list><field name="date" widget="remaining_days" /></list>`,
    });

    const cells = queryAll(".o_data_cell");
    expect(cells[0]).toHaveText("Today");
    expect(cells[1]).toHaveText("Tomorrow");
    expect(cells[2]).toHaveText("Yesterday");
    expect(cells[3]).toHaveText("In 2 days");
    expect(cells[4]).toHaveText("3 days ago");
    expect(cells[5]).toHaveText("02/08/2018");
    expect(cells[6]).toHaveText("06/08/2017");
    expect(cells[7]).toHaveText("");

    expect(queryOne(".o_field_widget > div", { root: cells[0] })).toHaveAttribute(
        "title",
        "10/08/2017"
    );
    expect(queryOne(".o_field_widget > div", { root: cells[0] })).toHaveClass([
        "fw-bold",
        "text-warning",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[1] })).not.toHaveClass([
        "fw-bold",
        "text-warning",
        "text-danger",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[2] })).toHaveClass([
        "fw-bold",
        "text-danger",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[3] })).not.toHaveClass([
        "fw-bold",
        "text-warning",
        "text-danger",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[4] })).toHaveClass([
        "fw-bold",
        "text-danger",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[5] })).not.toHaveClass([
        "fw-bold",
        "text-warning",
        "text-danger",
    ]);
    expect(queryOne(".o_field_widget > div", { root: cells[6] })).toHaveClass([
        "fw-bold",
        "text-danger",
    ]);
});

test.tags("desktop")("RemainingDaysField on a date field in multi edit list view", async () => {
    mockDate("2017-10-08 15:35:11"); // October 8 2017, 15:35:11

    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
        { id: 2, date: "2017-10-09" }, // tomorrow
        { id: 8, date: false },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list multi_edit="1"><field name="date" widget="remaining_days" /></list>`,
    });

    expect(queryAllTexts(".o_data_cell").slice(0, 2)).toEqual(["Today", "Tomorrow"]);

    // select two records and edit them
    await click(".o_data_row:eq(0) .o_list_record_selector input:first");
    await animationFrame();
    await click(".o_data_row:eq(1) .o_list_record_selector input:first");
    await animationFrame();

    await click(".o_data_row:eq(0) .o_data_cell:first");
    await animationFrame();

    expect(".o_field_remaining_days input").toHaveCount(1);

    await click(".o_field_remaining_days input");
    await edit("10/10/2017", { confirm: "enter" });
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal .o_field_widget").toHaveText("In 2 days", {
        message: "should have 'In 2 days' value to change",
    });
    await click(".modal .modal-footer .btn-primary");
    await animationFrame();

    expect(".o_data_row:eq(0) .o_data_cell:first").toHaveText("In 2 days", {
        message: "should have 'In 2 days' as date field value",
    });
    expect(".o_data_row:eq(1) .o_data_cell:first").toHaveText("In 2 days", {
        message: "should have 'In 2 days' as date field value",
    });
});

test.tags("desktop");
test("RemainingDaysField, enter wrong value manually in multi edit list view", async () => {
    mockDate("2017-10-08 15:35:11"); // October 8 2017, 15:35:11
    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
        { id: 2, date: "2017-10-09" }, // tomorrow
        { id: 8, date: false },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list multi_edit="1"><field name="date" widget="remaining_days" /></list>`,
    });

    const cells = queryAll(".o_data_cell");
    const rows = queryAll(".o_data_row");

    expect(cells[0]).toHaveText("Today");
    expect(cells[1]).toHaveText("Tomorrow");

    // select two records and edit them
    await click(".o_list_record_selector input", { root: rows[0] });
    await animationFrame();
    await click(".o_list_record_selector input", { root: rows[1] });
    await animationFrame();

    await click(".o_data_cell", { root: rows[0] });
    await animationFrame();

    expect(".o_field_remaining_days input").toHaveCount(1);

    await click(".o_field_remaining_days input");
    await edit("blabla", { confirm: "enter" });
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(cells[0]).toHaveText("Today");
    expect(cells[1]).toHaveText("Tomorrow");
});

test("RemainingDaysField on a date field in form view", async () => {
    mockDate("2017-10-08 15:35:11"); // October 8 2017, 15:35:11
    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="date" widget="remaining_days" /></form>`,
    });

    expect(".o_field_widget input").toHaveValue("10/08/2017");

    expect(".o_form_editable").toHaveCount(1);
    expect("div.o_field_widget[name='date'] input").toHaveCount(1);

    await click(".o_field_remaining_days input");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1, { message: "datepicker should be opened" });

    await click(getPickerCell("9").at(0));
    await animationFrame();
    await click(".o_form_button_save");
    await animationFrame();
    expect(".o_field_widget input").toHaveValue("10/09/2017");
});

test("RemainingDaysField on a date field on a new record in form", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
                <form>
                    <field name="date" widget="remaining_days" />
                </form>`,
    });

    expect(".o_form_editable .o_field_widget[name='date'] input").toHaveCount(1);
    await click(".o_field_widget[name='date'] input");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);
});

test("RemainingDaysField in form view (readonly)", async () => {
    mockDate("2017-10-08 15:35:11"); // October 8 2017, 15:35:11
    Partner._records = [
        { id: 1, date: "2017-10-08", datetime: "2017-10-08 10:00:00" }, // today
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <field name="date" widget="remaining_days" readonly="1" />
                    <field name="datetime" widget="remaining_days" readonly="1" />
                </form>`,
    });

    expect(".o_field_widget[name='date']").toHaveText("Today");
    expect(".o_field_widget[name='date'] > div ").toHaveClass(["fw-bold", "text-warning"]);
    expect(".o_field_widget[name='datetime']").toHaveText("Today");
    expect(".o_field_widget[name='datetime'] > div ").toHaveClass(["fw-bold", "text-warning"]);
});

test("RemainingDaysField on a datetime field in form view", async () => {
    mockDate("2017-10-08 15:35:11"); // October 8 2017, 15:35:11
    Partner._records = [
        { id: 1, datetime: "2017-10-08 10:00:00" }, // today
    ];

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `<form><field name="datetime" widget="remaining_days" /></form>`,
    });
    expect(".o_field_widget input").toHaveValue("10/08/2017 11:00:00");
    expect("div.o_field_widget[name='datetime'] input").toHaveCount(1);

    await click(".o_field_widget input");
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1, { message: "datepicker should be opened" });

    await click(getPickerCell("9").at(0));
    await animationFrame();
    await click(".o_form_button_save");
    await animationFrame();
    expect(".o_field_widget input").toHaveValue("10/09/2017 11:00:00");
});

test("RemainingDaysField on a datetime field in list view in UTC", async () => {
    mockDate("2017-10-08 15:35:11", 0); // October 8 2017, 15:35:11
    Partner._records = [
        { id: 1, datetime: "2017-10-08 20:00:00" }, // today
        { id: 2, datetime: "2017-10-09 08:00:00" }, // tomorrow
        { id: 3, datetime: "2017-10-07 18:00:00" }, // yesterday
        { id: 4, datetime: "2017-10-10 22:00:00" }, // + 2 days
        { id: 5, datetime: "2017-10-05 04:00:00" }, // - 3 days
        { id: 6, datetime: "2018-02-08 04:00:00" }, // + 4 months (diff >= 100 days)
        { id: 7, datetime: "2017-06-08 04:00:00" }, // - 4 months (diff >= 100 days)
        { id: 8, datetime: false },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list><field name="datetime" widget="remaining_days" /></list>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "Today",
        "Tomorrow",
        "Yesterday",
        "In 2 days",
        "3 days ago",
        "02/08/2018",
        "06/08/2017",
        "",
    ]);

    expect(".o_data_cell .o_field_widget div:first").toHaveAttribute("title", "10/08/2017");

    const cells = queryAll(".o_data_cell div div");
    expect(cells[0]).toHaveClass(["fw-bold", "text-warning"]);
    expect(cells[1]).not.toHaveClass(["fw-bold", "text-warning", "text-danger"]);
    expect(cells[2]).toHaveClass(["fw-bold", "text-danger"]);
    expect(cells[3]).not.toHaveClass(["fw-bold", "text-warning", "text-danger"]);
    expect(cells[4]).toHaveClass(["fw-bold", "text-danger"]);
    expect(cells[5]).not.toHaveClass(["fw-bold", "text-warning", "text-danger"]);
    expect(cells[6]).toHaveClass(["fw-bold", "text-danger"]);
});

test("RemainingDaysField on a datetime field in list view in UTC+6", async () => {
    mockDate("2017-10-08 15:35:11", +6); // October 8 2017, 15:35:11, UTC+6

    Partner._records = [
        { id: 1, datetime: "2017-10-08 20:00:00" }, // tomorrow
        { id: 2, datetime: "2017-10-09 08:00:00" }, // tomorrow
        { id: 3, datetime: "2017-10-07 18:30:00" }, // today
        { id: 4, datetime: "2017-10-07 12:00:00" }, // yesterday
        { id: 5, datetime: "2017-10-09 20:00:00" }, // + 2 days
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list><field name="datetime" widget="remaining_days" /></list>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "Tomorrow",
        "Tomorrow",
        "Today",
        "Yesterday",
        "In 2 days",
    ]);
    expect(".o_data_cell .o_field_widget div:first").toHaveAttribute("title", "10/09/2017");
});

test("RemainingDaysField on a date field in list view in UTC-6", async () => {
    mockDate("2017-10-08 15:35:11", -6); // October 8 2017, 15:35:11, UTC-6

    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
        { id: 2, date: "2017-10-09" }, // tomorrow
        { id: 3, date: "2017-10-07" }, // yesterday
        { id: 4, date: "2017-10-10" }, // + 2 days
        { id: 5, date: "2017-10-05" }, // - 3 days
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list><field name="date" widget="remaining_days" /></list>`,
    });
    expect(queryAllTexts(".o_data_cell")).toEqual([
        "Today",
        "Tomorrow",
        "Yesterday",
        "In 2 days",
        "3 days ago",
    ]);
    expect(".o_data_cell .o_field_widget div:first").toHaveAttribute("title", "10/08/2017");
});

test("RemainingDaysField on a datetime field in list view in UTC-8", async () => {
    mockDate("2017-10-08 15:35:11", -8); // October 8 2017, 15:35:11, UTC-8

    Partner._records = [
        { id: 1, datetime: "2017-10-08 20:00:00" }, // today
        { id: 2, datetime: "2017-10-09 07:00:00" }, // today
        { id: 3, datetime: "2017-10-09 10:00:00" }, // tomorrow
        { id: 4, datetime: "2017-10-08 06:00:00" }, // yesterday
        { id: 5, datetime: "2017-10-07 02:00:00" }, // - 2 days
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `<list><field name="datetime" widget="remaining_days" /></list>`,
    });

    expect(queryAllTexts(".o_data_cell")).toEqual([
        "Today",
        "Today",
        "Tomorrow",
        "Yesterday",
        "2 days ago",
    ]);
});

test("RemainingDaysField with custom decoration classes", async () => {
    mockDate("2017-10-08 15:35:11");

    Partner._records = [
        { id: 1, date: "2017-10-08" }, // today
        { id: 2, date: "2017-10-09" }, // tomorrow
        { id: 3, date: "2017-10-07" }, // yesterday
        { id: 4, date: "2017-10-10" }, // + 2 days
        { id: 5, date: "2017-10-05" }, // - 3 days
        { id: 6, date: "2018-02-08" }, // + 4 months (diff >= 100 days)
        { id: 7, date: "2017-06-08" }, // - 4 months (diff >= 100 days)
        { id: 8, date: false },
    ];

    await mountView({
        type: "list",
        resModel: "partner",
        arch: /* xml */ `
                <list>
                    <field
                        name="date"
                        widget="remaining_days"
                        options="{
                            'classes': {
                                'muted': 'days &lt; -30',
                                'danger': 'days &lt; 0',
                                'success': 'days == 0',
                                'warning': 'days &gt; 30',
                                'info': 'days &gt;= 2'
                            }
                        }"
                    />
                </list>`,
    });

    const cells = queryAll(".o_data_cell div div");
    expect(cells[0]).toHaveClass("text-success");
    expect(cells[1]).not.toHaveAttribute("class");
    expect(cells[2]).toHaveClass("text-danger");
    expect(cells[3]).toHaveClass("text-info");
    expect(cells[4]).toHaveClass("text-danger");
    expect(cells[5]).toHaveClass("text-warning");
    expect(cells[6]).toHaveClass("text-muted");
    expect(cells[7]).not.toHaveAttribute("class");
});
