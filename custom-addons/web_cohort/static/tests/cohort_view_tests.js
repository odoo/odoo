/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import {
    click,
    getFixture,
    nextTick,
    patchWithCleanup,
    makeDeferred,
    mockDownload,
    patchDate,
} from "@web/../tests/helpers/utils";
import { makeView } from "@web/../tests/views/helpers";
import {
    toggleSearchBarMenu,
    toggleMenuItem,
    toggleMenuItemOption,
    toggleMenu,
    removeFacet,
    setupControlPanelServiceRegistry,
} from "@web/../tests/search/helpers";
import { browser } from "@web/core/browser/browser";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { markup } from "@odoo/owl";

const serviceRegistry = registry.category("services");

let serverData;
let target;

async function changeScale(target, scale) {
    await click(target.querySelector(".o_view_scale_selector .dropdown-toggle"));
    await click(target.querySelector(`.o_scale_button_${scale}`));
}

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                subscription: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        start: { string: "Start", type: "date", sortable: true },
                        stop: { string: "Stop", type: "date", sortable: true },
                        recurring: {
                            string: "Recurring Price",
                            type: "integer",
                            store: true,
                            group_operator: "sum",
                        },
                    },
                    records: [
                        { id: 1, start: "2017-07-12", stop: "2017-08-11", recurring: 10 },
                        { id: 2, start: "2017-08-14", stop: "", recurring: 20 },
                        { id: 3, start: "2017-08-21", stop: "2017-08-29", recurring: 10 },
                        { id: 4, start: "2017-08-21", stop: "", recurring: 20 },
                        { id: 5, start: "2017-08-23", stop: "", recurring: 10 },
                        { id: 6, start: "2017-08-24", stop: "", recurring: 22 },
                        { id: 7, start: "2017-08-24", stop: "2017-08-29", recurring: 10 },
                        { id: 8, start: "2017-08-24", stop: "", recurring: 22 },
                    ],
                },
                lead: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        start: { string: "Start", type: "date" },
                        stop: { string: "Stop", type: "date" },
                        revenue: { string: "Revenue", type: "float", store: true },
                    },
                    records: [
                        { id: 1, start: "2017-07-12", stop: "2017-08-11", revenue: 1200.2 },
                        { id: 2, start: "2017-08-14", stop: "", revenue: 500 },
                        { id: 3, start: "2017-08-21", stop: "2017-08-29", revenue: 5599.99 },
                        { id: 4, start: "2017-08-21", stop: "", revenue: 13500 },
                        { id: 5, start: "2017-08-23", stop: "", revenue: 6000 },
                        { id: 6, start: "2017-08-24", stop: "", revenue: 1499.99 },
                        { id: 7, start: "2017-08-24", stop: "2017-08-29", revenue: 16000 },
                        { id: 8, start: "2017-08-24", stop: "", revenue: 22000 },
                    ],
                },
                attendee: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        event_begin_date: { string: "Event Start Date", type: "date" },
                        registration_date: { string: "Registration Date", type: "date" },
                    },
                    records: [
                        {
                            id: 1,
                            event_begin_date: "2018-06-30",
                            registration_date: "2018-06-13",
                        },
                        {
                            id: 2,
                            event_begin_date: "2018-06-30",
                            registration_date: "2018-06-20",
                        },
                        {
                            id: 3,
                            event_begin_date: "2018-06-30",
                            registration_date: "2018-06-22",
                        },
                        {
                            id: 4,
                            event_begin_date: "2018-06-30",
                            registration_date: "2018-06-22",
                        },
                        {
                            id: 5,
                            event_begin_date: "2018-06-30",
                            registration_date: "2018-06-29",
                        },
                    ],
                },
            },
        };
        setupControlPanelServiceRegistry();
        serviceRegistry.add("localization", makeFakeLocalizationService());

        target = getFixture();
    });
    QUnit.module("CohortView");

    QUnit.test("simple cohort rendering", async function (assert) {
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        assert.hasClass(target.querySelector(".o_cohort_view"), "o_view_controller");
        assert.containsOnce(target, ".table", "should have a table");
        assert.containsOnce(
            target,
            ".table thead tr:first th:first:contains(Start)",
            'should contain "Start" in header of first column'
        );
        assert.containsOnce(
            target,
            ".table thead tr:first th:nth-child(3):contains(Stop - By Day)",
            'should contain "Stop - By Day" in title'
        );
        assert.containsOnce(
            target,
            ".table thead tr:nth-child(2) th:first:contains(+0)",
            "interval should start with 0"
        );
        assert.containsOnce(
            target,
            ".table thead tr:nth-child(2) th:nth-child(16):contains(+15)",
            "interval should end with 15"
        );

        await toggleMenu(target, "Measures");
        assert.containsOnce(target, ".dropdown-menu:not(.d-none)", "should have list of measures");

        await click(target, ".o_view_scale_selector .scale_button_selection");
        assert.containsN(
            target,
            ".o_view_scale_selector .dropdown-menu span",
            4,
            "should have buttons of intervals"
        );
    });

    QUnit.test("no content helper", async function (assert) {
        serverData.models.subscription.records = [];

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        assert.containsOnce(target, "div.o_view_nocontent");
        // Renderer is still displayed beside the no content helper
        assert.containsOnce(target, ".o_cohort_renderer");
        assert.containsN(target, ".o_content button", 3);
    });

    QUnit.test("no content helper after update", async function (assert) {
        serverData.views = {
            "subscription,false,cohort": `<cohort string="Subscription" date_start="start" date_stop="stop" measure="recurring"/>`,
            "subscription,false,search": `
                <search>
                    <filter name="recurring_bigger_25" string="Recurring bigger than 25" domain="[('recurring', '>', 25)]"/>
                </search>
            `,
        };
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            config: {
                views: [[false, "search"]],
            },
        });

        assert.containsNone(target, "div.o_view_nocontent");

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Recurring bigger than 25");

        assert.containsOnce(target, "div.o_view_nocontent");
    });

    QUnit.test("correctly set by default measure and interval", async function (assert) {
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        await toggleMenu(target, "Measures");

        assert.equal(
            target.querySelector(".dropdown-menu span.selected").textContent,
            "Count",
            "count should be the default for measure field"
        );

        assert.equal(
            target.querySelector(".o_view_scale_selector button").textContent,
            "Day",
            "day should by default for interval"
        );

        assert.equal(
            target.querySelector(".table thead th:nth-child(2)").textContent,
            "Count",
            'should contain "Count" in header of second column'
        );
        assert.equal(
            target.querySelector(".table thead th:nth-child(3)").textContent,
            "Stop - By Day",
            'should contain "Stop - By Day" in title'
        );
    });

    QUnit.test("correctly sort measure items", async function (assert) {
        // It's important to compare capitalized and lowercased words
        // to be sure the sorting is effective with both of them
        serverData.models.subscription.fields.flop = {
            string: "Abc",
            type: "integer",
            store: true,
            group_operator: "sum",
        };
        serverData.models.subscription.fields.add = {
            string: "add",
            type: "integer",
            store: true,
            group_operator: "sum",
        };
        serverData.models.subscription.fields.zoo = {
            string: "Zoo",
            type: "integer",
            store: true,
            group_operator: "sum",
        };

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop"/>',
        });

        await toggleMenu(target, "Measures");

        const measureButtonEls = target.querySelectorAll(".dropdown-menu span");
        assert.deepEqual(
            [...measureButtonEls].map((e) => e.innerText.trim()),
            ["Abc", "add", "Recurring Price", "Zoo", "Count"]
        );
    });

    QUnit.test("correctly set measure and interval after changed", async function (assert) {
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" measure="recurring" interval="week" />',
        });

        await toggleMenu(target, "Measures");
        assert.equal(
            target.querySelector(".dropdown-menu span.selected").textContent,
            "Recurring Price",
            "should recurring for measure"
        );

        await click(target.querySelector(".o_view_scale_selector .dropdown-toggle"));
        assert.equal(
            target.querySelector(".o_view_scale_selector .active").textContent,
            "Week",
            "should week for interval"
        );
        assert.equal(
            target.querySelector(".table thead th:nth-child(2)").textContent,
            "Recurring Price",
            'should contain "Recurring Price" in header of second column'
        );
        assert.equal(
            target.querySelector(".table thead th:nth-child(3)").textContent,
            "Stop - By Week",
            'should contain "Stop - By Week" in title'
        );

        await toggleMenu(target, "Measures");
        await click(target.querySelector(".dropdown-menu span:not(.selected)"));
        assert.equal(
            target.querySelector(".dropdown-menu span.selected").textContent,
            "Count",
            "should active count for measure"
        );
        assert.equal(
            target.querySelector(".table thead th:nth-child(2)").textContent,
            "Count",
            'should contain "Count" in header of second column'
        );

        await changeScale(target, "month");
        assert.equal(
            target.querySelector(".table thead th:nth-child(3)").textContent,
            "Stop - By Month",
            'should contain "Stop - By Month" in title'
        );
    });

    QUnit.test("cohort view without attribute invisible on field", async function (assert) {
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: `<cohort string="Subscription" date_start="start" date_stop="stop"/>`,
        });

        await toggleMenu(target, "Measures");
        const cohortMeasureList = target.querySelectorAll(".dropdown-menu span");
        assert.equal(cohortMeasureList.length, 2);
        assert.equal(cohortMeasureList[0].textContent, "Recurring Price");
        assert.equal(cohortMeasureList[1].textContent, "Count");
    });

    QUnit.test("cohort view with attribute invisible on field", async function (assert) {
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: `
                <cohort string="Subscription" date_start="start" date_stop="stop">
                    <field name="recurring" invisible="1"/>
                </cohort>`,
        });

        await toggleMenu(target, "Measures");
        assert.containsOnce(target, ".dropdown-menu span");
        assert.notEqual(target.querySelector(".dropdown-menu span").textContent, "Recurring Price");
    });

    QUnit.test("export cohort", async function (assert) {
        assert.expect(6);

        mockDownload((options) => {
            var data = JSON.parse(options.data.data);
            assert.strictEqual(options.url, "/web/cohort/export");
            assert.strictEqual(data.interval_string, "Day");
            assert.strictEqual(data.measure_string, "Count");
            assert.strictEqual(data.date_start_string, "Start");
            assert.strictEqual(data.date_stop_string, "Stop");
            assert.strictEqual(data.title, "Subscription");
            return Promise.resolve();
        });

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
        });

        await click(target.querySelector(".o_cohort_download_button"));
    });

    QUnit.test(
        "when clicked on cell redirects to the correct list/form view ",
        async function (assert) {
            serverData.views = {
                "subscription,false,cohort": `
                    <cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count" interval="week" />`,
                "subscription,my_list_view,list": `
                    <tree>
                        <field name="start"/>
                        <field name="stop"/>
                    </tree>`,
                "subscription,my_form_view,form": `
                    <form>
                        <field name="start"/>
                        <field name="stop"/>
                    </form>`,
                "subscription,false,list": `
                    <tree>
                        <field name="recurring"/>
                        <field name="start"/>
                    </tree>`,
                "subscription,false,form": `
                    <form>
                        <field name="recurring"/>
                        <field name="start"/>
                    </form>`,
                "subscription,false,search": `<search></search>`,
            };

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                name: "Subscriptions",
                res_model: "subscription",
                type: "ir.actions.act_window",
                views: [
                    [false, "cohort"],
                    ["my_list_view", "list"],
                    ["my_form_view", "form"],
                ],
            });

            // Going to the list view, while clicking Period / Count cell
            await click(target.querySelector("td.o_cohort_value"));

            let listColumnsHeads = target.querySelectorAll(".o_list_view th");
            assert.strictEqual(
                listColumnsHeads[1].textContent,
                "Start",
                "First field in the list view should be start"
            );
            assert.strictEqual(
                listColumnsHeads[2].textContent,
                "Stop",
                "First field in the list view should be start"
            );
            // Going back to cohort view
            await click(target.querySelector(".o_back_button"));
            // Going to the list view
            await click(target.querySelector("td div.o_cohort_value"));
            listColumnsHeads = target.querySelectorAll(".o_list_view th");
            assert.strictEqual(
                listColumnsHeads[1].textContent,
                "Start",
                "First field in the list view should be start"
            );
            assert.strictEqual(
                listColumnsHeads[2].textContent,
                "Stop",
                "First field in the list view should be start"
            );
            // Going to the form view
            await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));

            const fieldWidgets = target.querySelectorAll(".o_form_view .o_field_widget");
            assert.hasAttrValue(
                fieldWidgets[0],
                "name",
                "start",
                "First field in the form view should be start"
            );
            assert.hasAttrValue(
                fieldWidgets[1],
                "name",
                "stop",
                "Second field in the form view should be stop"
            );
        }
    );

    QUnit.test("test mode churn", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "cohort",
            resModel: "lead",
            serverData,
            arch: '<cohort string="Leads" date_start="start" date_stop="stop" interval="week" mode="churn" />',
            mockRPC: function (route, args) {
                if (args.method === "get_cohort_data") {
                    assert.strictEqual(
                        args.kwargs.mode,
                        "churn",
                        "churn mode should be sent via RPC"
                    );
                }
            },
        });

        const values = target.querySelectorAll("td .o_cohort_value");
        assert.strictEqual(
            values[0].textContent.trim(),
            "0%",
            "first col should display 0 percent"
        );
        assert.strictEqual(
            values[4].textContent.trim(),
            "100%",
            "col 5 should display 100 percent"
        );
    });

    QUnit.test("test backward timeline", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "cohort",
            resModel: "attendee",
            serverData,
            arch: '<cohort string="Attendees" date_start="event_begin_date" date_stop="registration_date" interval="day" timeline="backward" mode="churn"/>',
            mockRPC: function (route, args) {
                if (args.method === "get_cohort_data") {
                    assert.strictEqual(
                        args.kwargs.timeline,
                        "backward",
                        "backward timeline should be sent via RPC"
                    );
                }
            },
        });
        const columnsTh = target.querySelectorAll(".table thead tr:nth-child(2) th");
        assert.equal(columnsTh[0].textContent, "-15", "interval should start with -15");
        assert.equal(columnsTh[15].textContent, "0", "interval should end with 0");
        const values = target.querySelectorAll("td .o_cohort_value");
        assert.equal(values[0].textContent.trim(), "20%", "first col should display 20 percent");
        assert.equal(values[5].textContent.trim(), "40%", "col 6 should display 40 percent");
        assert.equal(values[7].textContent.trim(), "80%", "col 8 should display 80 percent");
        assert.equal(values[14].textContent.trim(), "100%", "col 15 should display 100 percent");
    });

    QUnit.test(
        "when clicked on cell redirects to the action list/form view passed in context",
        async function (assert) {
            serverData.views = {
                "subscription,false,cohort": `
                    <cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count" interval="week" />`,
                "subscription,my_list_view,list": `
                    <tree>
                        <field name="start"/>
                        <field name="stop"/>
                    </tree>`,
                "subscription,my_form_view,form": `
                    <form>
                        <field name="start"/>
                        <field name="stop"/>
                    </form>`,
                "subscription,false,list": `
                    <tree>
                        <field name="recurring"/>
                        <field name="start"/>
                    </tree>`,
                "subscription,false,form": `
                    <form>
                        <field name="recurring"/>
                        <field name="start"/>
                    </form>`,
                "subscription,false,search": `<search></search>`,
            };

            const webClient = await createWebClient({ serverData });

            await doAction(webClient, {
                name: "Subscriptions",
                res_model: "subscription",
                type: "ir.actions.act_window",
                views: [[false, "cohort"]],
                context: { list_view_id: "my_list_view", form_view_id: "my_form_view" },
            });

            // Going to the list view, while clicking Period / Count cell
            await click(target.querySelector("td.o_cohort_value"));

            let listColumnsHeads = target.querySelectorAll(".o_list_view th");
            assert.strictEqual(
                listColumnsHeads[1].textContent,
                "Start",
                "First field in the list view should be start"
            );
            assert.strictEqual(
                listColumnsHeads[2].textContent,
                "Stop",
                "First field in the list view should be start"
            );
            // Going back to cohort view
            await click(target.querySelector(".o_back_button"));
            // Going to the list view
            await click(target.querySelector("td div.o_cohort_value"));
            listColumnsHeads = target.querySelectorAll(".o_list_view th");
            assert.strictEqual(
                listColumnsHeads[1].textContent,
                "Start",
                "First field in the list view should be start"
            );
            assert.strictEqual(
                listColumnsHeads[2].textContent,
                "Stop",
                "First field in the list view should be start"
            );
            // Going to the form view
            await click(target.querySelector(".o_list_view .o_data_row .o_data_cell"));

            const fieldWidgets = target.querySelectorAll(".o_form_view .o_field_widget");
            assert.hasAttrValue(
                fieldWidgets[0],
                "name",
                "start",
                "First field in the form view should be start"
            );
            assert.hasAttrValue(
                fieldWidgets[1],
                "name",
                "stop",
                "Second field in the form view should be stop"
            );
        }
    );

    QUnit.test("rendering of a cohort view with comparison", async function (assert) {
        assert.expect(31);

        patchDate(2017, 7, 25, 1, 0, 0);

        serverData.views = {
            "subscription,false,cohort":
                '<cohort string="Subscriptions" date_start="start" date_stop="stop" measure="__count" interval="week" />',
            "subscription,false,search": `
                <search>
                    <filter date="start" name="date_filter" string="Date"/>
                </search>
            `,
        };
        patchWithCleanup(browser, { setTimeout: (fn) => fn() });
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, {
            name: "Subscriptions",
            res_model: "subscription",
            type: "ir.actions.act_window",
            views: [[false, "cohort"]],
        });

        function verifyContents(results, label) {
            const tables = target.querySelectorAll("table");
            assert.strictEqual(
                tables.length,
                results.length,
                `${label}: There should be ${results.length} tables`
            );
            tables.forEach((table) => {
                const result = results.shift();
                const rowCount = table.querySelectorAll(".o_cohort_row_clickable").length;

                if (rowCount) {
                    assert.strictEqual(rowCount, result, `the table should contain ${result} rows`);
                } else {
                    assert.strictEqual(
                        table.querySelector("th").textContent.trim(),
                        result,
                        `the table should contain the time range description ${result}`
                    );
                }
            });
        }

        // with no comparison, with data (no filter)
        verifyContents([3], "with no comparison, with data (no filter)");
        assert.containsNone(target, ".o_cohort_no_data");
        assert.containsNone(target, "div.o_view_nocontent");

        // with no comparison with no data (filter on 'last_year')
        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Date");
        await toggleMenuItemOption(target, "Date", "2016");

        verifyContents([], "with no comparison with no data (filter on 'last_year'");
        assert.containsNone(target, ".o_cohort_no_data");
        assert.containsOnce(target, "div.o_view_nocontent");

        // with comparison active, data and comparisonData (filter on 'this_month' + 'previous_period')
        await toggleMenuItemOption(target, "Date", "2016");
        await toggleMenuItemOption(target, "Date", "August");
        await toggleMenuItem(target, "Date: Previous period");

        verifyContents(
            ["August 2017", 2, "July 2017", 1],
            "with comparison active, data and comparisonData (filter on 'this_month' + 'previous_period')"
        );
        assert.containsNone(target, ".o_cohort_no_data");
        assert.containsNone(target, "div.o_view_nocontent");

        // with comparison active, data, no comparisonData (filter on 'this_year' + 'previous_period')
        await toggleMenuItemOption(target, "Date", "August");

        verifyContents(
            ["2017", 3, "2016"],
            "with comparison active, data, no comparisonData (filter on 'this_year' + 'previous_period')"
        );
        assert.containsOnce(target, ".o_cohort_no_data");
        assert.containsNone(target, "div.o_view_nocontent");

        // with comparison active, no data, comparisonData (filter on 'Q4' + 'previous_period')
        await toggleMenuItemOption(target, "Date", "Q4");

        verifyContents(
            ["Q4 2017", "Q3 2017", 3],
            "with comparison active, no data, comparisonData (filter on 'Q4' + 'previous_period')"
        );
        assert.containsOnce(target, ".o_cohort_no_data");
        assert.containsNone(target, "div.o_view_nocontent");

        // with comparison active, no data, no comparisonData (filter on 'last_year' + 'previous_period')
        await toggleMenuItemOption(target, "Date", "2016");
        await toggleMenuItemOption(target, "Date", "2017");

        verifyContents(
            ["Q4 2016", "Q3 2016"],
            "with comparison active, no data, no comparisonData (filter on 'last_year' + 'previous_period')"
        );
        assert.containsN(target, ".o_cohort_no_data", 2);
        assert.containsOnce(target, "div.o_view_nocontent");
    });

    QUnit.test("verify context", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: '<cohort string="Subscription" date_start="start" date_stop="stop" />',
            mockRPC: function (route, args) {
                if (args.method === "get_cohort_data") {
                    assert.ok(args.kwargs.context);
                }
            },
        });
    });

    QUnit.test("empty cohort view with action helper", async function (assert) {
        serverData.views = {
            "subscription,false,cohort": `<cohort date_start="start" date_stop="stop"/>`,
            "subscription,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>
            `,
        };
        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            context: { search_default_small_than_0: true },
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
        });

        assert.containsOnce(target, ".o_view_nocontent .abc");
        assert.containsNone(target, "table");

        await removeFacet(target);

        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");
    });

    QUnit.test("empty cohort view with sample data", async function (assert) {
        serverData.views = {
            "subscription,false,cohort": `<cohort date_start="start" date_stop="stop"/>`,
            "subscription,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>
            `,
        };

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            context: { search_default_small_than_0: true },
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
            useSampleModel: true,
        });

        assert.hasClass(target.querySelector(".o_cohort_view .o_content"), "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent .abc");

        await removeFacet(target);

        assert.doesNotHaveClass(
            target.querySelector(".o_cohort_view .o_content"),
            "o_view_sample_data"
        );
        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");
    });

    QUnit.test("non empty cohort view with sample data", async function (assert) {
        serverData.views = {
            "subscription,false,cohort": `<cohort date_start="start" date_stop="stop"/>`,
            "subscription,false,search": `
                <search>
                    <filter name="small_than_0" string="Small Than 0" domain="[('id', '&lt;', 0)]"/>
                </search>
            `,
        };

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            noContentHelp: markup('<p class="abc">click to add a foo</p>'),
            config: {
                views: [[false, "search"]],
            },
            useSampleModel: true,
        });

        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsNone(target, ".o_view_nocontent .abc");
        assert.containsOnce(target, "table");

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "Small Than 0");

        assert.doesNotHaveClass(target, "o_view_sample_data");
        assert.containsOnce(target, ".o_view_nocontent .abc");
        assert.containsNone(target, "table");
    });

    QUnit.test(
        "concurrent reloads: add a filter, and directly toggle a measure",
        async function (assert) {
            let def;
            await makeView({
                type: "cohort",
                resModel: "subscription",
                serverData,
                arch: `<cohort date_start="start" date_stop="stop"/>`,
                searchViewArch: `
                    <search>
                        <filter name="my_filter" string="My Filter" domain="[('id', '&lt;', 2)]"/>
                    </search>`,
                mockRPC: function (route, args) {
                    if (args.method === "get_cohort_data") {
                        return Promise.resolve(def);
                    }
                },
            });

            assert.containsN(target, ".o_cohort_row_clickable", 5);
            assert.equal(
                target.querySelector(".table thead th:nth-child(2)").textContent,
                "Count",
                'active measure should be "Count"'
            );

            // Set a domain (this reload is delayed)
            def = makeDeferred();
            await toggleSearchBarMenu(target);
            await toggleMenuItem(target, "My Filter");

            assert.containsN(target, ".o_cohort_row_clickable", 5);

            // Toggle a measure
            await toggleMenu(target, "Measures");
            await toggleMenuItem(target, "Recurring Price");

            assert.containsN(target, ".o_cohort_row_clickable", 5);

            def.resolve();
            await nextTick();

            assert.containsOnce(target, ".o_cohort_row_clickable");
            assert.equal(
                target.querySelector(".table thead th:nth-child(2)").textContent,
                "Recurring Price",
                'active measure should be "Recurring Price"'
            );
        }
    );

    QUnit.test('cohort view with attribute disable_linking="1"', async function (assert) {
        serviceRegistry.add(
            "action",
            {
                start() {
                    return {
                        doAction() {
                            assert.ok(false, "Should not perform a do_action");
                        },
                    };
                },
            },
            { force: true }
        );

        await makeView({
            type: "cohort",
            resModel: "subscription",
            serverData,
            arch: `<cohort date_start="start" date_stop="stop" disable_linking="1"/>`,
        });
        assert.containsOnce(target, ".table", "should have a table");
        await click(target.querySelector("td.o_cohort_value")); // should not trigger a do_action
    });
});
