/** @odoo-module **/

import { getPickerCell, getTimePickers } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    nextTick,
    patchDate,
    patchTimeZone,
    triggerEvent,
    triggerScroll,
} from "@web/../tests/helpers/utils";
import { pagerNext } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const getInputs = () => target.querySelectorAll(".o_field_daterange input");

/**
 * @param {HTMLElement} el
 */
const isHiddenByCSS = (el) => {
    const style = getComputedStyle(el);
    return style.visibility === "hidden" || style.opacity === "0";
};

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        datetime_end: { string: "Datetime End", type: "datetime" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();

        // Date field should not have an offset as they are ignored.
        // However, in the test environement, a UTC timezone is set to run all tests. And if any code does not use the safe timezone method
        // provided by the framework (which happens in this case inside the date range picker lib), unexpected behavior kicks in as the timezone
        // of the dev machine collides with the timezone set by the test env.
        // To avoid failing test on dev's local machines, a hack is to apply an timezone offset greater than the difference between UTC and the dev's
        // machine timezone. For belgium, > 60 is enough. For India, > 5h30 is required, hence 330.
        patchTimeZone(330);
    });

    QUnit.module("DateRangeField");

    QUnit.test("Datetime field - interaction with the datepicker", async (assert) => {
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
        });

        // Check date range picker initialization
        assert.containsOnce(getFixture(), ".o_field_daterange");
        assert.containsNone(getFixture(), ".o_datetime_picker");

        // open the first one
        const daterange = target.querySelector(".o_field_daterange");
        await click(daterange.querySelector("input[data-field=datetime]"));

        let datepicker = document.querySelector(".o_datetime_picker");
        assert.isVisible(datepicker, "first date range picker should be opened");
        assert.strictEqual(
            datepicker.querySelector(".o_date_item_cell.o_select_start").textContent,
            "8",
            "active start date should be '8' in date range picker"
        );
        let [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
        assert.strictEqual(
            hourSelectStart.value,
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            minuteSelectStart.value,
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            datepicker.querySelector(".o_date_item_cell.o_select_end").textContent,
            "13",
            "active end date should be '13' in date range picker"
        );
        let [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
        assert.strictEqual(
            hourSelectEnd.value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            minuteSelectEnd.value,
            "30",
            "active end date minute should be '30' in date range picker"
        );
        assert.containsN(
            minuteSelectStart,
            "option",
            12,
            "minute selection should contain 12 options (1 for each 5 minutes)"
        );
        // Close picker
        await click(document.querySelector(".o_form_view_container"));
        assert.containsNone(getFixture(), ".o_datetime_picker", "datepicker should be closed");

        // Try to check with end date
        await click(daterange.querySelector("input[data-field=datetime_end]"));

        datepicker = document.querySelector(".o_datetime_picker");
        assert.isVisible(datepicker, "first date range picker should be opened");
        assert.strictEqual(
            datepicker.querySelector(".o_date_item_cell.o_select_start").textContent,
            "8",
            "active start date should be '8' in date range picker"
        );
        [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
        assert.strictEqual(
            hourSelectStart.value,
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            minuteSelectStart.value,
            "30",
            "active start date minute should be '30' in date range picker"
        );
        assert.strictEqual(
            datepicker.querySelector(".o_date_item_cell.o_select_end").textContent,
            "13",
            "active end date should be '13' in date range picker"
        );
        [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
        assert.strictEqual(
            hourSelectEnd.value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            minuteSelectEnd.value,
            "30",
            "active end date minute should be '30' in date range picker"
        );
        assert.containsN(
            minuteSelectStart,
            "option",
            12,
            "minute selection should contain 12 options (1 for each 5 minutes)"
        );

        // Select a new range and check that inputs are updated
        await click(getPickerCell("8").at(0)); // 02/08/2017
        await click(getPickerCell("9").at(0)); // 02/09/2017
        assert.equal(
            target.querySelector("input[data-field=datetime]").value,
            "02/08/2017 15:30:00"
        );
        assert.equal(
            target.querySelector("input[data-field=datetime_end]").value,
            "02/09/2017 05:30:00"
        );

        // Save
        await clickSave(target);

        // Check date after save
        assert.strictEqual(
            target.querySelector("input[data-field=datetime]").value,
            "02/08/2017 15:30:00"
        );
        assert.strictEqual(
            target.querySelector("input[data-field=datetime_end]").value,
            "02/09/2017 05:30:00"
        );
    });

    QUnit.test("Date field - interaction with the datepicker", async (assert) => {
        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.partner.records[0].date_end = "2017-02-08";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                    <form>
                        <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
                    </form>`,
        });

        // Check date range picker initialization
        assert.containsOnce(getFixture(), ".o_field_daterange");
        assert.containsNone(getFixture(), ".o_datetime_picker");

        // open the first one
        await click(target.querySelector("input[data-field=date]"));
        let datepicker = document.querySelector(".o_datetime_picker");

        assert.isVisible(datepicker, "first date range picker should be opened");
        assert.strictEqual(
            datepicker.querySelector(".o_select_start").textContent,
            "3",
            "active start date should be '3' in date range picker"
        );
        assert.strictEqual(
            datepicker.querySelector(".o_select_end").textContent,
            "8",
            "active end date should be '8' in date range picker"
        );

        // Change date
        await click(getPickerCell("12").at(1));
        await click(getPickerCell("16").at(0));
        // Close picker
        await click(document.querySelector(".o_form_view"));

        // Check date after change
        assert.isNotVisible(datepicker, "date range picker should be closed");
        assert.strictEqual(
            target.querySelector("input[data-field=date]").value,
            "02/16/2017",
            "the date should be '02/16/2017'"
        );
        assert.strictEqual(
            target.querySelector("input[data-field=date_end]").value,
            "03/12/2017",
            "'the date should be '03/12/2017'"
        );

        // Try to change range with end date
        await click(target.querySelector("input[data-field=date_end]"));
        datepicker = document.querySelector(".o_datetime_picker");

        assert.isVisible(datepicker, "date range picker should be opened");
        assert.strictEqual(
            datepicker.querySelector(".o_select_start").textContent,
            "16",
            "start date should be a 16 in date range picker"
        );
        assert.strictEqual(
            datepicker.querySelector(".o_select_end").textContent,
            "12",
            "end date should be a 12 in date range picker"
        );

        // Change date
        await click(getPickerCell("13").at(0));
        await click(getPickerCell("18").at(1));
        // Close picker
        await click(document.querySelector(".o_form_view"));

        // Check date after change
        assert.isNotVisible(datepicker, "date range picker should be closed");
        assert.strictEqual(
            target.querySelector("input[data-field=date]").value,
            "02/13/2017",
            "the start date should be '02/13/2017'"
        );
        assert.strictEqual(
            target.querySelector("input[data-field=date_end]").value,
            "03/18/2017",
            "the end date should be '03/18/2017'"
        );

        // Save
        await clickSave(target);

        // Check date after save
        assert.strictEqual(
            target.querySelector("input[data-field=date]").value,
            "02/13/2017",
            "the start date should be '02/13/2017' after save"
        );
        assert.strictEqual(
            target.querySelector("input[data-field=date_end]").value,
            "03/18/2017",
            "the end date should be '03/18/2017' after save"
        );
    });

    QUnit.test(
        "date picker should still be present when scrolling outside of it",
        async (assert) => {
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                    </form>`,
            });

            await click(target.querySelector("input[data-field=datetime]"));
            assert.isVisible(
                document.querySelector(".o_datetime_picker"),
                "date range picker should be opened"
            );

            await triggerScroll(target, { top: 50 });
            assert.isVisible(
                document.querySelector(".o_datetime_picker"),
                "date range picker should still be opened"
            );
        }
    );

    QUnit.test("DateRangeField with label opens datepicker on click", async (assert) => {
        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
        serverData.models.partner.records[0].date_end = "2017-02-08";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="date" string="Daterange" />
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
                </form>`,
        });

        await click(target.querySelector("label.o_form_label"));
        assert.isVisible(
            document.querySelector(".o_datetime_picker"),
            "date range picker should be opened"
        );
    });

    QUnit.test(
        "Datetime field manually input value should send utc value to server",
        async (assert) => {
            assert.expect(4);

            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[1], { datetime: "2017-02-08 06:00:00" });
                    }
                },
            });

            // check date display correctly in readonly
            assert.strictEqual(
                target.querySelector(".o_field_daterange input").value,
                "02/08/2017 15:30:00",
                "the start date should be correctly displayed in readonly"
            );
            assert.strictEqual(
                target.querySelectorAll(".o_field_daterange input")[1].value,
                "03/13/2017 05:30:00",
                "the end date should be correctly displayed in readonly"
            );

            // update input for Datetime
            await editInput(target, "input[data-field=datetime]", "02/08/2017 11:30:00");
            // save form
            await clickSave(target);

            assert.strictEqual(
                target.querySelector(".o_field_daterange input").value,
                "02/08/2017 11:30:00",
                "the start date should be correctly displayed after manual update"
            );
        }
    );

    QUnit.test("Daterange field keyup should not erase end date", async (assert) => {
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                    </form>`,
            resId: 1,
        });

        // check date display correctly in readonly
        assert.strictEqual(
            target.querySelector(".o_field_daterange input").value,
            "02/08/2017 15:30:00",
            "the start date should be correctly displayed"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[1].value,
            "03/13/2017 05:30:00",
            "the end date should be correctly displayed"
        );

        // reveal the o_datetime_picker
        await click(target.querySelector("input[data-field=datetime]"));

        // the keyup event should not be handled by o_datetime_picker
        await triggerEvent(target, "input[data-field=datetime]", "keyup", {
            key: "ArrowLeft",
        });

        assert.strictEqual(
            target.querySelector(".o_field_daterange input").value,
            "02/08/2017 15:30:00",
            "the start date should be correctly displayed after onkeyup"
        );

        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[1].value,
            "03/13/2017 05:30:00",
            "the end date should be correctly displayed after onkeyup"
        );
    });

    // TODO: check if this test is still relevant
    // QUnit.test(
    //     "DateRangeField manually input wrong value should show toaster",
    //     async (assert)=> {
    //         serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
    //         serverData.models.partner.records[0].date_end = "2017-02-08";

    //         await makeView({
    //             type: "form",
    //             resModel: "partner",
    //             serverData,
    //             arch: `
    //                 <form>
    //                     <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
    //                 </form>`,
    //             resId: 1,
    //         });

    //         await editInput(target, "input[data-field=date]", "blabla");
    //         // click outside daterange field
    //         await click(target);
    //         assert.hasClass(
    //             target.querySelector(".o_field_daterange"),
    //             "o_field_invalid",
    //             "date field should be displayed as invalid"
    //         );
    //         // update input date with right value
    //         await editInput(target, "input[data-field=date]", "02/08/2017");
    //         assert.doesNotHaveClass(
    //             target.querySelector(".o_field_daterange[name='date']"),
    //             "o_field_invalid",
    //             "date field should not be displayed as invalid now"
    //         );

    //         // again enter wrong value and try to save should raise invalid fields value
    //         await editInput(target, "input[data-field=date]", "blabla");
    //         await clickSave(target);
    //         assert.strictEqual(
    //             target.querySelector(".o_notification_title").textContent,
    //             "Invalid fields: "
    //         );
    //         assert.strictEqual(
    //             target.querySelector(".o_notification_content").innerHTML,
    //             "<ul><li>A date</li></ul>"
    //         );
    //         assert.hasClass(target.querySelector(".o_notification"), "border-danger");
    //     }
    // );

    QUnit.test("Render with initial empty value: date field", async (assert) => {
        // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
        patchDate(2014, 7, 14, 12, 34, 56);
        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}"/>
                </form>`,
        });

        await click(target, "input[data-field=date]");
        assert.containsOnce(target, ".o_datetime_picker", "check that the datepicker is opened");

        // Select a value (today)
        await click(target.querySelector(".o_today"));

        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[0].value,
            "08/14/2014",
            "start date should be set properly"
        );

        // Add an end date
        await click(target.querySelector(".o_add_date"));

        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[0].value,
            target.querySelectorAll(".o_field_daterange input")[1].value,
            "the end date should be set to the same value as the start date"
        );
    });

    QUnit.test("Render with initial empty value: datetime field", async (assert) => {
        // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
        patchDate(2014, 7, 14, 12, 34, 56);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
        });

        await click(target, "input[data-field=datetime]");

        assert.containsOnce(target, ".o_datetime_picker", "check that the datepicker is opened");
        assert.containsNone(target, ".o_add_date");

        // Select a value (today)
        await click(target.querySelector(".o_today"));

        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[0].value,
            "08/14/2014 12:00:00",
            "start date should be set properly"
        );
        assert.notOk(isHiddenByCSS(target.querySelector(".o_add_date")));
        assert.strictEqual(
            target.querySelector(".o_add_date").innerText.trim().toLowerCase(),
            "add end date"
        );

        // Add an end date
        await click(target.querySelector(".o_add_date"));

        const [startInput, endInput] = target.querySelectorAll(".o_field_daterange input");
        assert.strictEqual(
            startInput.value,
            endInput.value,
            "the end date should be set to the same value as the start date"
        );
    });

    QUnit.test("Render with initial empty value and optional start date", async (assert) => {
        patchDate(2014, 7, 14, 12, 34, 56);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
        });

        await click(target, "input[data-field=datetime_end]");

        assert.containsOnce(target, ".o_datetime_picker", "check that the datepicker is opened");
        assert.containsNone(target, ".o_add_date");

        // Select a value (today)
        await click(target.querySelector(".o_today"));

        assert.strictEqual(
            target.querySelectorAll(".o_field_daterange input")[0].value,
            "08/14/2014 12:00:00",
            "end date should be set properly"
        );
        assert.notOk(isHiddenByCSS(target.querySelector(".o_add_date")));
        assert.strictEqual(
            target.querySelector(".o_add_date").innerText.trim().toLowerCase(),
            "add start date"
        );

        // Add an end date
        await click(target.querySelector(".o_add_date"));

        const [startInput, endInput] = target.querySelectorAll(".o_field_daterange input");
        assert.strictEqual(
            startInput.value,
            endInput.value,
            "the end date should be set to the same value as the start date"
        );
    });

    QUnit.test("initial empty date with optional start date", async (assert) => {
        patchDate(2014, 7, 14, 12, 34, 56);

        serverData.models.partner.records[0].datetime = "2017-03-13 00:00:00";
        serverData.models.partner.records[0].datetime_end = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.ok(isHiddenByCSS(target.querySelector(".o_add_date")));

        target.querySelector(".o_field_daterange input").focus();
        await nextTick();

        assert.notOk(isHiddenByCSS(target.querySelector(".o_add_date")));
        assert.containsNone(target, ".o_datetime_picker");
        assert.strictEqual(
            target.querySelector(".o_add_date").innerText.trim().toLowerCase(),
            "add end date"
        );

        // Add an end date
        await click(target.querySelector(".o_add_date"));

        const [startInput, endInput] = target.querySelectorAll(".o_field_daterange input");
        assert.containsOnce(target, ".o_datetime_picker");
        assert.strictEqual(
            startInput.value,
            endInput.value,
            "the end date should be set to the same value as the start date"
        );
    });

    QUnit.test("initial empty date with optional end date", async (assert) => {
        // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
        patchDate(2014, 7, 14, 12, 34, 56);

        serverData.models.partner.records[0].datetime = false;
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
            resId: 1,
        });

        assert.ok(isHiddenByCSS(target.querySelector(".o_add_date")));

        target.querySelector(".o_field_daterange input").focus();
        await nextTick();

        assert.notOk(isHiddenByCSS(target.querySelector(".o_add_date")));
        assert.strictEqual(
            target.querySelector(".o_add_date").innerText.trim().toLowerCase(),
            "add start date"
        );

        // Add a start date
        await click(target.querySelector(".o_add_date"));

        const [startInput, endInput] = target.querySelectorAll(".o_field_daterange input");
        assert.strictEqual(
            startInput.value,
            endInput.value,
            "the start date should be set to the same value as the end date"
        );
    });

    QUnit.test("Datetime field - open datepicker and switch page", async (assert) => {
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";
        serverData.models.partner.records.push({
            id: 2,
            date: "2017-03-04",
            datetime: "2017-03-10 11:00:00",
            datetime_end: "2017-04-15 00:00:00",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            resIds: [1, 2],
            serverData,
            arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                    </form>`,
        });

        // Check date range picker initialization
        assert.containsOnce(getFixture(), ".o_field_daterange");
        assert.containsNone(getFixture(), ".o_datetime_picker");

        // open datepicker
        await click(target.querySelector("input[data-field=datetime]"));

        let datepicker = document.querySelector(".o_datetime_picker");
        assert.isVisible(datepicker, "date range picker should be opened");

        // Start date: id=1
        assert.strictEqual(
            datepicker.querySelector(".o_select_start").textContent,
            "8",
            "active start date should be '8' in date range picker"
        );
        let [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
        assert.strictEqual(
            hourSelectStart.value,
            "15",
            "active start date hour should be '15' in date range picker"
        );
        assert.strictEqual(
            minuteSelectStart.value,
            "30",
            "active start date minute should be '30' in date range picker"
        );

        // End date: id=1
        assert.strictEqual(
            datepicker.querySelector(".o_select_end").textContent,
            "13",
            "active end date should be '13' in date range picker"
        );
        let [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
        assert.strictEqual(
            hourSelectEnd.value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            minuteSelectEnd.value,
            "30",
            "active end date minute should be '30' in date range picker"
        );

        // Close picker
        await click(document.querySelector(".o_form_view"));
        assert.isNotVisible(datepicker, "date range picker should be closed");

        await pagerNext(target);

        // Check date range picker initialization
        assert.containsOnce(getFixture(), ".o_field_daterange");
        assert.containsNone(getFixture(), ".o_datetime_picker");

        // open date range picker
        await click(target.querySelector("input[data-field=datetime]"));

        datepicker = document.querySelector(".o_datetime_picker");
        assert.isVisible(datepicker, "first date range picker should be opened");

        // Start date: id=2
        assert.strictEqual(
            datepicker.querySelector(".o_select_start").textContent,
            "10",
            "active start date should be '10' in date range picker"
        );
        [hourSelectStart, minuteSelectStart] = getTimePickers().at(0);
        assert.strictEqual(
            hourSelectStart.value,
            "16",
            "active start date hour should be '16' in date range picker"
        );
        assert.strictEqual(
            minuteSelectStart.value,
            "30",
            "active start date minute should be '30' in date range picker"
        );

        // End date id=2
        assert.strictEqual(
            datepicker.querySelector(".o_select_end").textContent,
            "15",
            "active end date should be '15' in date range picker"
        );
        [hourSelectEnd, minuteSelectEnd] = getTimePickers().at(1);
        assert.strictEqual(
            hourSelectEnd.value,
            "5",
            "active end date hour should be '5' in date range picker"
        );
        assert.strictEqual(
            minuteSelectEnd.value,
            "30",
            "active end date minute should be '30' in date range picker"
        );
    });

    QUnit.test("related end date, both start date and end date empty", async (assert) => {
        serverData.models.partner.records[0].datetime = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "");
        assert.containsNone(target, ".o_add_date");

        await editInput(getInputs()[0], null, "06/06/2023 12:00:00");

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "06/06/2023 12:00:00");
        assert.strictEqual(target.querySelector(".o_add_date").textContent.trim(), "Add end date");

        await click(target, ".o_add_date");

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "06/06/2023 12:00:00");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[0].value, "06/06/2023 12:00:00");
        assert.containsNone(target, ".o_add_date");
    });

    QUnit.test("required: related end date, both start date and end date empty", async (assert) => {
        serverData.models.partner.records[0].datetime = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}" required="datetime and datetime_end"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[1].value, "");
        assert.containsNone(target, ".o_add_date");

        await editInput(getInputs()[0], null, "06/06/2023 12:00:00");

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "06/06/2023 12:00:00");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[1].value, "");
        assert.containsNone(target, ".o_add_date");

        await editInput(getInputs()[1], null, "07/07/2023 13:00:00");

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "06/06/2023 12:00:00");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[1].value, "07/07/2023 13:00:00");
        assert.containsNone(target, ".o_add_date");

        await editInput(getInputs()[0], null, "");

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[1].value, "07/07/2023 13:00:00");
        assert.containsNone(target, ".o_add_date");
    });

    QUnit.test("related start date, both start date and end date empty", async (assert) => {
        serverData.models.partner.records[0].datetime = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[0].value, "");
        assert.containsNone(target, ".o_add_date");
    });

    QUnit.test("related end date, start date set and end date empty", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(target.querySelector(".o_add_date").textContent.trim(), "Add end date");
    });

    QUnit.test("related start date, start date set and end date empty", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(target.querySelector(".o_add_date").textContent.trim(), "Add end date");
    });

    QUnit.test("related end date, start date empty and end date set", async (assert) => {
        const recordData = serverData.models.partner.records[0];
        recordData.datetime_end = recordData.datetime;
        recordData.datetime = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime_end");
        assert.strictEqual(
            target.querySelector(".o_add_date").textContent.trim(),
            "Add start date"
        );
    });

    QUnit.test("related start date, start date empty and end date set", async (assert) => {
        const recordData = serverData.models.partner.records[0];
        recordData.datetime_end = recordData.datetime;
        recordData.datetime = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime_end");
        assert.strictEqual(
            target.querySelector(".o_add_date").textContent.trim(),
            "Add start date"
        );
    });

    QUnit.test("related end date, both start date and end date set", async (assert) => {
        const recordData = serverData.models.partner.records[0];
        recordData.datetime_end = recordData.datetime;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime" widget="daterange" options="{'end_date_field': 'datetime_end'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.containsNone(target, ".o_add_date");
    });

    QUnit.test("related start date, both start date and end date set", async (assert) => {
        const recordData = serverData.models.partner.records[0];
        recordData.datetime_end = recordData.datetime;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="datetime_end" widget="daterange" options="{'start_date_field': 'datetime'}"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs().length, 2);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime");
        assert.strictEqual(getInputs()[0].value, "02/08/2017 15:30:00");
        assert.hasAttrValue(getInputs()[1], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[0].value, "02/08/2017 15:30:00");
        assert.containsNone(target, ".o_add_date");

        await editInput(getInputs()[0], null, "");

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[0].value, "02/08/2017 15:30:00");
        assert.strictEqual(
            target.querySelector(".o_add_date").textContent.trim(),
            "Add start date"
        );

        await editInput(getInputs()[0], null, "");

        assert.strictEqual(getInputs().length, 1);
        assert.hasAttrValue(getInputs()[0], "data-field", "datetime_end");
        assert.strictEqual(getInputs()[0].value, "");
        assert.containsNone(target, ".o_add_date");
    });

    QUnit.test("related start date, required, both start date and end date set", async (assert) => {
        serverData.models.partner.fields.date_end = { string: "Some Date", type: "date" };
        const [firstRecord] = serverData.models.partner.records;
        firstRecord.date_end = firstRecord.date;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <form>
                    <field name="date" widget="daterange" options="{'start_date_field': 'date_end'}" required="1" />
                </form>`,
            resId: 1,
        });

        assert.strictEqual(getInputs()[0].value, "02/03/2017");
        assert.containsOnce(target, ".fa-long-arrow-right");
        assert.strictEqual(getInputs()[1].value, "02/03/2017");
    });

    QUnit.test("list daterange with start date and empty end date", async (assert) => {
        serverData.models.partner.fields.date_end = { string: "Some Date", type: "date" };

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <tree>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                </tree>`,
        });

        const arrowIcon = target.querySelector(".fa-long-arrow-right");
        const textSiblings = [...arrowIcon.parentNode.childNodes]
            .map((node) => {
                if (node === arrowIcon) {
                    return "->";
                } else if (node.nodeType === 3) {
                    return node.nodeValue.trim();
                } else {
                    return false;
                }
            })
            .filter(Boolean);

        assert.deepEqual(textSiblings, ["02/03/2017", "->"]);
    });

    QUnit.test("list daterange with empty start date and end date", async (assert) => {
        serverData.models.partner.fields.date_end = { string: "Some Date", type: "date" };
        const [firstRecord] = serverData.models.partner.records;
        [firstRecord.date, firstRecord.date_end] = [firstRecord.date_end, firstRecord.date];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: /* xml */ `
                <tree>
                    <field name="date" widget="daterange" options="{'end_date_field': 'date_end'}" />
                </tree>`,
        });

        const arrowIcon = target.querySelector(".fa-long-arrow-right");
        const textSiblings = [...arrowIcon.parentNode.childNodes]
            .map((node) => {
                if (node === arrowIcon) {
                    return "->";
                } else if (node.nodeType === 3) {
                    return node.nodeValue.trim();
                } else {
                    return false;
                }
            })
            .filter(Boolean);

        assert.deepEqual(textSiblings, ["->", "02/03/2017"]);
    });
});
