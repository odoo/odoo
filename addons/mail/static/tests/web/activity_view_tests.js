/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { serverDateToLocalDateShortFormat } from "@mail/utils/common/format";
import { serializeDate } from "@web/core/l10n/dates";
import {
    click,
    contains,
} from "@web/../tests/utils";
import { getFixture } from "@web/../tests/helpers/utils";

const { DateTime } = luxon;

let activityTypes;
function selectorActivityCell(recordName, type) {
    if (!['Prototype 1', 'Prototype 2'].includes(recordName)) {
        throw new Error(`ValueError: Invalid record name ${recordName}`);
    }
    const colIdx = activityTypes.filter((activityType) => activityType.name === type)[0].colIdx;
    const lineIdx = (recordName === 'Prototype 2') ? 1 : 2;
    return `tr:nth-child(${lineIdx}) > td:nth-child(${colIdx + 1})`;
}

QUnit.module("activity", (hooks) => {

let openView;
let previousWeek, yesterday, today, nextWeek;
let pyEnv;
let todoActivityType, callActivityType, meetingActivityType, uploadActivityType;
let target;
let userMarc, userPeter, userJean;
let userInfo;
let visibleAttachmentIds, invisibleAttachmentIds;
hooks.beforeEach(async () => {
    pyEnv = await startServer();
    const projectId1 = pyEnv["res.partner"].create({ name: "Prototype 1", has_visible_activities: true });
    const projectId2 = pyEnv["res.partner"].create({ name: "Prototype 2", has_visible_activities: true });
    userInfo = ["Marc", "Peter", "Jean"].map((name) => ({
        id: pyEnv["res.users"].create({ "name": name }),
        name: name,
    }));
    [userMarc, userPeter, userJean] = userInfo.map((info) => info.id);
    activityTypes = [{ name: 'to do' }, { name: 'call' }, { name: 'meeting' }, { name: 'upload' }];
    [todoActivityType, callActivityType, meetingActivityType, uploadActivityType] = activityTypes.map(
        (activityTypeDef) => {
            activityTypeDef.type = pyEnv["mail.activity.type"].create({ name: activityTypeDef.name, display_done: true });
            return activityTypeDef.type;
        });
    previousWeek = serializeDate(DateTime.now().plus({ days: -7 }));
    yesterday = serializeDate(DateTime.now().plus({ days: -1 }));
    today = serializeDate(DateTime.now());
    nextWeek = serializeDate(DateTime.now().plus({ days: 7 }));
    const activities_vals = [];
    const mailMessage_vals = [];
    visibleAttachmentIds = [];
    invisibleAttachmentIds = [];
    // Create data to have an activity view of 2 records by 3 activity type.
    // State of the activity cells computed as a combination of the activities of the cell are written in comment.
    const activityDef = [
        // line 1
        [projectId2, todoActivityType, "Prove of concept", previousWeek, "done", userJean],
        [projectId2, todoActivityType, "Write specification", previousWeek, "overdue", userJean],
        //                                                                                 done + overdue -> overdue
        [projectId2, uploadActivityType, "Upload specification", today, "today", userJean], // today -> today
        [projectId2, callActivityType, "Call with Marc", previousWeek, "done", userJean], // done -> done
        [projectId2, meetingActivityType, "Meeting with Marc", previousWeek, "done", userJean], // done -> done
        // line 2
        [projectId1, todoActivityType, "Write specification", previousWeek, "done", userMarc],
        [projectId1, todoActivityType, "Implementation", today, "today", userPeter],
        [projectId1, todoActivityType, "Write tests", nextWeek, "planned", userJean], // done + today + planned -> today
        [projectId1, uploadActivityType, "Upload specification", previousWeek, "done", userMarc],
        [projectId1, uploadActivityType, "Upload mockups", yesterday, "done", userMarc], // 2 done -> done
        [projectId1, callActivityType, "Call with Peter", previousWeek, "done", userMarc], // done -> done
        [projectId1, meetingActivityType, "Meeting with Peter to discuss specification", previousWeek, "done", userMarc],
        [projectId1, meetingActivityType, "Meeting with Peter for demo", nextWeek, "planned", userMarc],
        //                                                                                  done + planned -> planned
    ];
    for (const [recordId, activityType, summary, date, state, userId] of activityDef) {
        if (state !== 'done') {
            activities_vals.push({
                activity_type_id: activityType,
                date_deadline: date,
                res_id: recordId,
                res_model: "res.partner",
                summary: summary,
                state: state,
                user_id: userId,
            });
        } else {
            let attachmentId = null;
            if (activityType === uploadActivityType) {
                attachmentId = pyEnv["ir.attachment"].create({
                    create_date: date,
                    name: "test.txt",
                    mimetype: "text/plain",
                });
                if (date === yesterday) {
                    visibleAttachmentIds.push(attachmentId);
                } else {
                    invisibleAttachmentIds.push(attachmentId);
                }
            }
            mailMessage_vals.push({
                attachment_ids: attachmentId ? [attachmentId] : [],
                author_id: userId,
                body: '',
                date: date,
                mail_activity_type_id: activityType,
                model: "res.partner",
                res_id: recordId,
                subject: summary,
            });
        }
    }
    pyEnv["mail.activity"].create(activities_vals);
    pyEnv["mail.message"].create(mailMessage_vals);
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
    target = getFixture();
    openView = (await start({ serverData: { views } })).openView;
    await openView({
        res_model: "res.partner",
        views: [[false, "activity"]],
    });
    document.querySelectorAll('.o_activity_view th').forEach((elem, idx) => {
        const text = elem.textContent;
        for (const activityType of activityTypes) {
            if (text.includes(activityType.name)) {
                activityType.colIdx = idx;
            }
        }
    });
});

QUnit.test("Activity view rendering", async (assert) => {
    // Helper functions to simplify assertions
    const stateToClass = { planned: 'bg-success', overdue: 'bg-danger', today: 'bg-warning' };

    function containsProgressBar(activityTypeName, state, count = 1) {
        return contains(`.progress-bar.${stateToClass[state]}`, {
            parent: ['th.o_activity_type_cell', { text: activityTypeName }], count: count
        });
    }

    async function toggleFilterProgressBar(activityTypeName, state, activateFilter) {
        await click(`.progress-bar.${stateToClass[state]}`,
            { parent: ['th.o_activity_type_cell', { text: activityTypeName }] });
        await contains(`.progress-bar.${stateToClass[state]}.progress-bar-animated`, {
            count: (activateFilter ? 1 : 0),
        });
    }

    function containsHeaderCounter(activityTypeName, count = 1) {
        return contains('.o_animated_number', {
            parent: ['th.o_activity_type_cell', { text: activityTypeName }],
            count: count
        });
    }

    function containsHeaderOngoingActivityCounter(activityTypeName, expectedCounterValue, count = 1) {
        return contains('.o_animated_number', {
            parent: ['th.o_activity_type_cell', { text: activityTypeName }],
            text: expectedCounterValue.toString(),
            count: count,
        });
    }

    function containsHeaderTotalActivityCounter(activityTypeName, expectedCounterValue, count = 1) {
        return contains('.o_column_progress_aggregated_on', {
            parent: ['th.o_activity_type_cell', { text: activityTypeName }],
            textContent: `${expectedCounterValue}`,
            count: count,
        });
    }

    function selAvatar(recordName, type, userId) {
        return `${selectorActivityCell(recordName, type)} .o-mail-Avatar img[data-src='/web/image/res.users/${userId}/avatar_128']`;
    }

    function selCellCounter(recordName, type) {
        return `${selectorActivityCell(recordName, type)} .o-mail-ActivityCell-counter`;
    }

    assert.equal(visibleAttachmentIds.length, 1);
    assert.equal(invisibleAttachmentIds.length, 1);
    for (const todoDisplayDone of [true, false]) {
        pyEnv["mail.activity.type"].write([todoActivityType], {
            display_done: todoDisplayDone,
        });
        await openView({
            res_model: "res.partner",
            views: [[false, "activity"]],
        });

        await contains(".o_activity_view.o_view_controller");
        // Check cells status
        await contains(".o_activity_summary_cell.done", { count: 4 });
        await contains(".o_activity_summary_cell.today", { count: 2 });
        await contains(".o_activity_summary_cell.planned");
        await contains(".o_activity_summary_cell.overdue");
        // Check attachments
        await contains(`a[href*='/web/content/${visibleAttachmentIds[0]}?download=true']`);
        await contains(`a[href*='/web/content/${invisibleAttachmentIds[0]}?download=true']`, { count: 0 });
        // Check cells counters
        if (todoDisplayDone) {
            await contains(selCellCounter('Prototype 1', 'to do'), { text: '2 / 3' });
        } else {
            await contains(selCellCounter('Prototype 1', 'to do'), { text: '2' });
            await contains(selCellCounter('Prototype 1', 'to do'), { text: '/', count: 0 });
        }
        await contains(selCellCounter('Prototype 1', 'upload'), { text: '2' });
        await contains(selCellCounter('Prototype 1', 'meeting'), { text: '1 / 2' });
        if (todoDisplayDone) {
            await contains(selCellCounter('Prototype 2', 'to do'), { text: '1 / 2' });
        } else {
            await contains(selCellCounter('Prototype 2', 'to do'), { text: '1', count: 0 });
            await contains(selCellCounter('Prototype 2', 'to do'), { text: '/', count: 0 });
        }
        // Check cells avatars
        for (const [recordName, activityType, users] of [
            ['Prototype 1', 'to do', [userPeter, userJean]],
            ['Prototype 1', 'upload', []],
            ['Prototype 1', 'call', []],
            ['Prototype 1', 'meeting', [userMarc]],
            ['Prototype 2', 'to do', [userJean]],
            ['Prototype 2', 'upload', [userJean]],
            ['Prototype 2', 'call', []],
            ['Prototype 2', 'meeting', []],
        ]) {
            for (const user of users) {
                await contains(selAvatar(recordName, activityType, user));
            }
            for (const user of [userJean, userMarc, userPeter]) {
                if (!users.includes(user)) {
                    await contains(selAvatar(recordName, activityType, user), { count: 0 });
                }
            }
        }
        // Header: Check progress bar
        await containsProgressBar('to do', 'planned');
        await containsProgressBar('to do', 'overdue');
        await containsProgressBar('to do', 'today');
        await containsProgressBar('call', 'planned', 0);
        await containsProgressBar('call', 'overdue', 0);
        await containsProgressBar('call', 'today', 0);
        await containsProgressBar('meeting', 'planned');
        await containsProgressBar('meeting', 'overdue', 0);
        await containsProgressBar('meeting', 'today', 0);
        await containsProgressBar('upload', 'planned', 0);
        await containsProgressBar('upload', 'overdue', 0);
        await containsProgressBar('upload', 'today');
        // Header: Check counters
        await containsHeaderOngoingActivityCounter('to do', 3);
        if (todoDisplayDone) {
            await containsHeaderTotalActivityCounter('to do', 5);
        } else {
            await containsHeaderTotalActivityCounter('to do', 5, 0);
        }
        await containsHeaderCounter('call', 0);
        await containsHeaderOngoingActivityCounter('meeting', 1);
        await containsHeaderTotalActivityCounter('meeting', 3);
        await containsHeaderOngoingActivityCounter('upload', 1);
        await containsHeaderTotalActivityCounter('upload', 3);
        // Filter "to do" planned -> the cell "done + today + planned -> today" is kept as it contains a planned activity
        await toggleFilterProgressBar('to do', 'planned', true);
        await contains(".o_activity_summary_cell.today", { count: 2 });
        await contains(".o_activity_summary_cell.planned");
        await contains(".o_activity_summary_cell.overdue", { count: 0 });
        await contains(".o_activity_summary_cell.done", { count: 4 });
        await containsHeaderOngoingActivityCounter('to do', 1);
        if (todoDisplayDone) {
            await containsHeaderTotalActivityCounter('to do', 5);
        } else {
            await containsHeaderTotalActivityCounter('to do', 5, 0);
        }
        await toggleFilterProgressBar('to do', 'planned', false);
        // Filter "to do" overdue -> the cell "done + today + planned -> today" is not kept because no overdue activity
        await toggleFilterProgressBar('to do', 'overdue', true);
        await contains(".o_activity_summary_cell.today"); // today of "upload" still visible
        await contains(".o_activity_summary_cell.planned");
        await contains(".o_activity_summary_cell.overdue");
        await contains(".o_activity_summary_cell.done", { count: 4 });
        await containsHeaderOngoingActivityCounter('to do', 1);
        if (todoDisplayDone) {
            await containsHeaderTotalActivityCounter('to do', 5);
        } else {
            await containsHeaderTotalActivityCounter('to do', 5, 0);
        }
        await toggleFilterProgressBar('to do', 'overdue', false);
        // filter "meeting" planned -> the cell "done" of record 2 is hidden
        await toggleFilterProgressBar('meeting', 'planned', true);
        await contains(".o_activity_summary_cell.today", { count: 2 });
        await contains(".o_activity_summary_cell.planned");
        await contains(".o_activity_summary_cell.overdue");
        await contains(".o_activity_summary_cell.done", { count: 3 });
        await containsHeaderOngoingActivityCounter('meeting', 1);
        await containsHeaderTotalActivityCounter('meeting', 3);
        await toggleFilterProgressBar('meeting', 'planned', false);
        // filter upload -> cell "done" are hidden and the attachment related as well
        await toggleFilterProgressBar('upload', 'today', true);
        await contains(`a[href*='/web/content/${visibleAttachmentIds[0]}?download=true']`, { count: 0 });
        await toggleFilterProgressBar('upload', 'today', false);
    }
    // Test that completed activities are hidden when display_done is false
    const allActivityType = [todoActivityType, callActivityType, meetingActivityType, uploadActivityType];
    for (const [activityType, nDone] of [
        [todoActivityType, 0], [callActivityType, 2], [meetingActivityType, 1], [uploadActivityType, 1]]) {
        pyEnv["mail.activity.type"].write(allActivityType, { display_done: false });
        pyEnv["mail.activity.type"].write([activityType], { display_done: true });
        await openView({
            res_model: "res.partner",
            views: [[false, "activity"]],
        });
        await contains(".o_activity_summary_cell.done", { count: nDone });
    }
    pyEnv["mail.activity.type"].write(allActivityType, { display_done: false });
    await openView({
        res_model: "res.partner",
        views: [[false, "activity"]],
    });
    await contains(".o_activity_summary_cell.done", { count: 0 });
});

QUnit.test("Activity details popover rendering", async (assert) => {
    await openView({
        res_model: "res.partner",
        views: [[false, "activity"]],
    });
    for (const [recordName, activityType, nByStatus, ongoingActivityDefs, completedActivityDefs] of [
        ['Prototype 2', 'to do', { done: 1, overdue: 1 },
            [{ user: 'Jean', date: previousWeek, contains: ['7 days overdue', 'Write specification'] }],
            [{ user: 'Jean', date: previousWeek, contains: ['Prove of concept'] }]],
        ['Prototype 2', 'upload', { today: 1 },
            [{ user: 'Jean', date: today, contains: ['Upload specification'] }],
            []],
        ['Prototype 2', 'call', { done: 1 },
            [],
            [{ user: 'Jean', date: previousWeek, contains: ['Call with Marc'] }]],
        ['Prototype 1', 'to do', { done: 1, planned: 1, today: 1 },
            [
                { user: 'Peter', date: today, contains: ['Implementation'] },
                { user: 'Jean', date: today, contains: ['Write tests', 'Due in 7 days'] }
            ],
            [{ user: 'Marc', date: previousWeek, contains: ['Write specification'] }]],
        ['Prototype 1', 'upload', { done: 2 },
            [],
            [{ user: 'Marc', date: yesterday, nAttachment: 1 }, { user: 'Marc', date: previousWeek, nAttachment: 1 }]],
        ['Prototype 1', 'meeting', { done: 1, planned: 1 },
            [{ user: 'Marc', date: nextWeek, contains: ['Meeting with Peter for demo', 'Due in 7 days'] }],
            [{ user: 'Marc', date: previousWeek, contains: ['Meeting with Peter to discuss specification'] }]],
    ]) {
        await click(`${selectorActivityCell(recordName, activityType)} > div`);
        await contains('.o-mail-ActivityListPopover');
        // Status group
        for (const status of ['planned', 'today', 'overdue', 'done']) {
            if (status in nByStatus) {
                await contains(`.o-mail-ActivityListPopover-${status}`);
                await contains(`.o-mail-ActivityListPopover-${status} .rounded-pill`,
                    { text: nByStatus[status].toString() });
            } else {
                await contains(`.o-mail-ActivityListPopover-${status}`, { count: 0 });
            }
        }
        // N completed and ongoing activities
        const nOngoing = (nByStatus?.planned ?? 0) + (nByStatus?.today ?? 0) + (nByStatus?.overdue ?? 0);
        const nCompleted = nByStatus?.done ?? 0;
        await contains('.o-mail-ActivityListPopover .o-mail-ActivityListPopoverItem', { count: nOngoing });
        await contains('.o-mail-ActivityListPopover .o-mail-CompletedActivity', { count: nCompleted });
        // Ongoing activities
        const ongoingActivityDoms =
            target.querySelectorAll('.o-mail-ActivityListPopover .o-mail-ActivityListPopoverItem');
        for (let i = 0; i < ongoingActivityDefs.length; i++) {
            const activity = ongoingActivityDefs[i];
            const activityDom = ongoingActivityDoms[i];
            const baseMsg = `#${i + 1} activity`;
            assert.ok(activityDom.innerHTML.includes(activity.user), `${baseMsg} assigned to ${activity.user}`);
            if (activity.contains) {
                for (const mustContain of activity.contains) {
                    assert.ok(activityDom.innerHTML.includes(mustContain), `${baseMsg} must include ${mustContain}`);
                }
            }
        }
        // Completed activities
        const completedActivityDoms = target.querySelectorAll('.o-mail-ActivityListPopover .o-mail-CompletedActivity');
        for (let i = 0; i < completedActivityDefs.length; i++) {
            const activity = completedActivityDefs[i];
            const activityDom = completedActivityDoms[i];
            assert.ok(activityDom.innerHTML.includes(activity.user));
            assert.ok(activityDom.innerHTML.includes(serverDateToLocalDateShortFormat(activity.date)));
            if (activity.nAttachment) {
                await contains('.o-mail-AttachmentList .o-mail-AttachmentCard', { target: activityDom, count: activity.nAttachment });
            }
            const baseMsg = `#${i + 1} activity`;
            if (activity.contains) {
                for (const mustContain of activity.contains) {
                    assert.ok(activityDom.innerHTML.includes(mustContain), `${baseMsg} must include ${mustContain}`);
                }
            }
        }
        // Close it for next iteration
        await click(`${selectorActivityCell(recordName, activityType)} .o-mail-ActivityCell-deadline`);
        await contains('.o-mail-ActivityListPopover', { count: 0 });
    }
});

});
