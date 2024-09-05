import { expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllTexts, queryOne, scroll } from "@odoo/hoot-dom";
import { animationFrame, mockDate, mockTimeZone } from "@odoo/hoot-mock";
import {
    assertDateTimePicker,
    getPickerCell,
    zoomOut,
} from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickSave,
    contains,
    defineModels,
    defineParams,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";

    date = fields.Date();
    char_field = fields.Char({ string: "Char" });

    _records = [
        {
            id: 1,
            date: "2017-02-03",
            char_field: "first char field",
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="date"/>
                        <field name="char_field"/>
                    </group>
                </sheet>
            </form>
        `,
    };
}

defineModels([Partner]);

test("toggle datepicker", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_datetime_picker").toHaveCount(0);
    await contains(".o_field_date input").click();
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    await fieldInput("char_field").click();
    expect(".o_datetime_picker").toHaveCount(0);
});

test.tags("desktop")("open datepicker on Control+Enter", async () => {
    defineParams({
        lang_parameters: {
            date_format: "%d/%m/%Y",
            time_format: "%H:%M:%S",
        },
    });
    await mountView({
        resModel: "res.partner",
        type: "form",
        arch: `
            <form>
                <field name="date"/>
            </form>
        `,
    });

    expect(".o_field_date input").toHaveCount(1);

    await press(["ctrl", "enter"]);
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    //edit the input and open the datepicker again with ctrl+enter
    await contains(".o_field_date .o_input").click();
    await edit("09/01/1997");
    await press(["ctrl", "enter"]);
    await animationFrame();
    assertDateTimePicker({
        title: "January 1997",
        date: [
            {
                cells: [
                    [-29, -30, -31, 1, 2, 3, 4],
                    [5, 6, 7, 8, [9], 10, 11],
                    [12, 13, 14, 15, 16, 17, 18],
                    [19, 20, 21, 22, 23, 24, 25],
                    [26, 27, 28, 29, 30, 31, -1],
                    [-2, -3, -4, -5, -6, -7, -8],
                ],
                daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                weekNumbers: [1, 2, 3, 4, 5, 6],
            },
        ],
    });
});
test("toggle datepicker far in the future", async () => {
    Partner._records[0].date = "9999-12-31";
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_datetime_picker").toHaveCount(0);
    await contains(".o_field_date input").click();
    expect(".o_datetime_picker").toHaveCount(1);

    // focus another field
    await fieldInput("char_field").click();
    expect(".o_datetime_picker").toHaveCount(0);
});

test("date field is empty if no date is set", async () => {
    Partner._records[0].date = false;
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_field_date input").toHaveCount(1);
    expect(".o_field_date input").toHaveValue("");
});

test("set an invalid date when the field is already set", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_field_widget[name='date'] input").toHaveValue("02/03/2017");
    await fieldInput("date").edit("invalid date");
    expect(".o_field_widget[name='date'] input").toHaveValue("02/03/2017", {
        message: "Should have been reset to the original value",
    });
});

test("set an invalid date when the field is not set yet", async () => {
    Partner._records[0].date = false;
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_field_widget[name='date'] input").toHaveValue("");
    await fieldInput("date").edit("invalid date");
    expect(".o_field_widget[name='date'] input").toHaveValue("");
});

test("value should not set on first click", async () => {
    Partner._records[0].date = false;
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    await contains(".o_field_date input").click();
    expect(".o_field_widget[name='date'] input").toHaveValue("");
    await contains(getPickerCell(22)).click();

    await contains(".o_field_date input").click();
    expect(".o_date_item_cell.o_selected").toHaveText("22");
});

test("date field in form view (with positive time zone offset)", async () => {
    mockTimeZone(2); // should be ignored by date fields
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    onRpc("web_save", ({ args }) => {
        expect.step(args[1].date);
    });

    expect(".o_field_date input").toHaveValue("02/03/2017");

    // open datepicker and select another value
    await contains(".o_field_date input").click();
    expect(".o_datetime_picker").toHaveCount(1);
    expect(".o_date_item_cell.o_selected").toHaveCount(1);

    // select 22 Feb 2017
    await zoomOut();
    await zoomOut();
    await contains(getPickerCell("2017")).click();
    await contains(getPickerCell("Feb")).click();
    await contains(getPickerCell("22")).click();
    expect(".o_datetime_picker").toHaveCount(0);
    expect(".o_field_date input").toHaveValue("02/22/2017");

    await clickSave();
    expect.verifySteps(["2017-02-22"]);
    expect(".o_field_date input").toHaveValue("02/22/2017");
});

test("date field in form view (with negative time zone offset)", async () => {
    mockTimeZone(-2); // should be ignored by date fields
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    expect(".o_field_date input").toHaveValue("02/03/2017");
});

test("date field dropdown doesn't dissapear on scroll", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
                <form>
                    <div class="scrollable overflow-auto" style="height: 50px;">
                        <div style="height: 2000px;">
                            <field name="date" />
                        </div>
                    </div>
                </form>`,
    });

    await contains(".o_field_date input").click();
    expect(".o_datetime_picker").toHaveCount(1);
    await scroll(".scrollable", { top: 50 });
    expect(".scrollable").toHaveProperty("scrollTop", 50);
    expect(".o_datetime_picker").toHaveCount(1);
});

test("date field with label opens datepicker on click", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
            <form>
                <label for="date" string="What date is it" />
                <field name="date" />
            </form>`,
    });

    await contains("label.o_form_label").click();
    expect(".o_datetime_picker").toHaveCount(1);
});

test("date field with warn_future option ", async () => {
    Partner._records[0] = { id: 1 };
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        arch: `
            <form>
                <field name="date" options="{'warn_future': true}" />
            </form>`,
    });

    await contains(".o_field_date input").click();
    await zoomOut();
    await zoomOut();
    await contains(getPickerCell("2020")).click();
    await contains(getPickerCell("Dec")).click();
    await contains(getPickerCell("22")).click();
    expect(".fa-exclamation-triangle").toHaveCount(1);
    await fieldInput("date").clear();
    expect(".fa-exclamation-triangle").toHaveCount(0);
});

test("date field with warn_future option: do not overwrite datepicker option", async () => {
    Partner._onChanges.date = () => {};

    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        // Do not let the date field get the focus in the first place
        arch: `
                <form>
                    <group>
                        <field name="char_field" />
                        <field name="date" options="{'warn_future': true}" />
                    </group>
                </form>`,
    });

    expect(".o_field_widget[name='date'] input").toHaveValue("02/03/2017");
    await contains(".o_form_button_create").click();
    expect(".o_field_widget[name='date'] input").toHaveValue("");
});

test.tags("desktop")("date field in editable list view", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "res.partner",
        arch: `
                <list editable="bottom">
                    <field name="date"/>
                </list>`,
    });

    const cell = queryOne("tr.o_data_row td:not(.o_list_record_selector)");
    expect(cell).toHaveText("02/03/2017");
    await contains(cell).click();
    expect(".o_field_date input").toHaveCount(1);
    expect(".o_field_date input").toBeFocused();
    expect(".o_field_date input").toHaveValue("02/03/2017");

    // open datepicker and select another value
    await contains(".o_field_date input").click();
    expect(".o_datetime_picker").toHaveCount(1);
    await zoomOut();
    await zoomOut();
    await contains(getPickerCell("2017")).click();
    await contains(getPickerCell("Feb")).click();
    await contains(getPickerCell("22")).click();
    expect(".o_datetime_picker").toHaveCount(0);
    expect(".o_field_date input").toHaveValue("02/22/2017");

    await contains(".o_list_button_save").click();
    expect("tr.o_data_row td:not(.o_list_record_selector)").toHaveText("02/22/2017");
});

test.tags("desktop")("multi edition of date field in list view: clear date in input", async () => {
    onRpc("has_group", () => true);
    Partner._records = [
        { id: 1, date: "2017-02-03" },
        { id: 2, date: "2017-02-03" },
    ];

    await mountView({
        type: "list",
        resModel: "res.partner",
        arch: `
            <list multi_edit="1">
                <field name="date"/>
            </list>`,
    });

    await contains(".o_data_row:eq(0) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").click();
    await contains(".o_data_row:eq(0) .o_data_cell").click();

    expect(".o_field_date input").toHaveCount(1);
    await fieldInput("date").clear();

    expect(".modal").toHaveCount(1);
    await contains(".modal .modal-footer .btn-primary").click();

    expect(".o_data_row:first-child .o_data_cell").toHaveText("");
    expect(".o_data_row:nth-child(2) .o_data_cell").toHaveText("");
});

test("date field remove value", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });
    onRpc("web_save", ({ args }) => {
        expect.step(args[1].date);
    });

    expect(".o_field_date input").toHaveValue("02/03/2017");

    await fieldInput("date").clear();
    expect(".o_field_date input").toHaveValue("");

    await clickSave();
    expect(".o_field_date").toHaveText("");
    expect.verifySteps([false]);
});

test("date field should select its content onclick when there is one", async () => {
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    await contains(".o_field_date input").click();
    expect(".o_datetime_picker").toHaveCount(1);
    const active = document.activeElement;
    expect(active.tagName).toBe("INPUT");
    expect(active.value.slice(active.selectionStart, active.selectionEnd)).toBe("02/03/2017");
});

test("date field supports custom formats", async () => {
    defineParams({ lang_parameters: { date_format: "dd-MM-yyyy" } });
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    const dateViewValue = queryOne(".o_field_date input").value;
    await contains(".o_field_date input").click();
    expect(".o_field_date input").toHaveValue(dateViewValue);

    await contains(getPickerCell("22")).click();

    const dateEditValue = queryOne(".o_field_date input").value;
    await clickSave();
    expect(".o_field_date input").toHaveValue(dateEditValue);
});

test("date field supports internationalization", async () => {
    serverState.lang = "nb_NO";
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });

    const dateViewForm = queryOne(".o_field_date input").value;
    await contains(".o_field_date input").click();
    expect(".o_field_date input").toHaveValue(dateViewForm);
    expect(".o_zoom_out strong").toHaveText("februar 2017");

    await contains(getPickerCell("22")).click();
    const dateEditForm = queryOne(".o_field_date input").value;
    await clickSave();
    expect(".o_field_date input").toHaveValue(dateEditForm);
});

test("hit enter should update value", async () => {
    mockTimeZone(2);
    await mountView({ type: "form", resModel: "res.partner", resId: 1 });
    const year = new Date().getFullYear();
    await contains(".o_field_date input").edit("01/08");
    expect(".o_field_widget[name='date'] input").toHaveValue(`01/08/${year}`);
    await contains(".o_field_date input").edit("08/01");
    expect(".o_field_widget[name='date'] input").toHaveValue(`08/01/${year}`);
});

test("allow to use compute dates (+5d for instance)", async () => {
    mockDate({ year: 2021, month: 2, day: 15 });

    Partner._fields.date.default = "2019-09-15";
    await mountView({ type: "form", resModel: "res.partner" });

    expect(".o_field_date input").toHaveValue("09/15/2019");
    await fieldInput("date").edit("+5d");
    expect(".o_field_date input").toHaveValue("02/20/2021");

    // Discard and do it again
    await contains(".o_form_button_cancel").click();
    expect(".o_field_date input").toHaveValue("09/15/2019");
    await fieldInput("date").edit("+5d");
    expect(".o_field_date input").toHaveValue("02/20/2021");

    // Save and do it again
    await clickSave();
    expect(".o_field_date input").toHaveValue("02/20/2021");
    await fieldInput("date").edit("+5d");
    expect(".o_field_date input").toHaveValue("02/20/2021");
});

test("date field with min_precision option", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        // Do not let the date field get the focus in the first place
        arch: `
                <form>
                    <group>
                        <field name="date" options="{'min_precision': 'months'}" />
                    </group>
                </form>`,
    });

    await click(".o_field_date input");
    await animationFrame();
    expect(".o_date_item_cell").toHaveCount(12);
    expect(queryAllTexts(".o_date_item_cell")).toEqual([
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]);
    expect(".o_date_item_cell.o_selected").toHaveText("Feb");

    await click(getPickerCell("Jan"));
    await animationFrame();
    // The picker should be closed
    expect(".o_date_item_cell").toHaveCount(0);
    expect(".o_field_widget[name='date'] input").toHaveValue("01/01/2017");
});

test("date field with max_precision option", async () => {
    await mountView({
        type: "form",
        resModel: "res.partner",
        resId: 1,
        // Do not let the date field get the focus in the first place
        arch: `
                <form>
                    <group>
                        <field name="date" options="{'max_precision': 'months'}" />
                    </group>
                </form>`,
    });

    await click(".o_field_date input");
    await animationFrame();
    // Try to zoomOut twice to be in the year selector
    await zoomOut();
    // Currently in the month selector
    expect(".o_datetime_picker_header").toHaveText("2017");
    await zoomOut();
    // Stay in the month selector according to the max precision value
    expect(".o_datetime_picker_header").toHaveText("2017");
    expect(".o_date_item_cell.o_selected").toHaveText("Feb");

    await click(getPickerCell("Jan"));
    await animationFrame();
    await click(getPickerCell("12"));
    await animationFrame();
    expect(".o_field_widget[name='date'] input").toHaveValue("01/12/2017");
});
