/** @odoo-module **/

import { applyFilter, toggleMenu } from "@web/../tests/search/helpers";
import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import ActionModel from "web.ActionModel";
import CustomFilterItem from "web.CustomFilterItem";
import { createComponent } from "web.test_utils";
import { editSelect } from "web.test_utils_fields";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { click, getFixture, mount, triggerEvent } from "../helpers/utils";

import { Component, useState, xml } from "@odoo/owl";
const { DateTime } = luxon;

const serviceRegistry = registry.category("services");

let target;

/**
 * @param {typeof DatePicker} Picker
 * @param {Object} props
 * @returns {Promise<DatePicker>}
 */
async function mountPicker(Picker, props) {
    serviceRegistry
        .add(
            "localization",
            makeFakeLocalizationService({
                dateFormat: "dd/MM/yyyy",
                dateTimeFormat: "dd/MM/yyyy HH:mm:ss",
            })
        )
        .add("ui", uiService)
        .add("hotkey", hotkeyService);

    class Parent extends Component {
        setup() {
            this.state = useState(props);
        }

        onDateChange(date) {
            if (props.onDateTimeChanged) {
                props.onDateTimeChanged(date);
            }
            this.state.date = date;
        }
    }
    Parent.template = xml/* xml */ `
        <t t-component="props.Picker" t-props="state" onDateTimeChanged.bind="onDateChange" />
    `;

    const env = await makeTestEnv();
    await mount(Parent, target, { env, props: { Picker } });
}

function useFRLocale() {
    if (!window.moment.locales().includes("fr")) {
        // Mocks the FR locale if not loaded
        const originalLocale = window.moment.locale();
        window.moment.defineLocale("fr", {
            months: "janvier_février_mars_avril_mai_juin_juillet_août_septembre_octobre_novembre_décembre".split(
                "_"
            ),
            monthsShort: "janv._févr._mars_avr._mai_juin_juil._août_sept._oct._nov._déc.".split(
                "_"
            ),
            code: "fr",
            monthsParseExact: true,
            week: { dow: 1, doy: 4 },
        });
        // Moment automatically assigns newly defined locales.
        window.moment.locale(originalLocale);
        registerCleanup(() => window.moment.updateLocale("fr", null));
    }
    return "fr";
}

function useNOLocale() {
    if (!window.moment.locales().includes("nb")) {
        const originalLocale = window.moment.locale();
        window.moment.defineLocale("nb", {
            months: "januar_februar_mars_april_mai_juni_juli_august_september_oktober_november_desember".split(
                "_"
            ),
            monthsShort: "jan._feb._mars_april_mai_juni_juli_aug._sep._okt._nov._des.".split("_"),
            monthsParseExact: true,
            week: {
                dow: 1, // Monday is the first day of the week.
                doy: 4, // The week that contains Jan 4th is the first week of the year.
            },
        });
        // Moment automatically assigns newly defined locales.
        window.moment.locale(originalLocale);
        registerCleanup(() => window.moment.updateLocale("nb", null));
    }
    return "nb";
}

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.module("DatePicker");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(8);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
        });

        assert.containsOnce(target, "input.o_input.o_datepicker_input");
        assert.containsOnce(target, "span.o_datepicker_button");
        assert.containsNone(document.body, "div.bootstrap-datetimepicker-widget");

        const input = target.querySelector("input.o_input.o_datepicker_input");
        assert.strictEqual(input.value, "09/01/1997", "Value should be the one given");
        assert.strictEqual(
            input.dataset.target,
            `#${target.querySelector(".o_datepicker").id}`,
            "DatePicker id should match its input target"
        );

        await click(input);

        assert.containsOnce(document.body, "div.bootstrap-datetimepicker-widget .datepicker");
        assert.containsNone(document.body, "div.bootstrap-datetimepicker-widget .timepicker");
        assert.strictEqual(
            document.querySelector(".datepicker .day.active").dataset.day,
            "01/09/1997",
            "Datepicker should have set the correct day"
        );
    });

    QUnit.test("pick a date", async function (assert) {
        assert.expect(5);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector(".o_datepicker_input");

        await click(input);
        await click(document.querySelector(".datepicker th.next")); // next month

        assert.verifySteps([]);

        await click(document.querySelectorAll(".datepicker table td")[15]); // previous day

        assert.strictEqual(input.value, "08/02/1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date with locale (locale given in props)", async function (assert) {
        assert.expect(5);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            format: "dd MMM, yyyy",
            locale: useFRLocale(),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/09/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "09 janv., 1997");

        await click(input);
        await click(document.querySelector(".datepicker .picker-switch")); // month picker
        await click(document.querySelectorAll(".datepicker .month")[8]); // september
        await click(document.querySelector(".datepicker .day")); // first day

        assert.strictEqual(input.value, "01 sept., 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date with locale (locale from date props)", async function (assert) {
        assert.expect(5);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", {
                zone: "utc",
                locale: useFRLocale(),
            }),
            format: "dd MMM, yyyy",
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/09/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "09 janv., 1997");

        await click(input);
        await click(document.querySelector(".datepicker .picker-switch")); // month picker
        await click(document.querySelectorAll(".datepicker .month")[8]); // september
        await click(document.querySelector(".datepicker .day")); // first day

        assert.strictEqual(input.value, "01 sept., 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("enter a date value", async function (assert) {
        assert.expect(5);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.verifySteps([]);

        input.value = "08/02/1997";
        await triggerEvent(target, ".o_datepicker_input", "change");

        assert.verifySteps(["datetime-changed"]);

        await click(input);

        assert.strictEqual(
            document.querySelector(".datepicker .day.active").dataset.day,
            "02/08/1997",
            "Datepicker should have set the correct day"
        );
    });

    QUnit.test("Date format is correctly set", async function (assert) {
        assert.expect(2);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            format: "yyyy/MM/dd",
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "1997/01/09");
    });

    QUnit.module("DateTimePicker");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(11);

        await mountPicker(DateTimePicker, {
            date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
        });

        assert.containsOnce(target, "input.o_input.o_datepicker_input");
        assert.containsOnce(target, "span.o_datepicker_button");
        assert.containsNone(document.body, "div.bootstrap-datetimepicker-widget");

        const input = target.querySelector("input.o_input.o_datepicker_input");
        assert.strictEqual(input.value, "09/01/1997 12:30:01", "Value should be the one given");
        assert.strictEqual(
            input.dataset.target,
            `#${target.querySelector(".o_datepicker").id}`,
            "DateTimePicker id should match its input target"
        );

        await click(input);

        assert.containsOnce(document.body, "div.bootstrap-datetimepicker-widget .datepicker");
        assert.containsOnce(document.body, "div.bootstrap-datetimepicker-widget .timepicker");
        assert.strictEqual(
            document.querySelector(".datepicker .day.active").dataset.day,
            "01/09/1997",
            "Datepicker should have set the correct day"
        );

        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-hour").innerText.trim(),
            "12",
            "Datepicker should have set the correct hour"
        );
        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-minute").innerText.trim(),
            "30",
            "Datepicker should have set the correct minute"
        );
        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-second").innerText.trim(),
            "01",
            "Datepicker should have set the correct second"
        );
    });

    QUnit.test("pick a date and time", async function (assert) {
        assert.expect(5);

        await mountPicker(DateTimePicker, {
            date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector("input.o_input.o_datepicker_input");

        await click(input);
        await click(document.querySelector(".datepicker th.next")); // February
        await click(document.querySelectorAll(".datepicker table td")[15]); // 08
        await click(document.querySelector('a[title="Select Time"]'));
        await click(document.querySelector(".timepicker .timepicker-hour"));
        await click(document.querySelectorAll(".timepicker .hour")[15]); // 15h
        await click(document.querySelector(".timepicker .timepicker-minute"));
        await click(document.querySelectorAll(".timepicker .minute")[9]); // 45m
        await click(document.querySelector(".timepicker .timepicker-second"));

        assert.verifySteps([]);

        await click(document.querySelectorAll(".timepicker .second")[1]); // 05s

        assert.strictEqual(input.value, "08/02/1997 15:45:05");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date and time with locale", async function (assert) {
        assert.expect(6);

        await mountPicker(DateTimePicker, {
            date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            format: "dd MMM, yyyy HH:mm:ss",
            locale: useFRLocale(),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "01/09/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });

        const input = target.querySelector("input.o_input.o_datepicker_input");

        assert.strictEqual(input.value, "09 janv., 1997 12:30:01");

        await click(input);

        await click(document.querySelector(".datepicker .picker-switch")); // month picker
        await click(document.querySelectorAll(".datepicker .month")[8]); // september
        await click(document.querySelector(".datepicker .day")); // first day

        await click(document.querySelector('a[title="Select Time"]'));
        await click(document.querySelector(".timepicker .timepicker-hour"));
        await click(document.querySelectorAll(".timepicker .hour")[15]); // 15h
        await click(document.querySelector(".timepicker .timepicker-minute"));
        await click(document.querySelectorAll(".timepicker .minute")[9]); // 45m
        await click(document.querySelector(".timepicker .timepicker-second"));

        assert.verifySteps([]);

        await click(document.querySelectorAll(".timepicker .second")[1]); // 05s

        assert.strictEqual(input.value, "01 sept., 1997 15:45:05");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("enter a datetime value", async function (assert) {
        assert.expect(9);

        await mountPicker(DateTimePicker, {
            date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            onDateTimeChanged: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.verifySteps([]);

        input.value = "08/02/1997 15:45:05";
        await triggerEvent(target, ".o_datepicker_input", "change");

        assert.verifySteps(["datetime-changed"]);

        await click(input);

        assert.strictEqual(input.value, "08/02/1997 15:45:05");
        assert.strictEqual(
            document.querySelector(".datepicker .day.active").dataset.day,
            "02/08/1997",
            "Datepicker should have set the correct day"
        );
        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-hour").innerText.trim(),
            "15",
            "Datepicker should have set the correct hour"
        );
        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-minute").innerText.trim(),
            "45",
            "Datepicker should have set the correct minute"
        );
        assert.strictEqual(
            document.querySelector(".timepicker .timepicker-second").innerText.trim(),
            "05",
            "Datepicker should have set the correct second"
        );
    });

    QUnit.test("Date time format is correctly set", async function (assert) {
        assert.expect(2);

        await mountPicker(DateTimePicker, {
            date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            format: "HH:mm:ss yyyy/MM/dd",
        });
        const input = target.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "12:30:01 1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "12:30:01 1997/01/09");
    });

    QUnit.test("Datepicker works with norwegian locale", async (assert) => {
        assert.expect(6);

        await mountPicker(DatePicker, {
            date: DateTime.fromFormat("09/04/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            format: "dd MMM, yyyy",
            locale: useNOLocale(),
            onDateTimeChanged(date) {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/04/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        const input = target.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "09 apr., 1997");

        await click(input);

        assert.strictEqual(input.value, "1997/04/09");

        const days = [...document.querySelectorAll(".datepicker .day")];
        await click(days.find((d) => d.innerText.trim() === "1")); // first day of april

        assert.strictEqual(input.value, "01 apr., 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("custom filter date", async function (assert) {
        assert.expect(3);
        class MockedSearchModel extends ActionModel {
            dispatch(method, ...args) {
                assert.strictEqual(method, "createNewFilters");
                const preFilters = args[0];
                const preFilter = preFilters[0];
                assert.strictEqual(
                    preFilter.description,
                    'A date is equal to "05/05/2005"',
                    "description should be in localized format"
                );
                assert.deepEqual(
                    preFilter.domain,
                    '[["date_field","=","2005-05-05"]]',
                    "domain should be in UTC format"
                );
            }
        }
        const searchModel = new MockedSearchModel();
        const date_field = { name: "date_field", string: "A date", type: "date", searchable: true };
        await createComponent(CustomFilterItem, {
            props: {
                fields: { date_field },
            },
            env: { searchModel },
        });
        await toggleMenu(target, "Add Custom Filter");
        await editSelect(target.querySelector(".o_generator_menu_field"), "date_field");
        const valueInput = target.querySelector(".o_generator_menu_value .o_input");
        await click(valueInput);
        await editSelect(valueInput, "05/05/2005");
        await applyFilter(target);
    });

    QUnit.test("start with no value", async function (assert) {
        assert.expect(6);

        await mountPicker(DateTimePicker, {
            onDateTimeChanged(date) {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });

        const input = target.querySelector(".o_datepicker_input");
        assert.strictEqual(input.value, "");

        assert.verifySteps([]);
        input.value = "08/02/1997 15:45:05";
        await triggerEvent(target, ".o_datepicker_input", "change");

        assert.verifySteps(["datetime-changed"]);
        assert.strictEqual(input.value, "08/02/1997 15:45:05");
    });
});
