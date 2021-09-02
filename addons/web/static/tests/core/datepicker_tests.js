/** @odoo-module **/

import { DatePicker, DateTimePicker } from "@web/core/datepicker/datepicker";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeLocalizationService } from "../helpers/mock_services";
import { click, getFixture, triggerEvent } from "../helpers/utils";

const { DateTime } = luxon;
const { Component, mount, tags } = owl;
const { xml } = tags;
const serviceRegistry = registry.category("services");

/**
 * @param {typeof DatePicker} Picker
 * @param {{ props: any, onDateChange: () => any }} [params={}]
 * @returns {Promise<DatePicker>}
 */
const mountPicker = async (Picker, { props, onDateChange } = {}) => {
    serviceRegistry
        .add(
            "localization",
            makeFakeLocalizationService({
                dateFormat: "dd/MM/yyyy",
                dateTimeFormat: "dd/MM/yyyy HH:mm:ss",
            })
        )
        .add("ui", uiService);

    class Parent extends Component {}
    Parent.template = xml/* xml */ `
        <t t-component="props.Picker" t-props="props.props" t-on-datetime-changed="props.onDateChange" />
    `;

    const env = await makeTestEnv();
    const target = getFixture();
    const parent = await mount(Parent, { env, props: { Picker, props, onDateChange }, target });
    registerCleanup(() => parent.destroy());
    return parent;
};

const useFRLocale = () => {
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
};

QUnit.module("Components", () => {
    QUnit.module("DatePicker");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(8);

        const picker = await mountPicker(DatePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            },
        });

        assert.containsOnce(picker, "input.o_input.o_datepicker_input");
        assert.containsOnce(picker, "span.o_datepicker_button");
        assert.containsNone(document.body, "div.bootstrap-datetimepicker-widget");

        const input = picker.el.querySelector("input.o_input.o_datepicker_input");
        assert.strictEqual(input.value, "09/01/1997", "Value should be the one given");
        assert.strictEqual(
            input.dataset.target,
            `#${picker.el.id}`,
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

        const picker = await mountPicker(DatePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

        await click(input);
        await click(document.querySelector(".datepicker th.next")); // next month

        assert.verifySteps([]);

        await click(document.querySelectorAll(".datepicker table td")[15]); // previous day

        assert.strictEqual(input.value, "08/02/1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date with locale", async function (assert) {
        assert.expect(5);

        const picker = await mountPicker(DatePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
                format: "dd MMM, yyyy",
                locale: useFRLocale(),
            },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy"),
                    "01/09/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

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

        const picker = await mountPicker(DatePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
            },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

        assert.verifySteps([]);

        input.value = "08/02/1997";
        await triggerEvent(picker.el, ".o_datepicker_input", "change");

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

        const picker = await mountPicker(DatePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy", { zone: "utc" }),
                format: "yyyy/MM/dd",
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "1997/01/09");
    });

    QUnit.module("DateTimePicker");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(11);

        const picker = await mountPicker(DateTimePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            },
        });

        assert.containsOnce(picker, "input.o_input.o_datepicker_input");
        assert.containsOnce(picker, "span.o_datepicker_button");
        assert.containsNone(document.body, "div.bootstrap-datetimepicker-widget");

        const input = picker.el.querySelector("input.o_input.o_datepicker_input");
        assert.strictEqual(input.value, "09/01/1997 12:30:01", "Value should be the one given");
        assert.strictEqual(
            input.dataset.target,
            `#${picker.el.id}`,
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

        const picker = await mountPicker(DateTimePicker, {
            props: { date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss") },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = picker.el.querySelector("input.o_input.o_datepicker_input");

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

        const picker = await mountPicker(DateTimePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                format: "dd MMM, yyyy HH:mm:ss",
                locale: useFRLocale(),
            },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "01/09/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });

        const input = picker.el.querySelector("input.o_input.o_datepicker_input");

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

        const picker = await mountPicker(DateTimePicker, {
            props: { date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss") },
            onDateChange: (ev) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    ev.detail.date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

        assert.verifySteps([]);

        input.value = "08/02/1997 15:45:05";
        await triggerEvent(picker.el, ".o_datepicker_input", "change");

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

        const picker = await mountPicker(DateTimePicker, {
            props: {
                date: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
                format: "HH:mm:ss yyyy/MM/dd",
            },
        });
        const input = picker.el.querySelector(".o_datepicker_input");

        assert.strictEqual(input.value, "12:30:01 1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "12:30:01 1997/01/09");
    });
});
