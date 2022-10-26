/** @odoo-module **/

import {
    click,
    clickSave,
    editInput,
    getFixture,
    patchDate,
    patchTimeZone,
    triggerEvent,
    triggerScroll,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

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

    QUnit.test(
        "Datetime field - interaction with the datepicker [REQUIRE FOCUS]",
        async function (assert) {
            serverData.models.partner.fields.datetime_end = {
                string: "Datetime End",
                type: "datetime",
            };
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                        <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                    </form>`,
            });

            // Check date range picker initialization
            assert.containsN(
                document.body,
                ".daterangepicker",
                2,
                "should initialize 2 date range picker"
            );
            const datepickers = document.querySelectorAll(`.daterangepicker`);
            assert.isNotVisible(
                datepickers[0],
                "first date range picker should be closed initially"
            );
            assert.isNotVisible(
                datepickers[datepickers.length - 1],
                "second date range picker should be closed initially"
            );

            // open the first one
            let fields = target.querySelectorAll(".o_field_daterange");
            await click(fields[0].querySelector("input"));

            let datepicker = document.querySelector(
                `.daterangepicker[data-name="${fields[0].getAttribute("name")}"]`
            );
            assert.isVisible(datepicker, "first date range picker should be opened");
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .active.start-date").textContent,
                "8",
                "active start date should be '8' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .hourselect").value,
                "15",
                "active start date hour should be '15' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .minuteselect").value,
                "30",
                "active start date minute should be '30' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .active.end-date").textContent,
                "13",
                "active end date should be '13' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .hourselect").value,
                "5",
                "active end date hour should be '5' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .minuteselect").value,
                "30",
                "active end date minute should be '30' in date range picker"
            );
            assert.containsN(
                datepicker.querySelector(".drp-calendar.left .minuteselect"),
                "option",
                12,
                "minute selection should contain 12 options (1 for each 5 minutes)"
            );
            // Close picker
            await click(datepicker.querySelector(".cancelBtn"));
            assert.strictEqual(
                datepicker.style.display,
                "none",
                "date range picker should be closed"
            );

            // Try to check with end date
            await click(fields[fields.length - 1], "input");
            datepicker = document.querySelector(
                `.daterangepicker[data-name="${fields[fields.length - 1].getAttribute("name")}"]`
            );

            assert.isVisible(datepicker, "date range picker should be opened");
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .active.start-date").textContent,
                "8",
                "active start date should be '8' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .hourselect").value,
                "15",
                "active start date hour should be '15' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.left .minuteselect").value,
                "30",
                "active start date minute should be '30' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .active.end-date").textContent,
                "13",
                "active end date should be '13' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .hourselect").value,
                "5",
                "active end date hour should be '5' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".drp-calendar.right .minuteselect").value,
                "30",
                "active end date minute should be '30' in date range picker"
            );

            // Select a new range and check that inputs are updated
            await triggerEvent(datepicker, ".start-date", "mousedown"); // 02/08/2017
            await triggerEvent(datepicker, ".start-date + .available", "mousedown"); // 02/09/2017
            await click(datepicker, ".applyBtn");
            assert.equal(
                target.querySelector("[name=datetime] input").value,
                "02/08/2017 15:30:00"
            );
            assert.equal(
                target.querySelector("[name=datetime_end] input").value,
                "02/09/2017 05:30:00"
            );

            // Save
            await clickSave(target);
            fields = target.querySelectorAll(".o_field_daterange input");

            // Check date after save
            assert.strictEqual(fields[0].value, "02/08/2017 15:30:00");
            assert.strictEqual(fields[fields.length - 1].value, "02/09/2017 05:30:00");
        }
    );

    QUnit.test(
        "Date field - interaction with the datepicker [REQUIRE FOCUS]",
        async function (assert) {
            serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
            serverData.models.partner.records[0].date_end = "2017-02-08";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="date" widget="daterange" options="{'related_end_date': 'date_end'}"/>
                        <field name="date_end" widget="daterange" options="{'related_start_date': 'date'}"/>
                    </form>`,
            });

            let fields = target.querySelectorAll(".o_field_daterange");
            const datepickers = document.querySelectorAll(`.daterangepicker`);

            // Check date range picker initialization
            assert.containsN(
                document.body,
                ".daterangepicker",
                2,
                "should initialize 2 date range picker"
            );
            assert.isNotVisible(
                datepickers[0],
                "first date range picker should be closed initially"
            );
            assert.isNotVisible(
                datepickers[datepickers.length - 1],
                "second date range picker should be closed initially"
            );

            // open the first one
            await click(fields[0].querySelector("input"));
            let datepicker = document.querySelector(
                `.daterangepicker[data-name="${fields[0].getAttribute("name")}"]`
            );

            assert.isVisible(datepicker, "first date range picker should be opened");
            assert.strictEqual(
                datepicker.querySelector(".active.start-date").textContent,
                "3",
                "active start date should be '3' in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".active.end-date").textContent,
                "8",
                "active end date should be '8' in date range picker"
            );

            // Change date
            await triggerEvent(
                datepicker,
                ".drp-calendar.left .available[data-title='r2c4']",
                "mousedown"
            );
            await triggerEvent(
                datepicker,
                ".drp-calendar.right .available[data-title='r2c0']",
                "mousedown"
            );
            await click(datepicker.querySelector(".applyBtn"));

            // Check date after change
            assert.isNotVisible(datepicker, "date range picker should be closed");
            assert.strictEqual(
                fields[0].querySelector("input").value,
                "02/16/2017",
                "the date should be '02/16/2017'"
            );
            assert.strictEqual(
                fields[1].querySelector("input").value,
                "03/12/2017",
                "'the date should be '03/12/2017'"
            );

            // Try to change range with end date
            await click(fields[1].querySelector("input"));
            datepicker = document.querySelector(
                `.daterangepicker[data-name="${fields[1].getAttribute("name")}"]`
            );

            assert.isVisible(datepicker, "date range picker should be opened");
            assert.strictEqual(
                datepicker.querySelector(".active.start-date").textContent,
                "16",
                "start date should be a 16 in date range picker"
            );
            assert.strictEqual(
                datepicker.querySelector(".active.end-date").textContent,
                "12",
                "end date should be a 12 in date range picker"
            );

            // Change date
            await triggerEvent(
                datepicker,
                ".drp-calendar.left .available[data-title='r2c1']",
                "mousedown"
            );
            await triggerEvent(
                datepicker,
                ".drp-calendar.right .available[data-title='r2c6']",
                "mousedown"
            );
            await click(datepicker, ".applyBtn");

            // Check date after change
            assert.isNotVisible(
                datepickers[datepickers.length - 1],
                "date range picker should be closed"
            );
            assert.strictEqual(
                fields[0].querySelector("input").value,
                "02/13/2017",
                "the start date should be '02/13/2017'"
            );
            assert.strictEqual(
                fields[1].querySelector("input").value,
                "03/18/2017",
                "the end date should be '03/18/2017'"
            );

            // Save
            await clickSave(target);
            fields = target.querySelectorAll(".o_field_daterange");

            // Check date after save
            assert.strictEqual(
                fields[0].querySelector("input").value,
                "02/13/2017",
                "the start date should be '02/13/2017' after save"
            );
            assert.strictEqual(
                fields[1].querySelector("input").value,
                "03/18/2017",
                "the end date should be '03/18/2017' after save"
            );
        }
    );

    QUnit.test(
        "daterangepicker should disappear on scrolling outside of it",
        async function (assert) {
            serverData.models.partner.fields.datetime_end = {
                string: "Datetime End",
                type: "datetime",
            };
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                        <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                    </form>`,
            });

            await click(target.querySelector(".o_field_daterange[name='datetime'] input"));
            assert.isVisible(
                document.querySelector(".daterangepicker[data-name='datetime']"),
                "date range picker should be opened"
            );

            await triggerScroll(target, { top: 50 });
            assert.isNotVisible(
                document.querySelector(".daterangepicker[data-name='datetime']"),
                "date range picker should be closed"
            );
        }
    );

    QUnit.test("DateRangeField with label opens datepicker on click", async function (assert) {
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
                    <field name="date" widget="daterange" options="{'related_end_date': 'date_end'}"/>
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date'}"/>
                </form>`,
        });

        await click(target.querySelector("label.o_form_label"));
        assert.isVisible(
            document.querySelector(".daterangepicker[data-name='date']"),
            "date range picker should be opened"
        );
    });

    QUnit.test(
        "Datetime field manually input value should send utc value to server",
        async function (assert) {
            assert.expect(4);

            serverData.models.partner.fields.datetime_end = {
                string: "Datetime End",
                type: "datetime",
            };
            serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                        <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "write") {
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
            await editInput(
                target,
                ".o_field_daterange[name='datetime'] input",
                "02/08/2017 11:30:00"
            );
            // save form
            await clickSave(target);

            assert.strictEqual(
                target.querySelector(".o_field_daterange input").value,
                "02/08/2017 11:30:00",
                "the start date should be correctly displayed after manual update"
            );
        }
    );

    QUnit.test(
        "DateRangeField manually input wrong value should show toaster",
        async function (assert) {
            serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };
            serverData.models.partner.records[0].date_end = "2017-02-08";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="date" widget="daterange" options="{'related_end_date': 'date_end'}"/>
                        <field name="date_end" widget="daterange" options="{'related_start_date': 'date'}"/>
                    </form>`,
                resId: 1,
            });

            await editInput(target, ".o_field_daterange[name='date'] input", "blabla");
            // click outside daterange field
            await click(target);
            assert.hasClass(
                target.querySelector(".o_field_daterange[name='date']"),
                "o_field_invalid",
                "date field should be displayed as invalid"
            );
            // update input date with right value
            await editInput(target, ".o_field_daterange[name='date'] input", "02/08/2017");
            assert.doesNotHaveClass(
                target.querySelector(".o_field_daterange[name='date']"),
                "o_field_invalid",
                "date field should not be displayed as invalid now"
            );

            // again enter wrong value and try to save should raise invalid fields value
            await editInput(target, ".o_field_daterange[name='date'] input", "blabla");
            await clickSave(target);
            assert.strictEqual(
                target.querySelector(".o_notification_title").textContent,
                "Invalid fields: "
            );
            assert.strictEqual(
                target.querySelector(".o_notification_content").innerHTML,
                "<ul><li>A date</li></ul>"
            );
            assert.hasClass(target.querySelector(".o_notification"), "border-danger");
        }
    );

    QUnit.test("Render with initial empty value: date field", async function (assert) {
        // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
        patchDate(2014, 7, 14, 12, 34, 56);
        serverData.models.partner.fields.date_end = { string: "Date End", type: "date" };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="date" widget="daterange" options="{'related_end_date': 'date_end'}"/>
                    <field name="date_end" widget="daterange" options="{'related_start_date': 'date'}"/>
                </form>`,
        });

        await click(document.body, ".o_field_daterange[name=date] input");
        assert.containsN(document.body, ".month", 2);
        assert.equal(document.body.querySelectorAll(".month")[0].textContent, "Aug 2014");
        assert.equal(document.body.querySelectorAll(".month")[1].textContent, "Sep 2014");
    });

    QUnit.test("Render with initial empty value: datetime field", async function (assert) {
        // 2014-08-14 12:34:56 -> the day E. Zuckerman, who invented pop-up ads, has apologised.
        patchDate(2014, 7, 14, 12, 34, 56);
        serverData.models.partner.fields.datetime_end = {
            string: "Datetime End",
            type: "datetime",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end'}"/>
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime'}"/>
                </form>`,
        });

        await click(document.body, ".o_field_daterange[name=datetime] input");
        assert.containsN(document.body, ".month", 2);
        assert.equal(document.body.querySelectorAll(".month")[0].textContent, "Aug 2014");
        assert.equal(document.body.querySelectorAll(".month")[1].textContent, "Sep 2014");
    });

    QUnit.test("Datetime field with option format type is 'date'", async function (assert) {
        serverData.models.partner.fields.datetime_end = {
            string: "Datetime End",
            type: "datetime",
        };
        serverData.models.partner.records[0].datetime_end = "2017-03-13 00:00:00";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="datetime" widget="daterange" options="{'related_end_date': 'datetime_end', 'format_type': 'date'}"/>'
                    <field name="datetime_end" widget="daterange" options="{'related_start_date': 'datetime', 'format_type': 'date'}"/>'
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_daterange[name='datetime'] input").value,
            "02/08/2017",
            "the start date should only show date when option formatType is Date"
        );
        assert.strictEqual(
            target.querySelector(".o_field_daterange[name='datetime_end'] input").value,
            "03/13/2017",
            "the end date should only show date when option formatType is Date"
        );
    });
});
