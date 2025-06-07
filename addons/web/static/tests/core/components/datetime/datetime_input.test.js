import { test, expect, describe } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { assertDateTimePicker, getPickerCell } from "../../datetime/datetime_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import {
    contains,
    defineParams,
    makeMockEnv,
    mountWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { click, edit, queryAll, queryFirst, select } from "@odoo/hoot-dom";

const { DateTime } = luxon;

class DateTimeInputComp extends Component {
    static components = { DateTimeInput };
    static template = xml`<DateTimeInput t-props="props" />`;
    static props = ["*"];
}

async function changeLang(lang) {
    serverState.lang = lang;
    await makeMockEnv();
}

describe("DateTimeInput (date)", () => {
    defineParams({
        lang_parameters: {
            date_format: "%d/%m/%Y",
            time_format: "%H:%M:%S",
        },
    });

    test("basic rendering", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
            },
        });

        expect(".o_datetime_input").toHaveCount(1);
        assertDateTimePicker(false);

        expect(".o_datetime_input").toHaveValue("09/01/1997");

        await click(".o_datetime_input");
        await animationFrame();

        assertDateTimePicker({
            title: "January 1997",
            date: [
                {
                    cells: [
                        [0, 0, 0, 1, 2, 3, 4],
                        [5, 6, 7, 8, [9], 10, 11],
                        [12, 13, 14, 15, 16, 17, 18],
                        [19, 20, 21, 22, 23, 24, 25],
                        [26, 27, 28, 29, 30, 31, 0],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [1, 2, 3, 4, 5],
                },
            ],
        });
    });

    test("pick a date", async () => {
        expect.assertions(4);

        await makeMockEnv();

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                onChange: (date) => {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy")).toBe("08/02/1997", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        await contains(".o_datetime_input").click();
        await contains(".o_datetime_picker .o_next").click();

        expect.verifySteps([]);
        await contains(getPickerCell("8")).click();

        expect(".o_datetime_input").toHaveValue("08/02/1997");
        // the onchange is called twice (when clicking and whe the popover is closing)
        expect.verifySteps(["datetime-changed"]);
    });

    test("pick a date with FR locale", async () => {
        expect.assertions(4);

        await changeLang("fr-FR");

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                format: "dd MMM, yyyy",
                onChange: (date) => {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy")).toBe("19/09/1997", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect(".o_datetime_input").toHaveValue("09 janv., 1997");

        await contains(".o_datetime_input").click();
        await contains(".o_zoom_out").click();
        await contains(getPickerCell("sept.")).click();
        await contains(getPickerCell("19")).click();
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("19 sept., 1997");
        expect.verifySteps(["datetime-changed"]);
    });

    test("pick a date with locale (locale with different symbols)", async () => {
        expect.assertions(5);

        await changeLang("gu");

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                format: "dd MMM, yyyy",
                onChange: (date) => {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy")).toBe("19/09/1997", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect(".o_datetime_input").toHaveValue("09 જાન્યુ, 1997");

        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("09 જાન્યુ, 1997");

        await contains(".o_zoom_out").click();
        await contains(getPickerCell("સપ્ટે")).click();
        await contains(getPickerCell("19")).click();
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("19 સપ્ટે, 1997");
        expect.verifySteps(["datetime-changed"]);
    });

    test("enter a date value", async () => {
        expect.assertions(4);

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                onChange: (date) => {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy")).toBe("08/02/1997", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect.verifySteps([]);

        await contains(".o_datetime_input").click();
        await edit("08/02/1997");
        await animationFrame();
        await click(document.body);
        await animationFrame();

        expect.verifySteps(["datetime-changed"]);

        await click(".o_datetime_input");
        await animationFrame();

        expect(getPickerCell("8")).toHaveClass("o_selected");
    });

    test("Date format is correctly set", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                format: "yyyy/MM/dd",
            },
        });

        expect(".o_datetime_input").toHaveValue("1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("1997/01/09");
    });

    test.tags("mobile");
    test("popover should have enough space to be displayed", async () => {
        class Root extends Component {
            static components = { DateTimeInput };
            static template = xml`<div class="d-flex"><DateTimeInput t-props="props" /></div>`;
            static props = ["*"];
        }
        await mountWithCleanup(Root, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
            },
        });
        const parent = queryFirst(".o_datetime_input").parentElement;
        const initialParentHeight = parent.clientHeight;

        await contains(".o_datetime_input", { root: parent }).click();

        const pickerRectHeight = queryFirst(".o_datetime_picker").clientHeight;

        expect(initialParentHeight).toBeLessThan(pickerRectHeight, {
            message: "initial height shouldn't be big enough to display the picker",
        });
        expect(parent.clientHeight).toBeGreaterThan(pickerRectHeight, {
            message: "initial height should be big enough to display the picker",
        });
    });
});

describe("DateTimeInput (datetime)", () => {
    defineParams({
        lang_parameters: {
            date_format: "%d/%m/%Y",
            time_format: "%H:%M:%S",
        },
    });

    test("basic rendering", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
            },
        });

        expect(".o_datetime_input").toHaveCount(1);
        assertDateTimePicker(false);

        expect(".o_datetime_input").toHaveValue("09/01/1997 12:30:01");

        await contains(".o_datetime_input").click();

        assertDateTimePicker({
            title: "January 1997",
            date: [
                {
                    cells: [
                        [0, 0, 0, 1, 2, 3, 4],
                        [5, 6, 7, 8, [9], 10, 11],
                        [12, 13, 14, 15, 16, 17, 18],
                        [19, 20, 21, 22, 23, 24, 25],
                        [26, 27, 28, 29, 30, 31, 0],
                    ],
                    daysOfWeek: ["#", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    weekNumbers: [1, 2, 3, 4, 5],
                },
            ],
            time: [[12, 30]],
        });
    });

    test("pick a date and time", async () => {
        await makeMockEnv();

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                onChange: (date) => expect.step(date.toSQL().split(".")[0]),
            },
        });

        expect(".o_datetime_input").toHaveValue("09/01/1997 12:30:01");

        await contains(".o_datetime_input").click();

        // Select February 8th
        await contains(".o_datetime_picker .o_next").click();
        await contains(getPickerCell("8")).click();

        // Select 15:45
        const [hourSelect, minuteSelect] = queryAll(".o_time_picker_select");
        await select("15", { target: hourSelect });
        await animationFrame();
        await select("45", { target: minuteSelect });
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("08/02/1997 15:45:01");
        expect.verifySteps(["1997-02-08 12:30:01", "1997-02-08 15:30:01", "1997-02-08 15:45:01"]);
    });

    test("pick a date and time with locale", async () => {
        await changeLang("fr_FR");

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                format: "dd MMM, yyyy HH:mm:ss",
                onChange: (date) => expect.step(date.toSQL().split(".")[0]),
            },
        });

        expect(".o_datetime_input").toHaveValue("09 janv., 1997 12:30:01");

        await contains(".o_datetime_input").click();

        await contains(".o_zoom_out").click();
        await contains(getPickerCell("sept.")).click();
        await contains(getPickerCell("1")).click();

        // Select 15:45
        const [hourSelect, minuteSelect] = queryAll(".o_time_picker_select");
        await select("15", { target: hourSelect });
        await animationFrame();
        await select("45", { target: minuteSelect });
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("01 sept., 1997 15:45:01");
        expect.verifySteps(["1997-09-01 12:30:01", "1997-09-01 15:30:01", "1997-09-01 15:45:01"]);
    });

    test("pick a time with 12 hour format without meridiem", async () => {
        defineParams({
            lang_parameters: {
                date_format: "%d/%m/%Y",
                time_format: "%I:%M:%S",
            },
        });

        await makeMockEnv();
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 08:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                onChange: (date) => expect.step(date.toSQL().split(".")[0]),
            },
        });

        expect(".o_datetime_input").toHaveValue("09/01/1997 08:30:01");

        await contains(".o_datetime_input").click();

        const [, minuteSelect] = queryAll(".o_time_picker_select");
        await select("15", { target: minuteSelect });

        await click(document.body);
        await animationFrame();

        expect.verifySteps(["1997-01-09 08:15:01"]);
    });

    test("enter a datetime value", async () => {
        expect.assertions(7);

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                onChange: (date) => {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy HH:mm:ss")).toBe("08/02/1997 15:45:05", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect.verifySteps([]);

        await contains(".o_datetime_input").click();
        await edit("08/02/1997 15:45:05");
        await animationFrame();
        await click(document.body);
        await animationFrame();

        expect.verifySteps(["datetime-changed"]);

        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("08/02/1997 15:45:05");
        expect(getPickerCell("8")).toHaveClass("o_selected");

        const [hourSelect, minuteSelect] = queryAll(".o_time_picker_select");
        expect(hourSelect).toHaveValue("15");
        expect(minuteSelect).toHaveValue("45");
    });

    test("Date time format is correctly set", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                format: "HH:mm:ss yyyy/MM/dd",
            },
        });

        expect(".o_datetime_input").toHaveValue("12:30:01 1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("12:30:01 1997/01/09");
    });

    test("Datepicker works with norwegian locale", async () => {
        expect.assertions(7);

        await changeLang("nb");

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/04/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                format: "dd MMM, yyyy",
                onChange(date) {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy")).toBe("01/04/1997", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect(".o_datetime_input").toHaveValue("09 apr., 1997");

        // Forces an update to assert that the registered format is the correct one
        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("09 apr., 1997");

        await contains(getPickerCell("1")).click();
        expect(".o_datetime_input").toHaveValue("01 apr., 1997");
        expect.verifySteps(["datetime-changed"]);

        await click(".o_apply");
        await animationFrame();
        expect.verifySteps(["datetime-changed"]);
    });

    test("Datepicker works with dots and commas in format", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("10/03/2023 13:14:27", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                format: "dd.MM,yyyy",
            },
        });

        expect(".o_datetime_input").toHaveValue("10.03,2023");

        // Forces an update to assert that the registered format is the correct one
        await contains(".o_datetime_input").click();

        expect(".o_datetime_input").toHaveValue("10.03,2023");
    });

    test("start with no value", async () => {
        expect.assertions(5);

        await makeMockEnv();
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                type: "datetime",
                onChange(date) {
                    expect.step("datetime-changed");
                    expect(date.toFormat("dd/MM/yyyy HH:mm:ss")).toBe("08/02/1997 15:45:05", {
                        message: "Event should transmit the correct date",
                    });
                },
            },
        });

        expect(".o_datetime_input").toHaveValue("");
        expect.verifySteps([]);

        await contains(".o_datetime_input").click();
        await edit("08/02/1997 15:45:05");
        await animationFrame();
        await click(document.body);
        await animationFrame();

        expect.verifySteps(["datetime-changed"]);
        expect(".o_datetime_input").toHaveValue("08/02/1997 15:45:05");
    });

    test("Clicking close button closes datetime picker", async () => {
        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                type: "datetime",
                format: "dd MMM, yyyy HH:mm:ss",
            },
        });
        await contains(".o_datetime_input").click();
        await contains(".o_datetime_picker .o_datetime_buttons .btn-secondary").click();

        expect(".o_datetime_picker").toHaveCount(0);
    });

    test("check datepicker in localization with textual month format", async () => {
        defineParams({
            lang_parameters: {
                date_format: "%b/%d/%Y",
                time_format: "%H:%M:%S",
            },
        });

        let onChangeDate;

        await mountWithCleanup(DateTimeInputComp, {
            props: {
                value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
                type: "date",
                onChange: (date) => (onChangeDate = date),
            },
        });

        expect(".o_datetime_input").toHaveValue("Jan/09/1997");

        await contains(".o_datetime_input").click();
        await contains(getPickerCell("5")).click();

        expect(".o_datetime_input").toHaveValue("Jan/05/1997");
        expect(onChangeDate.toFormat("dd/MM/yyyy")).toBe("05/01/1997");
    });

    test("arab locale, latin numbering system as input", async () => {
        defineParams({
            lang_parameters: {
                date_format: "%d %b, %Y",
                time_format: "%H:%M:%S",
            },
        });

        await changeLang("ar-001");

        await mountWithCleanup(DateTimeInputComp);

        await contains(".o_datetime_input").click();
        await edit("٠٤ يونيو, ٢٠٢٣ ١١:٣٣:٠٠");
        await animationFrame();
        await click(document.body);
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("٠٤ يونيو, ٢٠٢٣ ١١:٣٣:٠٠");

        await contains(".o_datetime_input").click();
        await edit("15 07, 2020 12:30:43");
        await animationFrame();
        await click(document.body);
        await animationFrame();

        expect(".o_datetime_input").toHaveValue("١٥ يوليو, ٢٠٢٠ ١٢:٣٠:٤٣");
    });
});
