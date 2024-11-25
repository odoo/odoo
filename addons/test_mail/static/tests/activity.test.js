import { ActivityController } from "@mail/views/web/activity/activity_controller";
import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import {
    assertSteps,
    click,
    contains,
    insertText,
    openFormView,
    openView,
    registerArchs,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import {
    DEFAULT_MAIL_SEARCH_ID,
    DEFAULT_MAIL_VIEW_ID,
} from "@mail/../tests/mock_server/mock_models/constants";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate, animationFrame } from "@odoo/hoot-mock";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { MailTestActivity } from "@test_mail/../tests/mock_server/models/mail_test_activity";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { Domain } from "@web/core/domain";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { DynamicList } from "@web/model/relational_model/dynamic_list"
import { deepEqual, omit } from "@web/core/utils/objects";
import { getOrigin } from "@web/core/utils/urls";
import { serializeDate, formatDate } from "@web/core/l10n/dates";
import { onRpc, patchWithCleanup, serverState, contains as webContains } from "@web/../tests/web_test_helpers";
import { keyDown, waitFor } from "@odoo/hoot-dom";
import { MailActivitySchedule } from "@mail/../tests/mock_server/mock_models/mail_activity_schedule";

const { DateTime } = luxon;

let pyEnv;
const archs = {
    "mail.test.activity,false,activity": `
        <activity string="MailTestActivity">
            <templates>
                <div t-name="activity-box">
                    <field name="name"/>
                </div>
            </templates>
        </activity>
    `,
    "mail.test.activity,1,activity": `
        <activity string="MailTestActivity">
            <div t-name="activity-box">
                <span t-att-title="record.name.value">
                    <field name="name" display="full" class="w-100 text-truncate"/>
                </span>
                <span class="invisible_node" invisible="context.get('invisible', False)">
                    Test invisible
                </span>
            </div>
        </activity>
    `,
};

function patchActivityDomain(load, params) {
    if (params.domain) {
        // Remove domain term used to filter record having "done" activities (not understood by the getRecords mock)
        const domain = new Domain(params.domain);
        const newDomain = Domain.removeDomainLeaves(domain.toList(), [
            "activity_ids.active",
        ]);
        if (!deepEqual(domain.toList(), newDomain.toList())) {
            return load({
                ...params,
                domain: newDomain.toList(),
                context: params.context
                    ? { ...params.context, active_test: false }
                    : { active_test: false },
            });
        }
    }
    return load(params);
}

describe.current.tags("desktop");
defineTestMailModels();
beforeEach(async () => {
    mockDate("2023-4-8 10:00:00", 0);
    patchWithCleanup(DynamicList.prototype, {
        async load(params) {
            return patchActivityDomain(super.load.bind(this), params);
        },
    })
    patchWithCleanup(RelationalModel.prototype, {
        async load(params) {
            return patchActivityDomain(super.load.bind(this), params);
        },
    });
    pyEnv = await startServer();
    const mailTemplateIds = pyEnv["mail.template"].create([
        { name: "Template1" },
        { name: "Template2" },
    ]);
    // reset incompatible setup
    pyEnv["mail.activity.type"].unlink(pyEnv["mail.activity.type"].search([]));
    const mailActivityTypeIds = pyEnv["mail.activity.type"].create([
        { name: "Email", mail_template_ids: mailTemplateIds },
        { name: "Call" },
        { name: "Call for Demo" },
        { name: "To Do" },
    ]);
    const resUsersId1 = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "first partner" }),
    });
    const mailActivityIds = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[0],
            user_id: resUsersId1,
        },
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now()),
            can_write: true,
            state: "today",
            activity_type_id: mailActivityTypeIds[0],
            user_id: resUsersId1,
        },
        {
            res_model: "mail.test.activity",
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now().minus({ days: 2 })),
            can_write: true,
            state: "overdue",
            activity_type_id: mailActivityTypeIds[1],
            user_id: resUsersId1,
        },
    ]);
    pyEnv["mail.test.activity"].create([
        { name: "Meeting Room Furnitures", activity_ids: [mailActivityIds[0]] },
        { name: "Office planning", activity_ids: [mailActivityIds[1], mailActivityIds[2]] },
    ]);
});

test("activity view: simple activity rendering", async () => {
    const mailTestActivityIds = pyEnv["mail.test.activity"].search([]);
    const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);
    const env = await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".o_activity_view_table th", { text: "Email" });
    await contains(".progress-bar[data-tooltip='1 Planned']", {
        parent: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".progress-bar[data-tooltip='1 Today']", {
        parent: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".o_activity_view_table th", {
        text: "Call",
        after: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".progress-bar[data-tooltip='1 Overdue']", {
        parent: [".o_activity_view_table th", { text: "Call" }],
    });
    await contains(".o_activity_view_table th", {
        text: "Call for Demo",
        after: [".o_activity_view_table th", { text: "Call" }],
    });
    await contains(".progress-bar", {
        count: 0,
        parent: [".o_activity_view_table th", { text: "Call for Demo" }],
    });
    await contains(".o_activity_view_table tr:nth-child(1) .o_activity_record", {
        text: "Office planning",
    });
    await contains(".o_activity_view_table tr:nth-child(2) .o_activity_record", {
        text: "Meeting Room Furnitures",
    });
    const today = formatDate(DateTime.now());
    await contains(":nth-child(1 of .o_activity_summary_cell)", {
        text: today,
        parent: [
            "tr",
            {
                contains: [".o_activity_record", { text: "Office planning" }],
            },
        ],
    });
    await contains(".o_activity_empty_cell", {
        count: 2,
        parent: [
            "tr",
            {
                contains: [".o_activity_record", { text: "Office planning" }],
            },
        ],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            step("doAction");
            expect(action).toEqual({
                context: {
                    default_res_id: mailTestActivityIds[1],
                    default_res_model: "mail.test.activity",
                    default_activity_type_id: mailActivityTypeIds[2],
                },
                res_id: false,
                res_model: "mail.activity",
                target: "new",
                type: "ir.actions.act_window",
                view_mode: "form",
                view_type: "form",
                views: [[false, "form"]],
            });
        },
    });
    await click(":nth-child(1 of .o_activity_empty_cell)", {
        parent: [
            "tr",
            {
                contains: [".o_activity_record", { text: "Office planning" }],
            },
        ],
    });
    await assertSteps(["doAction"]);
    await contains(".o_activity_view_table tfoot .o_record_selector");
});

test("activity view: Activity rendering with done activities", async () => {
    const activityTypeUpload = pyEnv["mail.activity.type"].create({
        category: "upload_file",
        name: "Test Upload document",
        keep_done: true,
    });
    pyEnv["mail.activity"].create(
        Object.entries(["done", "done", "done", "done", "planned", "planned", "planned"]).map(
            ([idx, state]) => {
                const userId = pyEnv["res.users"].create({
                    partner_id: pyEnv["res.partner"].create({ name: `Partner ${idx}` }),
                });
                // issue with compute/related, `display_name` is wrong until next write.
                pyEnv["res.users"].write([userId], {});
                return {
                    active: state !== "done",
                    activity_type_id: activityTypeUpload,
                    attachment_ids:
                        state === "done"
                            ? [
                                  pyEnv["ir.attachment"].create({
                                      name: `attachment ${idx}`,
                                      create_date: serializeDate(
                                          DateTime.now().minus({ days: idx })
                                      ),
                                      create_uid: serverState.userId,
                                  }),
                              ]
                            : [],
                    can_write: true,
                    date_deadline: serializeDate(DateTime.now().plus({ days: idx })),
                    date_done:
                        state === "done"
                            ? serializeDate(DateTime.now().minus({ days: idx }))
                            : false,
                    display_name: `Upload folders ${idx}`,
                    state: state,
                    user_id: userId,
                };
            }
        )
    );
    const [meetingRecord, officeRecord] = pyEnv["mail.test.activity"].search([]);
    const uploadDoneActs = pyEnv["mail.activity"].search_read([
        ["activity_type_id", "=", activityTypeUpload],
        ["active", "=", false],
    ]);
    const uploadPlannedActs = pyEnv["mail.activity"].search_read([
        ["activity_type_id", "=", activityTypeUpload],
    ]);
    pyEnv["mail.test.activity"].write([meetingRecord], {
        activity_ids: [
            uploadPlannedActs[0].id,
            uploadPlannedActs[1].id,
            uploadPlannedActs[2].id,
            uploadDoneActs[0].id,
        ],
    });
    pyEnv["mail.test.activity"].write([officeRecord], {
        activity_ids: [uploadDoneActs[1].id, uploadDoneActs[2].id, uploadDoneActs[3].id],
    });
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    const domActivity = document.querySelector(".o_activity_view");
    const domHeaderUpload = domActivity.querySelector("table thead tr:first-child th:nth-child(6)");
    const selRowMeetingCellUpload = "table tbody tr:first-child td:nth-child(6)";
    const domRowMeetingCellUpload = domActivity.querySelector(selRowMeetingCellUpload);
    const selRowOfficeCellUpload = "table tbody tr:nth-child(2) td:nth-child(6)";
    const domRowOfficeCellUpload = domActivity.querySelector(selRowOfficeCellUpload);

    // Headers
    await contains(".o_column_progress .progress-bar:first-child[data-tooltip='3 Planned']", {
        target: domHeaderUpload,
    });
    await contains(".o_animated_number", {
        target: domHeaderUpload,
        text: "3",
    });
    await contains(".o_column_progress_aggregated_on", {
        target: domHeaderUpload,
        text: "7",
    });
    // Cells avatars
    await contains(
        `.o-mail-Avatar img[data-src='/web/image/res.users/${uploadPlannedActs[0].user_id[0]}/avatar_128'`,
        { target: domRowMeetingCellUpload }
    );
    await contains(
        `.o-mail-Avatar img[data-src='/web/image/res.users/${uploadPlannedActs[1].user_id[0]}/avatar_128'`,
        { target: domRowMeetingCellUpload }
    );
    await contains(
        `.o-mail-Avatar img[data-src='/web/image/res.users/${uploadPlannedActs[2].user_id[0]}/avatar_128'`,
        { target: domRowMeetingCellUpload, count: 0 }
    );
    await contains(`.o-mail-Avatar`, { target: domRowOfficeCellUpload, count: 0 }); // all activity are done
    // Cells counters
    await contains(".o-mail-ActivityCell-counter", {
        target: domRowMeetingCellUpload,
        text: "3 / 4",
    });
    await contains(".o-mail-ActivityCell-counter", {
        text: "3",
        target: domRowOfficeCellUpload,
    });
    // Cells dates
    await contains(".o-mail-ActivityCell-deadline", {
        text: formatDate(luxon.DateTime.fromISO(uploadPlannedActs[0].date_deadline)),
        target: domRowMeetingCellUpload,
    });
    await contains(".o-mail-ActivityCell-deadline", {
        text: formatDate(luxon.DateTime.fromISO(uploadDoneActs[1].date_done)),
        target: domRowOfficeCellUpload,
    });
    // Activity list popovers content
    await click(`${selRowMeetingCellUpload} > div`, {
        target: domActivity,
    });
    await contains(".o-mail-ActivityListPopover .badge.text-bg-success", { text: "3" }); // 3 planned
    for (const actIdx of [0, 1, 2]) {
        await contains(".o-mail-ActivityListPopoverItem", {
            text: uploadPlannedActs[actIdx].user_id[1],
        });
    }
    await contains(".o-mail-ActivityListPopoverItem", { text: "Due in 4 days" });
    await contains(".o-mail-ActivityListPopoverItem", { text: "Due in 5 days" });
    await contains(".o-mail-ActivityListPopoverItem", { text: "Due in 6 days" });
    await contains(".o-mail-ActivityListPopover .badge.text-bg-secondary", { text: "1" }); // 1 done
    await contains(".o-mail-ActivityListPopoverItem", { text: uploadDoneActs[0].user_id[1] });
    await contains(".o-mail-ActivityListPopoverItem", {
        text: formatDate(luxon.DateTime.fromISO(uploadDoneActs[0].date_done)),
    });
    await click(`${selRowOfficeCellUpload} > div`, {
        target: domActivity,
    });
    await contains(".o-mail-ActivityListPopover .badge.text-bg-secondary", { text: "3" }); // 3 done
    for (const actIdx of [1, 2, 3]) {
        await contains(".o-mail-ActivityListPopoverItem", {
            text: formatDate(luxon.DateTime.fromISO(uploadDoneActs[actIdx].date_done)),
        });
        await contains(".o-mail-ActivityListPopoverItem", {
            text: uploadDoneActs[actIdx].user_id[1],
        });
    }
});

test("activity view: a pager can be used when there are more than the limit of 100 activities to display", async () => {
    const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);

    const recordsToCreate = [];
    const activityToCreate = [];

    for (let i = 0; i < 101; i++) {
        activityToCreate.push({
            display_name: "An activity " + i * 2,
            date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[0],
        });
        activityToCreate.push({
            display_name: "An activity " + (i * 2 + 1),
            date_deadline: serializeDate(DateTime.now().plus({ days: 2 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[1],
        });
    }
    const createdActivity = pyEnv["mail.activity"].create(activityToCreate);
    for (let i = 0; i < 101; i++) {
        recordsToCreate.push({
            name: "pagerTestRecord" + i,
            activity_ids: [createdActivity[i * 2], createdActivity[i * 2 + 1]],
        });
    }
    pyEnv["mail.test.activity"].create(recordsToCreate);

    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
        domain: [["name", "like", "pagerTestRecord"]],
    });
    await contains(".o_activity_record", { count: 100 });
    await contains(".o_activity_summary_cell.planned", { count: 200 });
    await click(".o_pager_next");
    await contains(".o_activity_record");
    await contains(".o_activity_summary_cell.planned", { count: 2 });
    await click(".o_pager_previous");
    await contains(".o_activity_record", { count: 100 });
    await contains(".o_activity_summary_cell.planned", { count: 200 });
});

test("activity view: no content rendering", async () => {
    await start();
    // reset incompatible setup
    pyEnv["mail.activity.type"].unlink(pyEnv["mail.activity.type"].search([]));
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".o_view_nocontent");
    await contains(".o_view_nocontent .o_view_nocontent_empty_folder", {
        text: "No data to display",
    });
});

test("activity view: batch send mail on activity", async () => {
    const mailTestActivityIds = pyEnv["mail.test.activity"].search([]);
    const mailTemplateIds = pyEnv["mail.template"].search([]);
    onRpc("activity_send_mail", (args) => {
        step(JSON.stringify(args.args));
        return true;
    });
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await click("[data-bs-toggle=dropdown]", {
        parent: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".dropdown-menu.show .o_send_mail_template", { count: 2 });
    await click(".o_send_mail_template", { text: "Template1" });
    await assertSteps([
        `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[0]}]`, // template 1 sendt on activity 1 and 2
    ]);
    await click(".o_send_mail_template", { text: "Template2" });
    await assertSteps([
        `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[1]}]`, // template 2 sendt on activity 1 and 2
    ]);
});

test("activity view: activity_ids condition in domain", async () => {
    onRpc("get_activity_data", (args) => step(JSON.stringify(args.kwargs.domain)));
    onRpc("web_search_read", (args) => step(JSON.stringify(args.kwargs.domain)));
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });

    await click(".o_pager_value");
    await contains(".o_pager_value:focus");
    keyDown("Enter");

    await assertSteps([
        // load view requests
        JSON.stringify([["activity_ids.active", "in", [true, false]]]),
        '[[1,"=",1]]', // Due to the relational model patch above that removes it
        // pager requests
        JSON.stringify([["activity_ids.active", "in", [true, false]]]),
        '[[1,"=",1]]', // Due to the dynamic list patch above that removes it
    ]);
});

test("activity view: activity widget", async () => {
    const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);
    const [mailTestActivityId2] = pyEnv["mail.test.activity"].search([
        ["name", "=", "Office planning"],
    ]);
    const [mailTemplateId1] = pyEnv["mail.template"].search([["name", "=", "Template1"]]);
    onRpc("activity_send_mail", (args) => {
        expect(args.args).toEqual([[mailTestActivityId2], mailTemplateId1]);
        step("activity_send_mail");
        return true;
    });
    onRpc("action_feedback_schedule_next", (args) => {
        expect(args.args).toEqual([pyEnv["mail.activity"].search([["state", "=", "overdue"]])]);
        expect(args.kwargs.feedback).toBe("feedback2");
        step("action_feedback_schedule_next");
        return { serverGeneratedAction: true };
    });
    const env = await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            if (action.serverGeneratedAction) {
                step("serverGeneratedAction");
            } else if (action.res_model === "mail.compose.message") {
                expect(action.context).toEqual({
                    default_model: "mail.test.activity",
                    default_res_ids: [mailTestActivityId2],
                    default_subtype_xmlid: "mail.mt_comment",
                    default_template_id: mailTemplateId1,
                    force_email: true,
                });
                step("do_action_compose");
            } else if (action.res_model === "mail.activity.schedule") {
                expect(action.context).toEqual({
                    default_activity_type_id: mailActivityTypeIds[1],
                    active_ids: [mailTestActivityId2],
                    active_id: mailTestActivityId2,
                    active_model: "mail.test.activity",
                });
                step("do_action_activity");
            } else {
                step("Unexpected action" + action.res_model);
            }
        },
    });
    await click(".today .o-mail-ActivityCell-deadline");
    await contains(".o-mail-ActivityListPopover");
    await contains(".o-mail-ActivityListPopover-todayTitle", { text: "Today" });
    await contains(".o-mail-ActivityMailTemplate-name", { text: "Template1" });
    await contains(".o-mail-ActivityMailTemplate-name", { text: "Template2" });
    await click(".o-mail-ActivityMailTemplate-preview[data-mail-template-id='1']");
    await assertSteps(["do_action_compose"]);
    await click(".today .o-mail-ActivityCell-deadline");
    await click(".o-mail-ActivityMailTemplate-send[data-mail-template-id='1']");
    await assertSteps(["activity_send_mail"]);
    await click(".overdue .o-mail-ActivityCell-deadline");
    await contains(".o-mail-ActivityMailTemplate-name", { count: 0 });
    await click(".o-mail-ActivityListPopover button", { text: "Schedule an activity" });
    await assertSteps(["do_action_activity"]);
    await contains(".o-mail-ActivityListPopover", { count: 0 });
    await click(".overdue .o-mail-ActivityCell-deadline");
    await click(".o-mail-ActivityListPopoverItem-markAsDone");
    await insertText(
        ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
        "feedback2"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']");
    await assertSteps(["action_feedback_schedule_next", "serverGeneratedAction"]);
});

test("activity view: Mark as done with keep done enabled", async () => {
    const emailActType = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
    pyEnv["mail.activity.type"].write([emailActType], { keep_done: true });
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".o_activity_view:not(.o_action)");
    const domActivity = document.querySelector(".o_activity_view:not(.o_action)");
    const domHeaderEmail = domActivity.querySelector("table thead tr:first-child th:nth-child(2)");
    const selRowOfficeCellEmail = "table tbody tr:nth-child(2) td:nth-child(2)";

    await contains(".o_animated_number", {
        target: domHeaderEmail,
        text: "2",
    });
    await contains(".o_column_progress_aggregated_on", {
        target: domHeaderEmail,
        text: "2",
    });
    await click(`${selRowOfficeCellEmail} > div`, {
        target: domActivity,
    });
    await click(".o-mail-ActivityListPopoverItem .o-mail-ActivityListPopoverItem-markAsDone");
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await contains(".o_animated_number", {
        target: domHeaderEmail,
        text: "1",
    });
    await contains(".o_column_progress_aggregated_on", {
        target: domHeaderEmail,
        text: "2",
    });
});

test("activity view: no group_by_menu and no comparison_menu", async () => {
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await click(".o_searchview_dropdown_toggler");
    await contains(".o-dropdown--menu .o_dropdown_container", { count: 2 });
    await contains(".o-dropdown--menu .o_filter_menu");
    await contains(".o-dropdown--menu .o_favorite_menu");
});

test("activity view: group_by in the action has no effect", async () => {
    patchWithCleanup(ActivityModel.prototype, {
        async load(params) {
            // force params to have a groupBy set, the model should ignore this value during the load
            params.groupBy = ["user_id"];
            await super.load(params);
        },
    });
    onRpc("get_activity_data", ({ kwargs }) => {
        expect(kwargs.groupby).toBe(undefined);
        step("get_activity_data");
    });
    await start();
    registerArchs(archs);
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await assertSteps(["get_activity_data"]);
});

test("activity view: search more to schedule an activity for a record of a respecting model", async () => {
    const mailTestActivityId1 = pyEnv["mail.test.activity"].create({
        name: "MailTestActivity 3",
    });
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": '<tree string="MailTestActivity"><field name="name"/></tree>',
    };
    const env = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            step("doAction");
            const expectedAction = {
                context: {
                    active_ids: [mailTestActivityId1],
                    active_id: mailTestActivityId1,
                    active_model: "mail.test.activity",
                },
                name: "Schedule Activity",
                res_model: "mail.activity.schedule",
                target: "new",
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
            };
            expect(action).toEqual(expectedAction);
            options.onClose();
        },
    });
    await click(".o_activity_view tfoot tr .o_record_selector");
    await contains(".o_data_row .o_data_cell", {
        count: 3,
        parent: [".modal-dialog", { text: "Search: MailTestActivity" }],
    });
    await click(".o_data_row .o_data_cell", {
        text: "MailTestActivity 3",
        parent: [".modal-dialog", { text: "Search: MailTestActivity" }],
    });
    await assertSteps(["doAction"]);
});

test("activity view: Domain should not reset on load", async () => {
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": '<tree string="MailTestActivity"><field name="name"/></tree>',
    };
    const env = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
        domain: [["id", "=", 1]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            step("doAction");
            options.onClose();
        },
    });

    await click(".o_activity_view .o_record_selector");
    // search create dialog
    await click(".modal-lg .o_data_row .o_data_cell");
    await assertSteps(["doAction"]);
    await click(".o_activity_view .o_record_selector");
    // again open search create dialog
    await contains(".modal-lg .o_data_row");
});

test("activity view: 'scheduleActivity' does not add activity_ids condition as selectCreateDialog domain", async () => {
    patchWithCleanup(ActivityController.prototype, {
        scheduleActivity() {
            super.scheduleActivity();
            step(JSON.stringify(this.getSearchProps().domain));
        },
    });
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": '<tree string="MailTestActivity"><field name="name"/></tree>',
    };
    const env = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            options.onClose?.();
        },
    });
    // open search create dialog and schedule an activity
    await click(".o_activity_view .o_record_selector");
    await click(".modal-lg .o_data_row .o_data_cell", {
        text: "Meeting Room Furnitures",
    });

    // again open search create dialog
    await click(".o_activity_view .o_record_selector");
    await assertSteps(["[]", "[]"]);
});

test("activity view: 'onClose' of 'openActivityFormView' does not add activity_ids condition as selectCreateDialog domain", async () => {
    patchWithCleanup(ActivityController.prototype, {
        openActivityFormView(resId, activityTypeId) {
            super.openActivityFormView(resId, activityTypeId);
            step(JSON.stringify(this.getSearchProps().domain));
        },
    });
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": '<tree string="MailTestActivity"><field name="name"/></tree>',
    };
    const env = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            options.onClose?.();
        },
    });
    //schedule an activity on an empty activity cell
    await click(
        ".o_activity_view :nth-child(1 of .o_data_row) :nth-child(1 of .o_activity_empty_cell)"
    );
    await assertSteps(["[]"]);
});

test("activity view: 'onReloadData' does not add activity_ids condition as selectCreateDialog domain", async () => {
    patchWithCleanup(ActivityController.prototype, {
        get rendererProps() {
            const rendererProps = { ...super.rendererProps };
            step(JSON.stringify(this.getSearchProps().domain));
            return rendererProps;
        },
    });
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": '<tree string="MailTestActivity"><field name="name"/></tree>',
    };
    const env = await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            options.onClose?.();
        },
    });

    //schedule another activity on an activity cell with a scheduled activity
    await click(".today .o-mail-ActivityCell-deadline");
    await click(".o-mail-ActivityListPopover button:contains(Schedule an activity)");
    await assertSteps(["[]", "[]", "[]"]);
});

test("Activity view: discard an activity creation dialog", async () => {
    registerArchs(archs);
    onRpc("check_access_rights", () => true);
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await click(
        ".o_activity_view  :nth-child(1 of .o_data_row) :nth-child(1 of .o_activity_empty_cell)"
    );
    await contains(".modal.o_technical_modal");
    await click(".modal.o_technical_modal .o_form_button_cancel");
    await contains(".modal.o_technical_modal", { count: 0 });
});

test("Activity view: many2one_avatar_user widget in activity view", async () => {
    const [mailTestActivityId1] = pyEnv["mail.test.activity"].search([
        ["name", "=", "Meeting Room Furnitures"],
    ]);
    const resUsersId1 = pyEnv["res.users"].create({
        display_name: "first user",
        avatar_128: "Atmaram Bhide",
    });
    pyEnv["mail.test.activity"].write([mailTestActivityId1], { activity_user_id: resUsersId1 });
    registerArchs({
        "mail.test.activity,false,activity": `<activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <field name="activity_user_id" widget="many2one_avatar_user"/>
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
    });
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".o_m2o_avatar", { count: 2 });
    await contains(
        `tr:nth-child(2) .o_m2o_avatar > img[data-src="/web/image/res.users/${resUsersId1}/avatar_128"]`
    );
    // "should not have text on many2one_avatar_user if onlyImage node option is passed"
    await contains(".o_m2o_avatar > span", { count: 0 });
});

test("Activity view: on_destroy_callback doesn't crash", async () => {
    patchWithCleanup(ActivityRenderer.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                step("mounted");
            });
            onWillUnmount(() => {
                step("willUnmount");
            });
        },
    });
    registerArchs(archs);
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    // force the unmounting of the activity view by opening another one
    await openFormView("mail.test.activity");
    await assertSteps(["mounted", "willUnmount"]);
});

test("Schedule activity dialog uses the same search view as activity view", async () => {
    pyEnv["mail.test.activity"].unlink(pyEnv["mail.test.activity"].search([]));
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "list,false": `<list><field name="name"/></list>`,
    };
    registerArchs(archs);
    onRpc("get_views", (args) => step(JSON.stringify(args.kwargs.views)));
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await assertSteps([
        `[[${DEFAULT_MAIL_VIEW_ID},"activity"],[${DEFAULT_MAIL_SEARCH_ID},"search"]]`,
    ]);
    // click on "Schedule activity"
    await click(".o_activity_view .o_record_selector");
    await assertSteps([`[[false,"list"],[${DEFAULT_MAIL_SEARCH_ID},"search"]]`]);
    // open an activity view (with search arch 1)
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
        searchViewId: 1,
    });
    await assertSteps([`[[${DEFAULT_MAIL_VIEW_ID},"activity"],[1,"search"]]`]);
    // click on "Schedule activity"
    await click(".o_activity_view .o_record_selector");
    await assertSteps([`[[false,"list"],[1,"search"]]`]);
});

test("Activity view: apply progressbar filter", async () => {
    const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);
    const mailTemplateIds = pyEnv["mail.template"].search([]);
    const [resUsersId1] = pyEnv["res.users"].search([]);
    pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[2],
            mail_template_ids: mailTemplateIds,
            user_id: resUsersId1,
        },
    ]);
    const mailActivityIds = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[0],
            user_id: resUsersId1,
        },
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
            can_write: true,
            state: "planned",
            activity_type_id: mailActivityTypeIds[2],
            mail_template_ids: mailTemplateIds,
            user_id: resUsersId1,
        },
    ]);
    const [mailTestActivityId1] = pyEnv["mail.test.activity"].search([
        ["name", "=", "Meeting Room Furnitures"],
    ]);
    pyEnv["mail.test.activity"].write([mailTestActivityId1], {
        activity_ids: mailActivityIds,
    });
    registerArchs(archs);
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".o_activity_record", {
        text: "Office planning",
        parent: [".o_activity_view tbody tr:first-of-type"],
    });
    await contains(".o_activity_view .planned", { count: 2 });
    await click(".progress-bar[data-tooltip='1 Planned']", {
        parent: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".o_activity_view thead .o_activity_filter_planned");
    await contains(".progress-bar-striped");
    await contains(".progress-bar-animated.progress-bar-striped[data-tooltip='1 Planned']", {
        parent: [".o_activity_view_table th", { text: "Email" }],
    });
    await contains(".o_activity_view tbody .o_activity_filter_planned", { count: 5 });
    const tr = document.querySelectorAll(".o_activity_view tbody tr")[1];
    expect(tr.querySelectorAll("td")[1]).toHaveClass("o_activity_empty_cell");
});

test("Activity view: hide/show columns", async () => {
    registerArchs(archs);
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });

    for (const [index, column] of ["Email", "Call", "Call for Demo", "To Do"].entries()) {
        await contains(`.o_activity_view th:nth-child(${index + 2}) div span:first-child`, {
            text: column,
        });
    }
    await contains(".o_activity_view th:last-child button.dropdown-toggle");
    await click("th:last-child button.dropdown-toggle");
    await click("input[name='Email']");
    for (const [index, column] of ["Call", "Call for Demo", "To Do"].entries()) {
        await contains(`.o_activity_view th:nth-child(${index + 2}) div span:first-child`, {
            text: column,
        });
    }
    await click("input[name='Call for Demo']");
    for (const [index, column] of ["Call", "To Do"].entries()) {
        await contains(`.o_activity_view th:nth-child(${index + 2}) div span:first-child`, {
            text: column,
        });
    }

    await click("input[name='Email']");
    for (const [index, column] of ["Email", "Call", "To Do"].entries()) {
        await contains(`.o_activity_view th:nth-child(${index + 2}) div span:first-child`, {
            text: column,
        });
    }
});

test("Activity view: luxon in renderingContext", async () => {
    registerArchs({
        "mail.test.activity,false,activity": `
            <activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <t t-if="luxon">
                            <span class="luxon">luxon</span>
                        </t>
                    </div>
                </templates>
            </activity>
        `,
    });
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(".luxon", { count: 2 });
});

test("test displaying image (write_date field)", async () => {
    // the presence of write_date field ensures that the image is reloaded when necessary
    registerArchs({
        "mail.test.activity,false,activity": `
            <activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <img t-att-src="activity_image('partner', 'image', record.id.raw_value)"/>
                        <field name="id"/>
                    </div>
                </templates>
            </activity>`,
    });
    onRpc("web.search_read", (route, args) => {
        expect(Object.keys(args.specification)).toEqual(["write_date", "id"]);
        return { length: 2, records: [{ id: 1 }, { id: 2 }] };
    });
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    await contains(`.o_activity_record img[src='${getOrigin()}/web/image/partner/2/image']`);
});

test("test node visibility depends on invisible attribute on the node and in the context", async () => {
    registerArchs(archs);
    MailTestActivity._views = {
        ...MailTestActivity._views,
        "activity,1": `
                <activity string="MailTestActivity">
                    <div t-name="activity-box">
                        <span t-att-title="record.name.value">
                            <field name="name" display="full" class="w-100 text-truncate"/>
                        </span>
                        <span class="invisible_node" invisible="context.get('invisible', False)">
                            Test invisible
                        </span>
                    </div>
                </activity>`,
    };
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[1, "activity"]],
    });
    await contains(".invisible_node", { count: 2 });
    await openView({
        res_model: "mail.test.activity",
        views: [[1, "activity"]],
        context: { invisible: true },
    });
    await contains(".invisible_node", { count: 0 });
});

test("update activity view after creating multiple activities", async () => {
    MailTestActivity._views = {
        ...MailTestActivity._views,
        [`activity,${DEFAULT_MAIL_VIEW_ID}`]: `
            <activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
        "list,false": `<tree string="MailTestActivity"><field name="name"/><field name="activity_ids" widget="list_activity"/></tree>`
    }
    MailActivitySchedule._views = {
        ...MailActivitySchedule._views,
        [`form,${DEFAULT_MAIL_VIEW_ID}`]: "<form><field name='summary'/></form>",
    }

    const Activity = pyEnv["mail.activity"];
    const activityToCreate = omit(Activity[0], "id");
    Activity.unlink(Activity.search([]));

    onRpc(({method, model}) => {
        if (method === "web_save" && model === "mail.activity.schedule") {
            Activity.create(activityToCreate);
        }
    });

    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    expect(".o_activity_summary_cell").toHaveCount(0);
    await click("table tfoot tr .o_record_selector");
    await click(
        ".o_list_renderer table tbody tr:nth-child(2) td:nth-child(2) .o-mail-ActivityButton"
    );
    await webContains(".o-mail-ActivityListPopover > button.btn-secondary").click();
    const modalSchedule = await waitFor(".modal:has(.o_form_view)");
    await insertText(`.o_form_view .o_field_widget[name='summary'] input`, "test1", {
        target: modalSchedule,
    });
    await click(".modal-footer button.o_form_button_save", {target: modalSchedule});
    await click(".modal-footer button.o_form_button_cancel");
    await waitFor(".o_activity_summary_cell:not(.o_activity_empty_cell)");
    expect(".o_activity_summary_cell:not(.o_activity_empty_cell)").toHaveCount(1);
});

test("Activity View: Hide 'New' button in SelectCreateDialog based on action context", async () => {
    MailTestActivity._views = {
        ...MailTestActivity._views,
        [`activity,${DEFAULT_MAIL_VIEW_ID}`]: `
            <activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
        "list,false": `
            <tree string="MailTestActivity">
                <field name="name"/>
                <field name="activity_ids" widget="list_activity"/>
            </tree>
        `,
    }
    await start();
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
        context: { create: false },
    });
    await click("table tfoot tr .o_record_selector");
    await animationFrame();
    expect('.o_create_button').toHaveCount(0, {
        message: "'New' button should be hidden",
    });
});
