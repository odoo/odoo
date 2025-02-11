/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { clearRegistryWithCleanup, makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import {
    click,
    editInput,
    editSelect,
    getFixture,
    mount,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { localization } from "@web/core/l10n/localization";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import {
    assertDateTimePicker,
    getPickerCell,
    getTimePickers,
    zoomOut,
} from "./datetime_test_helpers";
import { datetimePickerService } from "@web/core/datetime/datetimepicker_service";

const { DateTime } = luxon;

/**
 * @typedef {import("@web/core/datetime/datetime_input").DateTimeInputProps} DateTimeInputProps
 */

/**
 * @param {DateTimeInputProps} props
 */
const mountInput = async (props) => {
    const env = await makeTestEnv();
    await mount(Root, getFixture(), { env, props });
    return fixture.querySelector(".o_datetime_input");
};

class Root extends Component {
    static components = { DateTimeInput };

    static template = xml`
        <DateTimeInput t-props="props" />
        <t t-foreach="mainComponentEntries" t-as="comp" t-key="comp[0]">
            <t t-component="comp[1].Component" t-props="comp[1].props" />
        </t>
    `;

    setup() {
        this.mainComponentEntries = mainComponentRegistry.getEntries();
    }
}

const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

let fixture;

QUnit.module("Components", ({ beforeEach }) => {
    beforeEach(() => {
        clearRegistryWithCleanup(mainComponentRegistry);

        serviceRegistry
            .add("hotkey", hotkeyService)
            .add(
                "localization",
                makeFakeLocalizationService({
                    dateFormat: "dd/MM/yyyy",
                    dateTimeFormat: "dd/MM/yyyy HH:mm:ss",
                })
            )
            .add("popover", popoverService)
            .add("ui", uiService)
            .add("datetime_picker", datetimePickerService);

        fixture = getFixture();
    });

    QUnit.module("DateTimeInput (date)");

    QUnit.test("basic rendering", async function (assert) {
        await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
        });

        assert.containsOnce(fixture, ".o_datetime_input");
        assertDateTimePicker(false);

        const input = fixture.querySelector(".o_datetime_input");
        assert.strictEqual(input.value, "09/01/1997", "Value should be the one given");

        await click(input);

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

    QUnit.test("pick a date", async function (assert) {
        assert.expect(5);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            onChange: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        await click(input);
        await click(getFixture(), ".o_datetime_picker .o_next"); // next month

        assert.verifySteps([]);

        await click(getPickerCell("8").at(0));

        assert.strictEqual(input.value, "08/02/1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date with FR locale", async function (assert) {
        assert.expect(5);

        patchWithCleanup(luxon.Settings, { defaultLocale: "fr-FR" });

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            format: "dd MMM, yyyy",
            onChange: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/09/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.strictEqual(input.value, "09 janv., 1997");

        await click(input);
        await zoomOut();
        await click(getPickerCell("sept."));
        await click(getPickerCell("1").at(0));

        assert.strictEqual(input.value, "01 sept., 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("pick a date with locale (locale with different symbols)", async function (assert) {
        assert.expect(6);

        patchWithCleanup(luxon.Settings, { defaultLocale: "gu" });

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            format: "dd MMM, yyyy",
            onChange: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/09/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.strictEqual(input.value, "09 જાન્યુ, 1997");

        await click(input);

        assert.strictEqual(input.value, "09 જાન્યુ, 1997");

        await zoomOut();
        await click(getPickerCell("સપ્ટે"));
        await click(getPickerCell("1").at(0));

        assert.strictEqual(input.value, "01 સપ્ટે, 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("enter a date value", async function (assert) {
        assert.expect(5);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            onChange: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "08/02/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.verifySteps([]);

        await editInput(input, null, "08/02/1997");

        assert.verifySteps(["datetime-changed"]);

        await click(input);

        assert.hasClass(getPickerCell("8").at(0), "o_selected");
    });

    QUnit.test("Date format is correctly set", async function (assert) {
        assert.expect(2);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            format: "yyyy/MM/dd",
        });

        assert.strictEqual(input.value, "1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "1997/01/09");
    });

    QUnit.module("DateTimeInput (datetime)");

    QUnit.test("basic rendering", async function (assert) {
        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
        });

        assert.containsOnce(fixture, ".o_datetime_input");
        assertDateTimePicker(false);

        assert.strictEqual(input.value, "09/01/1997 12:30:01", "Value should be the one given");

        await click(input);

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
            time: [[12, 30]],
        });
    });

    QUnit.test("pick a date and time", async function (assert) {
        assert.expect(6);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            onChange: (date) => assert.step(date.toSQL().split(".")[0]),
        });

        assert.strictEqual(input.value, "09/01/1997 12:30:01");

        await click(input);

        // Select February 8th
        await click(getFixture(), ".o_datetime_picker .o_next");
        await click(getPickerCell("8").at(0));

        // Select 15:45
        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "15");
        await editSelect(minuteSelect, null, "45");

        assert.strictEqual(input.value, "08/02/1997 15:45:01");
        assert.verifySteps(["1997-02-08 12:30:01", "1997-02-08 15:30:01", "1997-02-08 15:45:01"]);
    });

    QUnit.test("pick a date and time with locale", async function (assert) {
        assert.expect(6);

        patchWithCleanup(luxon.Settings, { defaultLocale: "fr-FR" });

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            format: "dd MMM, yyyy HH:mm:ss",
            onChange: (date) => assert.step(date.toSQL().split(".")[0]),
        });

        assert.strictEqual(input.value, "09 janv., 1997 12:30:01");

        await click(input);

        // Select September 1st
        await zoomOut();
        await click(getPickerCell("sept."));
        await click(getPickerCell("1").at(0));

        // Select 15:45
        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "15");
        await editSelect(minuteSelect, null, "45");

        assert.strictEqual(input.value, "01 sept., 1997 15:45:01");
        assert.verifySteps(["1997-09-01 12:30:01", "1997-09-01 15:30:01", "1997-09-01 15:45:01"]);
    });

    QUnit.test("pick a time with 12 hour format without meridiem", async function (assert) {
        assert.expect(3);

        patchWithCleanup(localization, {
            dateFormat: "dd/MM/yyyy",
            dateTimeFormat: "dd/MM/yyyy hh:mm:ss",
            timeFormat: "hh:mm:ss",
        });

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 08:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            onChange: (date) => assert.step(date.toSQL().split(".")[0]),
        });

        assert.strictEqual(input.value, "09/01/1997 08:30:01");

        await click(input);

        const [, minuteSelect] = getTimePickers().at(0);
        await editSelect(minuteSelect, null, "15");

        assert.verifySteps(["1997-01-09 08:15:01"]);
    });

    QUnit.test("enter a datetime value", async function (assert) {
        assert.expect(7);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            onChange: (date) => {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.verifySteps([]);

        input.value = "08/02/1997 15:45:05";
        await triggerEvent(fixture, ".o_datetime_input", "change");

        assert.verifySteps(["datetime-changed"]);

        await click(input);

        assert.strictEqual(input.value, "08/02/1997 15:45:05");
        assert.hasClass(getPickerCell("8").at(0), "o_selected");
        assert.deepEqual(getTimePickers({ parse: true }).at(0), [15, 45]);
    });

    QUnit.test("Date time format is correctly set", async function (assert) {
        assert.expect(2);

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            format: "HH:mm:ss yyyy/MM/dd",
        });

        assert.strictEqual(input.value, "12:30:01 1997/01/09");

        // Forces an update to assert that the registered format is the correct one
        await click(input);

        assert.strictEqual(input.value, "12:30:01 1997/01/09");
    });

    QUnit.test("Datepicker works with norwegian locale", async (assert) => {
        assert.expect(6);

        patchWithCleanup(luxon.Settings, { defaultLocale: "nb-NO" });

        const input = await mountInput({
            value: DateTime.fromFormat("09/04/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            format: "dd MMM, yyyy",
            onChange(date) {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy"),
                    "01/04/1997",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.strictEqual(input.value, "09 apr., 1997");

        await click(input);

        assert.strictEqual(input.value, "09 apr., 1997");

        await click(getPickerCell("1").at(0));

        assert.strictEqual(input.value, "01 apr., 1997");
        assert.verifySteps(["datetime-changed"]);
    });

    QUnit.test("Datepicker works with dots and commas in format", async (assert) => {
        assert.expect(2);

        const input = await mountInput({
            value: DateTime.fromFormat("10/03/2023 13:14:27", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            format: "dd.MM,yyyy",
        });

        assert.strictEqual(input.value, "10.03,2023");

        await click(input);

        assert.strictEqual(input.value, "10.03,2023");
    });

    QUnit.test("start with no value", async function (assert) {
        assert.expect(6);

        const input = await mountInput({
            type: "datetime",
            onChange(date) {
                assert.step("datetime-changed");
                assert.strictEqual(
                    date.toFormat("dd/MM/yyyy HH:mm:ss"),
                    "08/02/1997 15:45:05",
                    "Event should transmit the correct date"
                );
            },
        });

        assert.strictEqual(input.value, "");
        assert.verifySteps([]);

        await editInput(input, null, "08/02/1997 15:45:05");

        assert.verifySteps(["datetime-changed"]);
        assert.strictEqual(input.value, "08/02/1997 15:45:05");
    });

    QUnit.test("Clicking close button closes datetime picker", async function (assert) {
        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997 12:30:01", "dd/MM/yyyy HH:mm:ss"),
            type: "datetime",
            format: "dd MMM, yyyy HH:mm:ss",
        });
        await click(input);
        await click(getFixture(), ".o_datetime_picker .o_datetime_buttons .btn-secondary");

        assert.strictEqual(
            getFixture().querySelector(".o_datetime_picker"),
            null,
            "Datetime picker is closed"
        );
    });

    QUnit.test("arab locale, latin numbering system as input", async (assert) => {
        patchWithCleanup(localization, {
            dateFormat: "dd MMM, yyyy",
            dateTimeFormat: "dd MMM, yyyy hh:mm:ss",
            timeFormat: "hh:mm:ss",
        });
        patchWithCleanup(luxon.Settings, {
            defaultLocale: "ar-001",
            defaultNumberingSystem: "arab",
        });

        const input = await mountInput();

        await editInput(input, null, "٠٤ يونيو, ٢٠٢٣ ١١:٣٣:٠٠");

        assert.strictEqual(input.value, "٠٤ يونيو, ٢٠٢٣ ١١:٣٣:٠٠");

        await editInput(input, null, "15 07, 2020 12:30:43");

        assert.strictEqual(input.value, "١٥ يوليو, ٢٠٢٠ ١٢:٣٠:٤٣");
    });

    QUnit.test("check datepicker in localization with textual month format", async function (assert) {
        assert.expect(3);
        let onChangeDate;

        Object.assign(localization, {
            dateFormat: 'MMM/dd/yyyy',
            timeFormat: 'HH:mm:ss',
            dateTimeFormat: 'MMM/dd/yyyy HH:mm:ss',
        });

        const input = await mountInput({
            value: DateTime.fromFormat("09/01/1997", "dd/MM/yyyy"),
            type: "date",
            onChange: date => onChangeDate = date,
        });

        assert.strictEqual(input.value, "Jan/09/1997");

        await click(input);
        await click(getPickerCell("5").at(0));

        assert.strictEqual(input.value, "Jan/05/1997");
        assert.strictEqual(onChangeDate.toFormat("dd/MM/yyyy"), "05/01/1997");
    });
});
