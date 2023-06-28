/* @odoo-module */

import {
    start,
    startServer,
    click,
} from "@mail/../tests/helpers/test_utils";


QUnit.module("activity");

QUnit.test("Activity view rendering", async (assert) => {
    const pyEnv = await startServer();
    const projectId1 = pyEnv["res.partner"].create({ display_name: "Prototype 1" });
    const projectId2 = pyEnv["res.partner"].create({ display_name: "Prototype 2" });
    const todoActivityType = pyEnv["mail.activity.type"].create({ name: 'to do', keep_done: true });
    const callActivityType = pyEnv["mail.activity.type"].create({ name: 'call', keep_done: true });
    const meetingActivityType = pyEnv["mail.activity.type"].create({ name: 'meeting', keep_done: true });
    const previousWeek = moment().add(-7, "day").format("YYYY-MM-DD");
    const today = moment().format("YYYY-MM-DD");
    const nextWeek = moment().add(7, "day").format("YYYY-MM-DD");
    const activities_vals = [];
    // Create data to have an activity view of 2 records by 3 activity.
    // State of the activity cells computed as a combination of the activities of the cell are written in comment.
    for (const [recordId, activityType, name, date, state] of [
        // record 1
        [projectId1, todoActivityType, "Write specification", previousWeek, "done"],
        [projectId1, todoActivityType, "Implementation", today, "today"],
        [projectId1, todoActivityType, "Write tests", nextWeek, "planned"], // done + today + planned -> today
        [projectId1, callActivityType, "Call with Peter", previousWeek, "done"], // done -> done
        [projectId1, meetingActivityType, "Meet with Peter to discuss specification", previousWeek, "done"],
        [projectId1, meetingActivityType, "Meet with Peter for demo", nextWeek, "planned"], // done + planned -> planned
        // record 2
        [projectId2, todoActivityType, "Prove of concept", previousWeek, "done"],
        [projectId2, todoActivityType, "Write specification", previousWeek, "overdue"], // done + overdue -> overdue
        [projectId2, callActivityType, "Call with Marc", previousWeek, "done"], // done -> done
        [projectId2, meetingActivityType, "Meet with Marc", previousWeek, "done"], // done -> done
    ]) {
        activities_vals.push({
            display_name: name,
            date_deadline: date,
            date_done: state === 'done' ? date : false, // For the test, date_done == date_deadline but not mandatory
            state: state,
            activity_type_id: activityType,
            res_id: recordId,
            res_model: "res.partner",
        });
    }
    pyEnv["mail.activity"].create(activities_vals);
    const views = {
        "res.partner,false,activity": `
            <activity string="Partners">
                <templates>
                    <div t-name="activity-box" class="d-flex w-100">
                         <field name="name" string="Event Name" class="w-100 text-truncate"/>
                    </div>
                </templates>
            </activity>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.partner",
        res_id: projectId1,
        views: [[false, "activity"]],
    });

    const stateToClass = { planned: 'bg-success', overdue: 'bg-danger', today: 'bg-warning' };
    function selProgressBar(activityTypeName, state) {
        return `th.o_activity_type_cell:contains('${activityTypeName}') .progress-bar.${stateToClass[state]}`;
    }

    function selHeaderCounter(activityTypeName) {
        return `th.o_activity_type_cell:contains('${activityTypeName}') .o_animated_number`;
    }

    function selHeaderOngoingActivityCounter(activityTypeName, expectedCount) {
        return `${selHeaderCounter(activityTypeName)}:contains('${expectedCount}')`;
    }

    function selHeaderTotalActivityCounter(activityTypeName, expectedCount) {
        return `${selHeaderCounter(activityTypeName)} ~ div:contains('${expectedCount}')`;
    }

    assert.containsOnce($, ".o_activity_view.o_view_controller");
    // Check cells status
    assert.containsN($, ".o_activity_summary_cell.done", 3);
    assert.containsOnce($, ".o_activity_summary_cell.today");
    assert.containsOnce($, ".o_activity_summary_cell.planned");
    assert.containsOnce($, ".o_activity_summary_cell.overdue");
    // Header: Check progress bar
    assert.containsOnce($, selProgressBar('to do', 'planned'));
    assert.containsOnce($, selProgressBar('to do', 'overdue'));
    assert.containsOnce($, selProgressBar('to do', 'today'));
    assert.containsNone($, selProgressBar('call', 'planned'));
    assert.containsNone($, selProgressBar('call', 'overdue'));
    assert.containsNone($, selProgressBar('call', 'today'));
    assert.containsOnce($, selProgressBar('meeting', 'planned'));
    assert.containsNone($, selProgressBar('meeting', 'overdue'));
    assert.containsNone($, selProgressBar('meeting', 'today'));
    // Header: Check counters
    assert.containsOnce($, selHeaderOngoingActivityCounter('to do', 3));
    assert.containsOnce($, selHeaderTotalActivityCounter('to do', 5));
    assert.containsNone($, selHeaderCounter('call'));
    assert.containsOnce($, selHeaderOngoingActivityCounter('meeting', 1));
    assert.containsOnce($, selHeaderTotalActivityCounter('meeting', 3));
    // Filter "to do" planned -> the cell "done + today + planned -> today" is kept as it contains a planned activity
    await click(selProgressBar('to do', 'planned'));
    assert.containsOnce($, ".o_activity_summary_cell.today");
    assert.containsOnce($, ".o_activity_summary_cell.planned");
    assert.containsNone($, ".o_activity_summary_cell.overdue");
    assert.containsN($, ".o_activity_summary_cell.done", 3);
    assert.containsOnce($, selHeaderOngoingActivityCounter('to do', 1));
    assert.containsOnce($, selHeaderTotalActivityCounter('to do', 5));
    await click(selProgressBar('to do', 'planned'));
    // Filter "to do" overdue -> the cell "done + today + planned -> today" is not kept because no overdue activity
    await click(selProgressBar('to do', 'overdue'));
    assert.containsNone($, ".o_activity_summary_cell.today");
    assert.containsOnce($, ".o_activity_summary_cell.planned");
    assert.containsOnce($, ".o_activity_summary_cell.overdue");
    assert.containsN($, ".o_activity_summary_cell.done", 3);
    assert.containsOnce($, selHeaderOngoingActivityCounter('to do', 1));
    assert.containsOnce($, selHeaderTotalActivityCounter('to do', 5));
    await click(selProgressBar('to do', 'overdue'));
    // filter "meeting" planned -> the cell "done" of record 2 is hidden
    await click(selProgressBar('meeting', 'planned'));
    assert.containsOnce($, ".o_activity_summary_cell.today");
    assert.containsOnce($, ".o_activity_summary_cell.planned");
    assert.containsOnce($, ".o_activity_summary_cell.overdue");
    assert.containsN($, ".o_activity_summary_cell.done", 2);
    assert.containsOnce($, selHeaderOngoingActivityCounter('meeting', 1));
    assert.containsOnce($, selHeaderTotalActivityCounter('meeting', 3));
    await click(selProgressBar('meeting', 'planned'));
});
