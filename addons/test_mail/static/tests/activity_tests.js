/** @odoo-module **/

import { ActivityModel } from "@mail/views/web/activity/activity_model";
import { ActivityRenderer } from "@mail/views/web/activity/activity_renderer";
import { start, startServer } from "@mail/../tests/helpers/test_utils";

import testUtils from "web.test_utils";

import {
    editInput,
    legacyExtraNextTick,
    patchWithCleanup,
    click,
    patchDate,
} from "@web/../tests/helpers/utils";
import { doAction } from "@web/../tests/webclient/helpers";
import { session } from "@web/session";
import { toggleSearchBarMenu } from "@web/../tests/search/helpers";

let serverData;
let pyEnv;

QUnit.module("test_mail", {}, function () {
    QUnit.module("activity view", {
        async beforeEach() {
            patchDate(2023, 4, 8, 10, 0, 0);
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
                    date_deadline: moment().add(3, "days").format("YYYY-MM-DD"), // now
                    can_write: true,
                    state: "planned",
                    activity_type_id: mailActivityTypeIds[0],
                    mail_template_ids: mailTemplateIds,
                    user_id: resUsersId1,
                },
                {
                    display_name: "An activity",
                    date_deadline: moment().format("YYYY-MM-DD"), // now
                    can_write: true,
                    state: "today",
                    activity_type_id: mailActivityTypeIds[0],
                    mail_template_ids: mailTemplateIds,
                    user_id: resUsersId1,
                },
                {
                    res_model: "mail.test.activity",
                    display_name: "An activity",
                    date_deadline: moment().subtract(2, "days").format("YYYY-MM-DD"), // now
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
                },
            };
        },
    });

    var activityDateFormat = function (date) {
        return date.toLocaleDateString(moment().locale(), { day: "numeric", month: "short" });
    };

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
        var $th1 = $activity.find("table thead tr:first th:nth-child(2)");
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
        var $th2 = $activity.find("table thead tr:first th:nth-child(3)");
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

        var today = activityDateFormat(new Date());

        assert.ok(
            $activity.find(
                "table tbody tr:first td:nth-child(2).today .o-mail-ActivityCell-deadline:contains(" +
                    today +
                    ")"
            ).length,
            "should contain an activity for today in second cell of first line " + today
        );
        var td = "table tbody tr:nth-child(1) td.o_activity_empty_cell";
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

    QUnit.test(
        "activity view: there is no default limit of 80 in the relationalModel",
        async function (assert) {
            const mailActivityTypeIds = pyEnv["mail.activity.type"].search([]);

            const recordsToCreate = [];
            const activityToCreate = [];

            for (let i = 0; i < 81; i++) {
                activityToCreate.push({
                    display_name: "An activity " + i,
                    date_deadline: moment().add(3, "days").format("YYYY-MM-DD"),
                    can_write: true,
                    state: "planned",
                    activity_type_id: mailActivityTypeIds[0],
                });
            }
            const createdActivity = pyEnv["mail.activity"].create(activityToCreate);
            for (let i = 0; i < 81; i++) {
                // The default limit of the RelationalModel is 80, test if it is overwrited by creating more than 80 records
                recordsToCreate.push({ name: i + "", activity_ids: [createdActivity[i]] });
            }
            pyEnv["mail.test.activity"].create(recordsToCreate);

            const { openView } = await start({
                serverData,
            });
            await openView({
                res_model: "mail.test.activity",
                views: [[false, "activity"]],
            });

            const activityRecords = document.querySelectorAll(".o_activity_record");
            // 81 test.activity records in tests
            // + 2 in global of all tests in this file
            // = 83 records
            assert.strictEqual(
                activityRecords.length,
                83,
                "The 83 records should have been loaded"
            );
        }
    );

    QUnit.test("activity view: no content rendering", async function (assert) {
        assert.expect(2);

        const { openView, pyEnv } = await start({
            serverData,
        });
        // reset incompatible setup
        pyEnv["mail.activity.type"].unlink(pyEnv["mail.activity.type"].search([]));
        await openView({
            res_model: "mail.test.activity",
            views: [[false, "activity"]],
        });
        const $activity = $(document);

        assert.containsOnce($activity, ".o_view_nocontent", "should display the no content helper");
        assert.strictEqual(
            $activity.find(".o_view_nocontent .o_view_nocontent_empty_folder").text().trim(),
            "No data to display",
            "should display the no content helper text"
        );
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
            JSON.stringify([["activity_ids", "!=", false]]),
            JSON.stringify([["activity_ids", "!=", false]]),
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
                } else if (action.res_model === "mail.activity") {
                    assert.deepEqual(
                        {
                            default_activity_type_id: mailActivityTypeIds[1],
                            default_res_id: mailTestActivityId2,
                            default_res_model: "mail.test.activity",
                        },
                        action.context
                    );
                    assert.step("do_action_activity");
                } else {
                    assert.step("Unexpected action");
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
                await this._super(params);
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
                    var expectedAction = {
                        context: {
                            default_res_id: mailTestActivityId1,
                            default_res_model: "mail.test.activity",
                        },
                        name: "Schedule Activity",
                        res_id: false,
                        res_model: "mail.activity",
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
            var $modal = $(".modal-lg");
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
        await legacyExtraNextTick();
        assert.containsOnce($, ".modal.o_technical_modal", "Activity Modal should be opened");

        await testUtils.dom.click($('.modal.o_technical_modal button[special="cancel"]'));
        await legacyExtraNextTick();
        assert.containsNone($, ".modal.o_technical_modal", "Activity Modal should be closed");
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

            await legacyExtraNextTick();
            assert.containsN(document.body, ".o_m2o_avatar", 2);
            assert.containsOnce(
                document.body,
                `tr:nth-child(2) .o_m2o_avatar > img[data-src="/web/image/res.users/${resUsersId1}/avatar_128"]`,
                "should have m2o avatar image"
            );
            assert.containsNone(
                document.body,
                ".o_m2o_avatar > span",
                "should not have text on many2one_avatar_user if onlyImage node option is passed"
            );
        }
    );

    QUnit.test("Activity view: on_destroy_callback doesn't crash", async function (assert) {
        assert.expect(3);

        patchWithCleanup(ActivityRenderer.prototype, {
            setup() {
                this._super();
                owl.onMounted(() => {
                    assert.step("mounted");
                });
                owl.onWillUnmount(() => {
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
                date_deadline: moment().add(3, "days").format("YYYY-MM-DD"), // now
                can_write: true,
                state: "planned",
                activity_type_id: mailActivityTypeIds[2],
                mail_template_ids: mailTemplateIds,
                user_id: resUsersId1,
            }
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
        assert.hasClass(target.querySelector(".o_activity_type_cell:nth-child(2) .bg-success"), "progress-bar-animated progress-bar-striped", "progress bar is animated with a strip effect");
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
        assert.containsN(document.body, ".luxon", 2);
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
                    assert.deepEqual(kwargs.fields, ["write_date", "id"]);
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
});
