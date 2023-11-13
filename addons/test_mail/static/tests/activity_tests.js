/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import { start } from "@mail/../tests/helpers/test_utils";

import { RelationalModel } from "@web/model/relational_model/relational_model";
import { Domain } from "@web/core/domain";
import { serializeDate } from "@web/core/l10n/dates";
import { deepEqual } from "@web/core/utils/objects";
import { session } from "@web/session";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { editInput, patchWithCleanup, click, patchDate } from "@web/../tests/helpers/utils";
import { toggleSearchBarMenu } from "@web/../tests/search/helpers";
import { contains } from "@web/../tests/utils";
import { doAction } from "@web/../tests/webclient/helpers";
import { onMounted, onWillUnmount } from "@odoo/owl";
const { DateTime } = luxon;

let serverData;
let pyEnv;

QUnit.module("test_mail", {}, function () {
    QUnit.module("activity view", {
        async beforeEach() {
            patchDate(2023, 4, 8, 10, 0, 0);
            patchWithCleanup(RelationalModel.prototype, {
                async load(params) {
                    if (params.domain) {
                        // Remove domain term used to filter record having "done" activities (not understood by the getRecords mock)
                        const domain = new Domain(params.domain);
                        const newDomain = Domain.removeDomainLeaves(domain.toList(), [
                            "activity_ids.active",
                        ]);
                        if (!deepEqual(domain.toList(), newDomain.toList())) {
                            return super.load({
                                ...params,
                                domain: newDomain.toList(),
                                context: params.context
                                    ? { ...params.context, active_test: false }
                                    : { active_test: false },
                            });
                        }
                        return super.load(params);
                    }
                    return super.load(params);
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
            const resUsersId1 = pyEnv["res.users"].create({ display_name: "first user" });
            const mailActivityIds = pyEnv["mail.activity"].create([
                {
                    display_name: "An activity",
                    date_deadline: serializeDate(DateTime.now().plus({ days: 3 })),
                    can_write: true,
                    state: "planned",
                    activity_type_id: mailActivityTypeIds[0],
                    mail_template_ids: mailTemplateIds,
                    user_id: resUsersId1,
                },
                {
                    display_name: "An activity",
                    date_deadline: serializeDate(DateTime.now()),
                    can_write: true,
                    state: "today",
                    activity_type_id: mailActivityTypeIds[0],
                    mail_template_ids: mailTemplateIds,
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
            serverData = {
                views: {
                    "mail.test.activity,false,activity":
                        '<activity string="MailTestActivity">' +
                        "<templates>" +
                        '<div t-name="activity-box">' +
                        '<field name="name"/>' +
                        "</div>" +
                        "</templates>" +
                        "</activity>",
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
                },
            };
        },
    });

    QUnit.test("activity view: simple activity rendering", async function (assert) {
        assert.expect(14);
        const mailTestActivityIds = pyEnv["mail.test.activity"].search([]);
        const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);

        const { env, openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        patchWithCleanup(env.services.action, {
            doAction(action, options) {
                assert.deepEqual(
                    action,
                    {
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
                    },
                    "should do a do_action with correct parameters"
                );
                options.onClose();
                return Promise.resolve();
            },
        });

        const $activity = $(document.querySelector(".o_activity_view"));
        assert.containsOnce($activity, "table", "should have a table");
        const $th1 = $activity.find("table thead tr:first th:nth-child(2)");
        assert.containsOnce(
            $th1,
            "span:first:contains(Email)",
            'should contain "Email" in header of first column'
        );
        assert.containsOnce(
            $th1,
            ".o_activity_counter",
            "should contain a progressbar in header of first column"
        );
        assert.hasAttrValue(
            $th1.find(".o_column_progress .progress-bar:first"),
            "data-tooltip",
            "1 Planned",
            "the counter progressbars should be correctly displayed"
        );
        assert.hasAttrValue(
            $th1.find(".o_column_progress .progress-bar:nth-child(2)"),
            "data-tooltip",
            "1 Today",
            "the counter progressbars should be correctly displayed"
        );
        const $th2 = $activity.find("table thead tr:first th:nth-child(3)");
        assert.containsOnce(
            $th2,
            "span:first:contains(Call)",
            'should contain "Call" in header of second column'
        );
        assert.hasAttrValue(
            $th2.find(".o_column_progress .progress-bar"),
            "data-tooltip",
            "1 Overdue",
            "the counter progressbars should be correctly displayed"
        );
        assert.containsNone(
            $activity,
            "table thead tr:first th:nth-child(4) .o_kanban_counter",
            "should not contain a progressbar in header of 3rd column"
        );
        assert.ok(
            $activity.find("table tbody tr:first td:first:contains(Office planning)").length,
            'should contain "Office planning" in first colum of first row'
        );
        assert.ok(
            $activity.find("table tbody tr:nth-child(2) td:first:contains(Meeting Room Furnitures)")
                .length,
            'should contain "Meeting Room Furnitures" in first colum of second row'
        );

        const today = DateTime.now().toLocaleString(luxon.DateTime.DATE_SHORT);

        assert.ok(
            $activity.find(
                "table tbody tr:first td:nth-child(2).today .o-mail-ActivityCell-deadline:contains(" +
                    today +
                    ")"
            ).length,
            "should contain an activity for today in second cell of first line " + today
        );
        const td = "table tbody tr:nth-child(1) td.o_activity_empty_cell";
        assert.containsN(
            $activity,
            td,
            2,
            "should contain an empty cell as no activity scheduled yet."
        );

        // schedule an activity (this triggers a do_action)
        await testUtils.fields.editAndTrigger($activity.find(td + ":first"), null, [
            "mouseenter",
            "click",
        ]);
        assert.containsOnce(
            $activity,
            "table tfoot tr .o_record_selector",
            "should contain search more selector to choose the record to schedule an activity for it"
        );
    });

    QUnit.test("activity view: Activity rendering with done activities", async function (assert) {
        const activityTypeUpload = pyEnv["mail.activity.type"].create({
            category: "upload_file",
            name: "Test Upload document",
            keep_done: true,
        });
        pyEnv["mail.activity"].create(
            Object.entries(["done", "done", "done", "done", "planned", "planned", "planned"]).map(
                ([idx, state]) => ({
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
                                      create_uid: pyEnv.currentUserId,
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
                    user_id: pyEnv["res.users"].create({ display_name: `user${idx}` }),
                })
            )
        );
        const [meetingRecord, officeRecord] = pyEnv["mail.test.activity"].search([]);
        const uploadDoneActs = pyEnv["mail.activity"].searchRead([
            ["activity_type_id", "=", activityTypeUpload],
            ["active", "=", false],
        ]);
        const uploadPlannedActs = pyEnv["mail.activity"].searchRead([
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
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        const domActivity = document.querySelector(".o_activity_view");
        const domHeaderUpload = domActivity.querySelector(
            "table thead tr:first-child th:nth-child(6)"
        );
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
            text: luxon.DateTime.fromISO(uploadPlannedActs[0].date_deadline).toLocaleString(
                luxon.DateTime.DATE_SHORT
            ),
            target: domRowMeetingCellUpload,
        });
        await contains(".o-mail-ActivityCell-deadline", {
            text: luxon.DateTime.fromISO(uploadDoneActs[1].date_done).toLocaleString(
                luxon.DateTime.DATE_SHORT
            ),
            target: domRowOfficeCellUpload,
        });
        // Activity list popovers content
        await click(domActivity, `${selRowMeetingCellUpload} > div`);
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
            text: luxon.DateTime.fromISO(uploadDoneActs[0].date_done).toLocaleString(
                luxon.DateTime.DATE_SHORT
            ),
        });

        await click(domActivity, `${selRowOfficeCellUpload} > div`);
        await contains(".o-mail-ActivityListPopover .badge.text-bg-secondary", { text: "3" }); // 3 done
        for (const actIdx of [1, 2, 3]) {
            await contains(".o-mail-ActivityListPopoverItem", {
                text: luxon.DateTime.fromISO(uploadDoneActs[actIdx].date_done).toLocaleString(
                    luxon.DateTime.DATE_SHORT
                ),
            });
            await contains(".o-mail-ActivityListPopoverItem", {
                text: uploadDoneActs[actIdx].user_id[1],
            });
        }
    });

    QUnit.test(
        "activity view: a pager can be used when there are more than the limit of 100 activities to display",
        async function (assert) {
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

            const { openView } = await start({
                serverData,
            });
            await openView({
                res_model: "mail.test.activity",
                views: [[false, "activity"]],
                domain: [["name", "like", "pagerTestRecord"]],
            });
            assert.containsN(
                document.body,
                ".o_activity_record",
                100,
                "Only 100 records should have been displayed"
            );
            assert.containsN(
                document.body,
                ".o_activity_summary_cell.planned",
                200,
                "200 activities should have been displayed (2 per records)"
            );
            await click(document.querySelector(".o_pager_next"));
            assert.containsN(
                document.body,
                ".o_activity_record",
                1,
                "Only 1 record is now displayed"
            );
            assert.containsN(
                document.body,
                ".o_activity_summary_cell.planned",
                2,
                "Only the 2 activities of the last record are now displayed"
            );
            await click(document.querySelector(".o_pager_previous"));
            assert.containsN(document.body, ".o_activity_record", 100);
            assert.containsN(document.body, ".o_activity_summary_cell.planned", 200);
        }
    );

    QUnit.test("activity view: no content rendering", async function () {
        const { openView, pyEnv } = await start({ serverData });
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

    QUnit.test("activity view: batch send mail on activity", async function (assert) {
        assert.expect(6);

        const mailTestActivityIds = pyEnv["mail.test.activity"].search([]);
        const mailTemplateIds = pyEnv["mail.template"].search([]);
        const { openView } = await start({
            serverData,
            mockRPC: function (route, args) {
                if (args.method === "activity_send_mail") {
                    assert.step(JSON.stringify(args.args));
                    return Promise.resolve(true);
                }
            },
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        const $activity = $(document);
        assert.notOk(
            $activity.find(
                "table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show"
            ).length,
            "dropdown shouldn't be displayed"
        );

        testUtils.dom.click(
            $activity.find("table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v")
        );
        assert.ok(
            $activity.find(
                "table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show"
            ).length,
            "dropdown should have appeared"
        );

        testUtils.dom.click(
            $activity.find(
                "table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template2)"
            )
        );
        assert.notOk(
            $activity.find(
                "table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show"
            ).length,
            "dropdown shouldn't be displayed"
        );

        testUtils.dom.click(
            $activity.find("table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v")
        );
        testUtils.dom.click(
            $activity.find(
                "table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template1)"
            )
        );
        assert.verifySteps([
            `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[1]}]`, // send mail template 1 on mail.test.activity 1 and 2
            `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[0]}]`, // send mail template 2 on mail.test.activity 1 and 2
        ]);
    });

    QUnit.test("activity view: activity_ids condition in domain", async function (assert) {
        assert.expect(3);
        const { openView } = await start({
            serverData,
            mockRPC: function (route, args) {
                if (["get_activity_data", "web_search_read"].includes(args.method)) {
                    assert.step(JSON.stringify(args.kwargs.domain));
                }
            },
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });

        assert.verifySteps([
            JSON.stringify([["activity_ids.active", "in", [true, false]]]),
            '[[1,"=",1]]', // Due to the patch above that removes it
        ]);
    });

    QUnit.test("activity view: activity widget", async function (assert) {
        assert.expect(16);

        const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);
        const [mailTestActivityId2] = pyEnv["mail.test.activity"].search([
            ["name", "=", "Office planning"],
        ]);
        const [mailTemplateId1] = pyEnv["mail.template"].search([["name", "=", "Template1"]]);
        const { env, openView } = await start({
            mockRPC: function (route, args) {
                if (args.method === "activity_send_mail") {
                    assert.deepEqual(
                        [[mailTestActivityId2], mailTemplateId1],
                        args.args,
                        "Should send template related to mailTestActivity2"
                    );
                    assert.step("activity_send_mail");
                    // random value returned in order for the mock server to know that this route is implemented.
                    return true;
                }
                if (args.method === "action_feedback_schedule_next") {
                    assert.deepEqual(
                        [pyEnv["mail.activity"].search([["state", "=", "overdue"]])],
                        args.args,
                        "Should execute action_feedback_schedule_next only on the overude activity"
                    );
                    assert.equal(args.kwargs.feedback, "feedback2");
                    assert.step("action_feedback_schedule_next");
                    return Promise.resolve({ serverGeneratedAction: true });
                }
            },
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        patchWithCleanup(env.services.action, {
            doAction(action) {
                if (action.serverGeneratedAction) {
                    assert.step("serverGeneratedAction");
                } else if (action.res_model === "mail.compose.message") {
                    assert.deepEqual(
                        {
                            default_model: "mail.test.activity",
                            default_res_ids: [mailTestActivityId2],
                            default_subtype_xmlid: "mail.mt_comment",
                            default_template_id: mailTemplateId1,
                            force_email: true,
                        },
                        action.context
                    );
                    assert.step("do_action_compose");
                } else if (action.res_model === "mail.activity.schedule") {
                    assert.deepEqual(
                        {
                            default_activity_type_id: mailActivityTypeIds[1],
                            active_id: mailTestActivityId2,
                            active_ids: [mailTestActivityId2],
                            active_model: "mail.test.activity",
                        },
                        action.context
                    );
                    assert.step("do_action_activity");
                } else {
                    assert.step("Unexpected action" + action.res_model);
                }
                return Promise.resolve();
            },
        });

        await click(document.querySelector(".today .o-mail-ActivityCell-deadline"));
        assert.containsOnce(
            document.body,
            ".o-mail-ActivityListPopover",
            "dropdown should be displayed"
        );
        assert.ok(
            document
                .querySelector(".o-mail-ActivityListPopover-todayTitle")
                .textContent.includes("Today"),
            "Title should be today"
        );
        assert.ok(
            [...document.querySelectorAll(".o-mail-ActivityMailTemplate-name")].filter((el) =>
                el.textContent.includes("Template1")
            ).length,
            "Template1 should be available"
        );
        assert.ok(
            [...document.querySelectorAll(".o-mail-ActivityMailTemplate-name")].filter((el) =>
                el.textContent.includes("Template2")
            ).length,
            "Template2 should be available"
        );

        await click(document.querySelector(".o-mail-ActivityMailTemplate-preview"));
        await click(document.querySelector(".today .o-mail-ActivityCell-deadline"));
        await click(document.querySelector(".o-mail-ActivityMailTemplate-send"));
        await click(document.querySelector(".overdue .o-mail-ActivityCell-deadline"));
        assert.containsNone(
            document.body,
            ".o-mail-ActivityMailTemplate-name",
            "No template should be available"
        );

        await click($(".o-mail-ActivityListPopover button:contains(Schedule an activity)")[0]);
        await click(document.querySelector(".overdue .o-mail-ActivityCell-deadline"));
        await click(document.querySelector(".o-mail-ActivityListPopoverItem-markAsDone"));
        await editInput(
            document.body,
            ".o-mail-ActivityMarkAsDone textarea[placeholder='Write Feedback']",
            "feedback2"
        );
        await click(
            document.querySelector(
                ".o-mail-ActivityMarkAsDone button[aria-label='Done and Schedule Next']"
            )
        );
        assert.verifySteps([
            "do_action_compose",
            "activity_send_mail",
            "do_action_activity",
            "action_feedback_schedule_next",
            "serverGeneratedAction",
        ]);
    });

    QUnit.test("activity view: Mark as done with keep done enabled", async function (assert) {
        const emailActType = pyEnv["mail.activity.type"].search([["name", "=", "Email"]])[0];
        pyEnv["mail.activity.type"].write([emailActType], {
            keep_done: true,
        });
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
            context: { active_test: false },
        });
        const domActivity = document.querySelector(".o_activity_view");
        const domHeaderEmail = domActivity.querySelector(
            "table thead tr:first-child th:nth-child(2)"
        );
        const selRowOfficeCellEmail = "table tbody tr:nth-child(2) td:nth-child(2)";

        await contains(".o_animated_number", {
            target: domHeaderEmail,
            text: "2",
        });
        await contains(".o_column_progress_aggregated_on", {
            target: domHeaderEmail,
            text: "2",
        });
        await click(domActivity, `${selRowOfficeCellEmail} > div`);
        await click(
            document,
            ".o-mail-ActivityListPopoverItem .o-mail-ActivityListPopoverItem-markAsDone"
        );
        await click(document, ".o-mail-ActivityMarkAsDone button[aria-label='Done']");
        await contains(".o_animated_number", {
            target: domHeaderEmail,
            text: "1",
        });
        await contains(".o_column_progress_aggregated_on", {
            target: domHeaderEmail,
            text: "2",
        });
    });

    QUnit.test("activity view: no group_by_menu and no comparison_menu", async function (assert) {
        assert.expect(4);

        serverData.actions = {
            1: {
                id: 1,
                name: "MailTestActivity Action",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
            },
        };

        const mockRPC = (route, args) => {
            if (args.method === "get_activity_data") {
                assert.strictEqual(
                    args.kwargs.context.lang,
                    "zz_ZZ",
                    "The context should have been passed"
                );
            }
        };

        patchWithCleanup(session.user_context, { lang: "zz_ZZ" });

        const { webClient } = await start({ serverData, mockRPC });

        await doAction(webClient, 1);
        await toggleSearchBarMenu(document);
        assert.containsN(
            document.body,
            ".o_cp_searchview .o_dropdown_container",
            2,
            "only two elements should be available in view search"
        );
        assert.isVisible(
            document.querySelector(".o_cp_searchview .o_dropdown_container.o_filter_menu"),
            "filter should be available in view search"
        );
        assert.isVisible(
            document.querySelector(".o_cp_searchview .o_dropdown_container.o_favorite_menu"),
            "favorites should be available in view search"
        );
    });

    QUnit.test("activity view: group_by in the action has no effect", async function (assert) {
        assert.expect(1);

        patchWithCleanup(ActivityModel.prototype, {
            async load(params) {
                // force params to have a groupBy set, the model should ignore this value during the load
                params.groupBy = ["user_id"];
                await super.load(params);
            },
        });

        serverData.actions = {
            1: {
                id: 1,
                name: "MailTestActivity Action",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
            },
        };

        const mockRPC = (route, args) => {
            if (args.method === "get_activity_data") {
                assert.strictEqual(
                    args.kwargs.groupby,
                    undefined,
                    "groupby should have been removed from the load params"
                );
            }
        };

        const { webClient } = await start({ serverData, mockRPC });

        await doAction(webClient, 1);
    });

    QUnit.test(
        "activity view: search more to schedule an activity for a record of a respecting model",
        async function (assert) {
            assert.expect(5);
            const mailTestActivityId1 = pyEnv["mail.test.activity"].create({
                name: "MailTestActivity 3",
            });
            Object.assign(serverData.views, {
                "mail.test.activity,false,list":
                    '<tree string="MailTestActivity"><field name="name"/></tree>',
            });
            const { env, openView } = await start({
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        args.kwargs.name = "MailTestActivity";
                    }
                },
                serverData,
            });
            await openView({
                res_model: "mail.test.activity",
                views: [[false, "activity"]],
            });
            patchWithCleanup(env.services.action, {
                doAction(action, options) {
                    assert.step("doAction");
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
                    assert.deepEqual(
                        action,
                        expectedAction,
                        "should execute an action with correct params"
                    );
                    options.onClose();
                    return Promise.resolve();
                },
            });

            const activity = $(document);
            assert.containsOnce(
                activity,
                "table tfoot tr .o_record_selector",
                "should contain search more selector to choose the record to schedule an activity for it"
            );
            await testUtils.dom.click(activity.find("table tfoot tr .o_record_selector"));
            // search create dialog
            const $modal = $(".modal-lg");
            assert.strictEqual(
                $modal.find(".o_data_row").length,
                3,
                "all mail.test.activity should be available to select"
            );
            // select a record to schedule an activity for it (this triggers a do_action)
            await testUtils.dom.click($modal.find(".o_data_row:last .o_data_cell"));
            assert.verifySteps(["doAction"]);
        }
    );

    QUnit.test("Activity view: discard an activity creation dialog", async function (assert) {
        assert.expect(2);

        serverData.actions = {
            1: {
                id: 1,
                name: "MailTestActivity Action",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
            },
        };

        Object.assign(serverData.views, {
            "mail.activity,false,form": `<form>
                <field name="display_name"/>
                <footer>
                    <button string="Discard" class="btn-secondary" special="cancel"/>
                </footer>
            </form>`,
        });

        const mockRPC = (route, args) => {
            if (args.method === "check_access_rights") {
                return true;
            }
        };

        const { webClient } = await start({ serverData, mockRPC });
        await doAction(webClient, 1);

        await testUtils.dom.click(
            document.querySelector(".o_activity_view .o_data_row .o_activity_empty_cell")
        );
        await contains(".modal.o_technical_modal");

        await testUtils.dom.click($('.modal.o_technical_modal button[special="cancel"]'));
        await contains(".modal.o_technical_modal", { count: 0 });
    });

    QUnit.test(
        "Activity view: many2one_avatar_user widget in activity view",
        async function (assert) {
            assert.expect(3);

            const [mailTestActivityId1] = pyEnv["mail.test.activity"].search([
                ["name", "=", "Meeting Room Furnitures"],
            ]);
            const resUsersId1 = pyEnv["res.users"].create({
                display_name: "first user",
                avatar_128: "Atmaram Bhide",
            });
            pyEnv["mail.test.activity"].write([mailTestActivityId1], {
                activity_user_id: resUsersId1,
            });
            Object.assign(serverData.views, {
                "mail.test.activity,false,activity": `<activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <field name="activity_user_id" widget="many2one_avatar_user"/>
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
            });
            serverData.actions = {
                1: {
                    id: 1,
                    name: "MailTestActivity Action",
                    res_model: "mail.test.activity",
                    type: "ir.actions.act_window",
                    views: [[false, "activity"]],
                },
            };

            const { webClient } = await start({ serverData });
            await doAction(webClient, 1);

            await contains(".o_m2o_avatar", { count: 2 });
            assert.containsOnce(
                document.body,
                `tr:nth-child(2) .o_m2o_avatar > img[data-src="/web/image/res.users/${resUsersId1}/avatar_128"]`,
                "should have m2o avatar image"
            );
            // "should not have text on many2one_avatar_user if onlyImage node option is passed"
            await contains(".o_m2o_avatar > span", { count: 0 });
        }
    );

    QUnit.test("Activity view: on_destroy_callback doesn't crash", async function (assert) {
        assert.expect(3);

        patchWithCleanup(ActivityRenderer.prototype, {
            setup() {
                super.setup();
                onMounted(() => {
                    assert.step("mounted");
                });
                onWillUnmount(() => {
                    assert.step("willUnmount");
                });
            },
        });

        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        // force the unmounting of the activity view by opening another one
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "form"]],
        });

        assert.verifySteps(["mounted", "willUnmount"]);
    });

    QUnit.test(
        "Schedule activity dialog uses the same search view as activity view",
        async function (assert) {
            assert.expect(8);
            pyEnv["mail.test.activity"].unlink(pyEnv["mail.test.activity"].search([]));
            Object.assign(serverData.views, {
                "mail.test.activity,false,list": `<list><field name="name"/></list>`,
                "mail.test.activity,false,search": `<search/>`,
                "mail.test.activity,1,search": `<search/>`,
            });

            function mockRPC(route, args) {
                if (args.method === "get_views") {
                    assert.step(JSON.stringify(args.kwargs.views));
                }
            }

            const { webClient } = await start({ serverData, mockRPC });

            // open an activity view (with default search arch)
            await doAction(webClient, {
                name: "Dashboard",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
            });

            assert.verifySteps(['[[false,"activity"],[false,"search"]]']);

            // click on "Schedule activity"
            await click(document.querySelector(".o_activity_view .o_record_selector"));

            assert.verifySteps(['[[false,"list"],[false,"search"]]']);

            // open an activity view (with search arch 1)
            await doAction(webClient, {
                name: "Dashboard",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
                search_view_id: [1, "search"],
            });

            assert.verifySteps(['[[false,"activity"],[1,"search"]]']);

            // click on "Schedule activity"
            await click(document.querySelector(".o_activity_view .o_record_selector"));

            assert.verifySteps(['[[false,"list"],[1,"search"]]']);
        }
    );

    QUnit.test("Activity view: apply progressbar filter", async function (assert) {
        assert.expect(12);

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
        const mailActivityIds = pyEnv["mail.activity"].search([]);
        const [mailTestActivityId1] = pyEnv["mail.test.activity"].search([
            ["name", "=", "Meeting Room Furnitures"],
        ]);
        pyEnv["mail.test.activity"].write([mailTestActivityId1], {
            activity_ids: [mailActivityIds[0], mailActivityIds[3]],
        });

        serverData.actions = {
            1: {
                id: 1,
                name: "MailTestActivity Action",
                res_model: "mail.test.activity",
                type: "ir.actions.act_window",
                views: [[false, "activity"]],
            },
        };

        const { target, webClient } = await start({ serverData });

        await doAction(webClient, 1);

        assert.containsNone(
            document.querySelector(".o_activity_view thead"),
            ".o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false",
            "should not have active filter"
        );
        assert.containsNone(
            document.querySelector(".o_activity_view tbody"),
            ".o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false",
            "should not have active filter"
        );
        assert.strictEqual(
            document.querySelector(".o_activity_view tbody .o_activity_record").textContent,
            "Office planning",
            "'Office planning' should be first record"
        );
        assert.containsN(
            document.querySelector(".o_activity_view tbody"),
            ".planned",
            2,
            "other records should be available"
        );

        await click(document.querySelector(".o_column_progress .progress-bar"));
        assert.containsOnce(
            document.querySelector(".o_activity_view thead"),
            ".o_activity_filter_planned",
            "planned should be active filter"
        );
        assert.hasClass(
            target.querySelector(".o_activity_type_cell:nth-child(2) .bg-success"),
            "progress-bar-animated progress-bar-striped",
            "progress bar is animated with a strip effect"
        );
        assert.containsOnce(target, ".progress-bar-striped", "only one progress bar is animated");
        assert.containsN(
            document.querySelector(".o_activity_view tbody"),
            ".o_activity_filter_planned",
            5,
            "planned should be active filter"
        );
        assert.containsNone(
            document.querySelector(".o_activity_view thead tr :nth-child(4)"),
            ".progress-bar-animated",
            "the progress bar of the Call for Demo activity type should not be animated"
        );
        assert.strictEqual(
            document.querySelector(".o_activity_view tbody .o_activity_record").textContent,
            "Meeting Room Furnitures",
            "'Office planning' should be first record"
        );
        const tr = document.querySelectorAll(".o_activity_view tbody tr")[1];
        assert.hasClass(
            tr.querySelectorAll("td")[1],
            "o_activity_empty_cell",
            "other records should be hidden"
        );
        assert.containsNone(
            document.querySelector(".o_activity_view tbody"),
            "planned",
            "other records should be hidden"
        );
    });

    QUnit.test("Activity view: hide/show columns", async function (assert) {
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });

        let expectedColumns = ["Email", "Call", "Call for Demo", "To Do"];
        for (const [index, column] of expectedColumns.entries()) {
            assert.strictEqual(
                document.querySelectorAll(".o_activity_view th div span:first-child")[index]
                    .textContent,
                column,
                "The column names should match"
            );
        }

        assert.containsOnce(
            document.body,
            "th:last-child button.dropdown-toggle",
            "The last column is the column selector"
        );

        await click(document.querySelector("th:last-child button.dropdown-toggle"));

        await click(document.body, "input[name='Email']");
        expectedColumns = ["Call", "Call for Demo", "To Do"];
        for (const [index, column] of expectedColumns.entries()) {
            assert.strictEqual(
                document.querySelectorAll(".o_activity_view th div span:first-child")[index]
                    .textContent,
                column,
                "The column names should match"
            );
        }

        await click(document.body, "input[name='Call for Demo']");
        expectedColumns = ["Call", "To Do"];
        for (const [index, column] of expectedColumns.entries()) {
            assert.strictEqual(
                document.querySelectorAll(".o_activity_view th div span:first-child")[index]
                    .textContent,
                column,
                "The column names should match"
            );
        }

        await click(document.body, "input[name='Email']");
        expectedColumns = ["Email", "Call", "To Do"];
        for (const [index, column] of expectedColumns.entries()) {
            assert.strictEqual(
                document.querySelectorAll(".o_activity_view th div span:first-child")[index]
                    .textContent,
                column,
                "The column names should match"
            );
        }
    });

    QUnit.test("Activity view: luxon in renderingContext", async function (assert) {
        Object.assign(serverData.views, {
            "mail.test.activity,false,activity": `
                    <activity string="MailTestActivity">
                        <templates>
                            <div t-name="activity-box">
                                <t t-if="luxon">
                                    <span class="luxon">luxon</span>
                                </t>
                            </div>
                        </templates>
                    </activity>`,
        });
        const { openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        await contains(".luxon", { count: 2 });
    });

    QUnit.test("test displaying image (write_date field)", async (assert) => {
        // the presence of write_date field ensures that the image is reloaded when necessary
        assert.expect(2);

        Object.assign(serverData.views, {
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

        const { target, openView } = await start({
            serverData,
            mockRPC(route, { method, kwargs }, result) {
                if (method === "web_search_read") {
                    assert.deepEqual(Object.keys(kwargs.specification), ["write_date", "id"]);
                    return Promise.resolve({
                        length: 2,
                        records: [
                            { id: 1, write_date: "2022-08-05 08:37:00" },
                            { id: 2, write_date: "2022-08-05 08:37:00" },
                        ],
                    });
                }
            },
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });

        assert.ok(
            target
                .querySelector(".o_activity_record img")
                .dataset.src.endsWith(
                    "/web/image?model=partner&field=image&id=2&unique=1659688620000"
                ),
            "image src is the preview image given in option"
        );
    });

    QUnit.test("test node is visible with invisible attribute on node", async function (assert) {
        const { target, openView } = await start({
            serverData,
        });
        await openView({
            res_model: "mail.test.activity",
            views: [[1, "activity"]],
        });

        assert.containsN(
            target,
            ".invisible_node",
            2,
            "The node with the invisible attribute should be displayed since the context does not have `invisible` key or has falsy value"
        );
    });

    QUnit.test(
        "test node is not displayed with invisible attribute on node",
        async function (assert) {
            const { target, openView } = await start({
                serverData,
            });
            await openView({
                res_model: "mail.test.activity",
                views: [[1, "activity"]],
                context: { invisible: true },
            });

            assert.containsNone(
                target,
                ".invisible_node",
                "The node with the invisible attribute should be displayed since `invisible` key in the context contains truly value"
            );
        }
    );
});
