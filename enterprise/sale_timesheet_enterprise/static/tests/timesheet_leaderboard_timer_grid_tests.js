import { click, getFixture, getNodesTextContent, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { start } from "@mail/../tests/helpers/test_utils";

import { setupTestEnv } from "@hr_timesheet/../tests/hr_timesheet_common_tests";

import { TimesheetGridSetupHelper } from "@timesheet_grid/../tests/helpers";

import { browser } from "@web/core/browser/browser";

let target, timesheetGridSetup, rankingData, leaderboard;

async function initAndOpenView(showIndicators = true, showLeaderboard = true) {
    const { openView } = await start({
        serverData: {
            views: {
                "analytic.line,false,grid":
                    `<grid js_class="timer_timesheet_grid">
                        <field name="date" type="col">
                            <range name="week" string="Week" span="week" step="day"/>
                            <range name="month" string="Month" span="month" step="day"/>
                        </field>
                        <field name="unit_amount" type="measure" widget="timesheet_uom"/>
                    </grid>`,
                "analytic.line,false,search": "<search><field name='project_id'/></search>",
            },
        },
        async mockRPC(route, args) {
            if (args.method === "get_timesheet_ranking_data") {
                return rankingData[args.args[0]];
            } else if (args.method === "read" && args.args[1].length === 2 && args.args[1][0] === "timesheet_show_rates" && args.args[1][1] === "timesheet_show_leaderboard") {
                return [{ timesheet_show_rates: showIndicators, timesheet_show_leaderboard: showLeaderboard }];
            }
            return timesheetGridSetup.mockTimesheetTimerGridRPC(route, args);
        },
    });
    patchDate(2002, 3, 25, 0, 0, 0);
    await openView({
        res_model: "analytic.line",
        views: [[false, "grid"]],
        context: { group_by: ["project_id", "task_id"] },
    });
    leaderboard = target.querySelector(".o_timesheet_leaderboard");
}

QUnit.module("Timesheet Leaderboard Grid View", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        timesheetGridSetup = new TimesheetGridSetupHelper(true);
        await timesheetGridSetup.setupTimesheetGrid();
        setupTestEnv();

        rankingData = {
            "2002-02-01T00:00:00.000+01:00": {
                "leaderboard": [...Array(11).keys()].map((id) => {
                    return {
                        "id": id,
                        "name": `Test ${id}`,
                        "billable_time_target": 100.0,
                        "billable_time": 150.0,
                        "total_time": 150.0,
                        "total_valid_time": 150.0,
                        "billing_rate": 150.0,
                    }
                }),
                "employee_id": 1,
                "total_time_target": 144.0,
            },
            "2002-03-01T00:00:00.000+01:00": {
                "leaderboard": [
                    {
                        "id": 6,
                        "name": "User 5",
                        "billable_time_target": 100.0,
                        "billable_time": 148.0,
                        "total_time": 148.0,
                        "total_valid_time": 148.0,
                        "billing_rate": 148.0,
                    },
                ],
                "employee_id": 1,
                "total_time_target": 144.0,
            },
            "2002-04-01T00:00:00.000+01:00": {
                "leaderboard": [
                    {
                        "id": 1,
                        "name": "Administrator",
                        "billable_time_target": 25.0,
                        "billable_time": 20.0,
                        "total_time": 20.0, // 5th in total time leaderboard
                        "total_valid_time": 20.0,
                        "billing_rate": 100.0, // 1st in billing rate leaderboard
                    },
                    {
                        "id": 2,
                        "name": "User 1",
                        "billable_time_target": 50.0,
                        "billable_time": 40.0,
                        "total_time": 40.0, // 4th in total time leaderboard
                        "total_valid_time": 40.0,
                        "billing_rate": 80.0, // 2nd in billing rate leaderboard
                    },
                    {
                        "id": 3,
                        "name": "User 2",
                        "billable_time_target": 100.0,
                        "billable_time": 60.0,
                        "total_time": 60.0, // 3rd in total time leaderboard
                        "total_valid_time": 60.0,
                        "billing_rate": 60.0, // 3rd in billing rate leaderboard
                    },
                    {
                        "id": 4,
                        "name": "User 3",
                        "billable_time_target": 200.0,
                        "billable_time": 80.0,
                        "total_time": 80.0, // 2nd in total time leaderboard
                        "total_valid_time": 80.0,
                        "billing_rate": 40.0, // 4th in billing rate leaderboard
                    },
                    {
                        "id": 5,
                        "name": "User 4",
                        "billable_time_target": 500.0,
                        "billable_time": 100.0,
                        "total_time": 100.0, // 1st in total time leaderboard
                        "total_valid_time": 100.0,
                        "billing_rate": 20.0, // 5th in billing rate leaderboard
                    }
                ],
                "employee_id": 1,
                "total_time_target": 144.0,
            },
            "2002-05-01T00:00:00.000+01:00": {
                "leaderboard": [
                    {
                        "id": 7,
                        "name": "User 6",
                        "billable_time_target": 100.0,
                        "billable_time": 128.0,
                        "total_time": 128.0,
                        "total_valid_time": 128.0,
                        "billing_rate": 128.0,
                    },
                ],
                "employee_id": 1,
                "total_time_target": 120.0,
            },
        }
    });

    QUnit.test("Check that leaderboard is displayed if user's company has the feature on.", async function (assert) {
        await initAndOpenView();
        assert.containsOnce(target, ".o_timesheet_leaderboard");
        assert.containsOnce(leaderboard, ".o_timesheet_leaderboard_confetti"); // confettis are displayed (user 1st)
        assert.hasClass(leaderboard.querySelector("span").children[2], "text-success"); // billing rate in green
        assert.hasClass(leaderboard.querySelector("span").children[5], 'text-danger'); // total time in red
        assert.containsNone(leaderboard, "span:contains('···')"); // '···' not displayed (user's position <= 3)
    });

    QUnit.test("Check that leaderboard is not displayed if user's company doesn't have the features on.", async function (assert) {
        await initAndOpenView(false, false);
        assert.containsNone(target, ".o_timesheet_leaderboard");
    });

    QUnit.test("Check that billing and total time indicators are displayed if user's company has the feature on.", async function (assert) {
        await initAndOpenView(true, false); // init view without the leaderboard feature
        assert.containsOnce(leaderboard, "span > span:contains('Billing:')");
        assert.containsOnce(leaderboard, "span > span:contains('Total:')");
    });

    QUnit.test("Check that confettis are not displayed if current employee is not first in the leaderboard (or not in the leaderboard).", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0]; // current employee
        employee["billing_rate"] = 20.0; // employee is not 1st anymore
        await initAndOpenView();
        assert.containsNone(leaderboard, ".o_timesheet_leaderboard_confetti");
        await click(target, ".o_view_scale_selector > button");
        await click(target, ".o_scale_button_month");
        await click(target, "span[aria-label='Previous']");
        assert.containsNone(leaderboard, ".o_timesheet_leaderboard_confetti");
    });

    QUnit.test("Check that the billing rate is displayed in red if < than 100.", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0]; // current employee
        employee["billing_rate"] = 70.0;
        await initAndOpenView();
        assert.hasClass(leaderboard.querySelector("span").children[2], 'text-danger');
    });

    QUnit.test("Check that the total time is displayed without styling if the total valid time >= total time target.", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0]; // current employee
        employee["total_valid_time"] = 145.0; // no need to modify the total time at this point
        await initAndOpenView();
        assert.notOk(leaderboard.querySelector("span").children[5].classList.contains("text-danger"));
    });

    QUnit.test("Check that the indicators are replaced by text if current employee's billing rate <= 0 [Leaderboard feature only].", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0];
        employee["billing_rate"] = 0.0; // current employee shouldn't be in the leaderboard anymore
        await initAndOpenView();
        assert.containsOnce(leaderboard, "span:contains('Record timesheets to earn your rank!')");
    });

    QUnit.test("Check that the indicators are replaced by text if current employee's billing rate <= 0 [Billing Rate feature only].", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0];
        employee["billing_rate"] = 0.0; // current employee shouldn't be in the leaderboard anymore
        await initAndOpenView(true, false); // init view without leaderboard
        assert.containsOnce(leaderboard, "span:contains('Record timesheets to determine your billing rate!')");
    });

    QUnit.test("Check that '···' is displayed when current employee's ranking > 3.", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0]; // current employee
        employee["billing_rate"] = 5.0; // now current employee is 5th
        await initAndOpenView();
        assert.containsOnce(leaderboard, "span:contains('···')");
    });

    QUnit.test("Check that employees are sorted accordingly to the ranking criteria.", async function (assert) {
        const storage = new Map();
        patchWithCleanup(browser, {
            localStorage: {
                getItem: (key) => storage.get(key),
                setItem: (key, value) => storage.set(key, value),
            }
        });
        await initAndOpenView();
        await click(leaderboard, "div[role='button']"); // open leaderboard dialog
        const leaderboardModal = target.querySelector(".modal-content");
        const changeTypeButton = leaderboardModal.querySelector(".dropdown-toggle");
        await click(changeTypeButton);
        await click(leaderboardModal.querySelector(".dropdown-menu").children[1]); // set type to total time leaderboard
        assert.strictEqual(storage.get("leaderboardType"), "total_time");
        let ranking = getNodesTextContent(leaderboardModal.querySelectorAll(".o_employee_name"));
        assert.deepEqual(["User 4", "User 3", "User 2", "User 1", "Administrator"], ranking);
        // Retrieving the user's names in DOM's order so we can compare them directly

        await click(changeTypeButton);
        await click(leaderboardModal.querySelector(".dropdown-menu").children[0]); // set type to billing rate leaderboard
        assert.strictEqual(storage.get("leaderboardType"), "billing_rate");
        ranking = getNodesTextContent(leaderboardModal.querySelectorAll(".o_employee_name"));
        assert.deepEqual(["Administrator", "User 1", "User 2", "User 3", "User 4"], ranking);
        // Same as before
    });

    QUnit.test("Check that employee's name is displayed in bold if rank > 3.", async function (assert) {
        const rankingDataApril = rankingData["2002-04-01T00:00:00.000+01:00"];
        const employee = rankingDataApril["leaderboard"][0]; // current employee
        employee["billing_rate"] = 5.0; // now current employee is 5th
        await initAndOpenView();
        await click(leaderboard, "div[role='button']");
        assert.hasClass([...target.querySelectorAll(".o_employee_name")].pop().parentNode, "fw-bolder"); // Administrator is last
    });

    QUnit.test("Check that the month changing buttons work.", async function (assert) {
        await initAndOpenView();
        await click(leaderboard, "div[role='button']");
        const leaderboardModal = target.querySelector(".modal-content");
        const goForward = leaderboardModal.querySelector(".oi-chevron-right").parentNode;

        await click(leaderboardModal.querySelector(".oi-chevron-left").parentNode);
        assert.containsOnce(leaderboardModal, "span:contains('User 5')"); // User 5 is in march leaderboard
        assert.containsOnce(leaderboardModal, "span:contains('March 2002')");
        await click(goForward);
        assert.containsOnce(leaderboardModal, "span:contains('Administrator')"); // Administrator is in current month (april) leaderboard
        assert.containsOnce(leaderboardModal, "span:contains('April 2002')");
        await click(goForward);
        assert.containsOnce(leaderboardModal, "span:contains('User 6')"); // User 6 is in may leaderboard
        assert.containsOnce(leaderboardModal, "span:contains('May 2002')");
        await click(leaderboardModal.querySelector(".oi-chevron-left").parentNode.nextSibling);
        assert.containsOnce(leaderboardModal, "span:contains('Administrator')"); // Administrator is in current month leaderboard
        assert.containsOnce(leaderboardModal, "span:contains('April 2002')");
    });

    QUnit.test("Check that the 'Show more' and 'Show less' buttons work.", async function (assert) {
        await initAndOpenView();
        await click(leaderboard, "div[role='button']");
        const leaderboardModal = target.querySelector(".modal-content");
        const goBack = leaderboardModal.querySelector(".modal-body .oi-chevron-left").parentNode;
        await click(goBack);
        await click(goBack);

        assert.containsNone(leaderboardModal, ".modal-body td:contains('Test 10')");
        await click(target.querySelector(".o_leaderboard_modal_table ~ span"));
        assert.containsOnce(leaderboardModal, ".modal-body td:contains('Test 10')")
        await click(target.querySelector(".o_leaderboard_modal_table ~ span"));
        assert.containsNone(leaderboardModal, ".modal-body td:contains('Test 10')");
    });
});
