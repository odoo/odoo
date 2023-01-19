/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { ROUTES_TO_IGNORE } from "@mail/../tests/helpers/webclient_setup";

import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { ListController } from "@web/views/list/list_controller";

let target;
QUnit.module("activity widget", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("list activity widget with no activity", async function (assert) {
    const pyEnv = await startServer();
    const views = {
        "res.users,false,list": '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== "get_views" &&
                ![
                    "/mail/init_messaging",
                    "/mail/load_message_failures",
                    "/bus/im_status",
                    ...ROUTES_TO_IGNORE,
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
        session: { uid: pyEnv.currentUserId },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.containsOnce(target, ".o-activity-button-icon.text-muted");
    assert.strictEqual(document.querySelector(".o-list-activity-summary").innerText, "");
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget with activities", async function (assert) {
    const pyEnv = await startServer();
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([{}, {}]);
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([
        { name: "Type 1" },
        { name: "Type 2" },
    ]);
    pyEnv["res.users"].write([pyEnv.currentUserId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
        activity_summary: "Call with Al",
        activity_type_id: activityTypeId_1,
        activity_type_icon: "fa-phone",
    });

    pyEnv["res.users"].create({
        activity_ids: [activityId_2],
        activity_state: "planned",
        activity_summary: false,
        activity_type_id: activityTypeId_2,
    });
    const views = {
        "res.users,false,list": '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== "get_views" &&
                ![
                    "/mail/init_messaging",
                    "/mail/load_message_failures",
                    "/bus/im_status",
                    ...ROUTES_TO_IGNORE,
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    const row_1 = document.querySelector(".o_data_row");
    assert.containsOnce(row_1, ".o-activity-button-icon.text-warning.fa-phone");
    assert.strictEqual(row_1.querySelector(".o-list-activity-summary").innerText, "Call with Al");
    const row_2 = document.querySelectorAll(".o_data_row")[1];
    assert.containsOnce(row_2, ".o-activity-button-icon.text-success.fa-clock-o");
    assert.strictEqual(row_2.querySelector(".o-list-activity-summary").innerText, "Type 2");
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget with exception", async function (assert) {
    const pyEnv = await startServer();
    const activityId = pyEnv["mail.activity"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].create({});
    pyEnv["res.users"].write([pyEnv.currentUserId], {
        activity_ids: [activityId],
        activity_state: "today",
        activity_summary: "Call with Al",
        activity_type_id: activityTypeId,
        activity_exception_decoration: "warning",
        activity_exception_icon: "fa-warning",
    });
    const views = {
        "res.users,false,list": '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== "get_views" &&
                ![
                    "/mail/init_messaging",
                    "/mail/load_message_failures",
                    "/bus/im_status",
                    ...ROUTES_TO_IGNORE,
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
        serverData: { views },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.containsOnce(target, ".o-activity-button-icon.text-warning.fa-warning");
    assert.strictEqual(document.querySelector(".o-list-activity-summary").innerText, "Warning");
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget: open dropdown", async function (assert) {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "Call with Al",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "Meet FP",
            date_deadline: moment().add(1, "day").format("YYYY-MM-DD"), // tomorrow
            can_write: true,
            state: "planned",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_2,
        },
    ]);
    pyEnv["res.users"].write([pyEnv.currentUserId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
        activity_summary: "Call with Al",
        activity_type_id: activityTypeId_2,
    });
    const views = {
        "res.users,false,list": '<list><field name="activity_ids" widget="list_activity"/></list>',
    };
    const { openView } = await start({
        mockRPC: function (route, args) {
            if (
                args.method !== "get_views" &&
                ![
                    "/mail/init_messaging",
                    "/mail/load_message_failures",
                    "/bus/im_status",
                    ...ROUTES_TO_IGNORE,
                ].includes(route)
            ) {
                assert.step(args.method || route);
            }
            if (args.method === "action_feedback") {
                pyEnv["res.users"].write([pyEnv.currentUserId], {
                    activity_ids: [activityId_2],
                    activity_state: "planned",
                    activity_summary: "Meet FP",
                    activity_type_id: activityTypeId_1,
                });
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
        },
        serverData: { views },
    });
    patchWithCleanup(ListController.prototype, {
        setup() {
            this._super();
            const selectRecord = this.props.selectRecord;
            this.props.selectRecord = (...args) => {
                assert.step(`select_record ${JSON.stringify(args)}`);
                return selectRecord(...args);
            };
        },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.strictEqual(
        document.querySelector(".o-list-activity-summary").innerText,
        "Call with Al"
    );

    await click(".o-activity-button"); // open the popover
    await click(".o-activity-list-popover-item-mark-as-done"); // mark the first activity as done
    await click(".o-mail-activity-mark-as-done-button-done"); // confirm
    assert.strictEqual(document.querySelector(".o-list-activity-summary").innerText, "Meet FP");
    assert.verifySteps([
        "web_search_read",
        "activity_format",
        "action_feedback",
        "web_search_read",
    ]);
});

QUnit.test("list activity exception widget with activity", async function (assert) {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "An exception activity",
            date_deadline: moment().format("YYYY-MM-DD"), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_2,
        },
    ]);

    pyEnv["res.users"].write([pyEnv.currentUserId], { activity_ids: [activityId_1] });
    pyEnv["res.users"].create({
        message_attachment_count: 3,
        display_name: "second partner",
        message_follower_ids: [],
        message_ids: [],
        activity_ids: [activityId_2],
        activity_exception_decoration: "warning",
        activity_exception_icon: "fa-warning",
    });
    const views = {
        "res.users,false,list": `
            <tree>
                <field name="activity_exception_decoration" widget="activity_exception"/>
            </tree>
        `,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.containsN(target, ".o_data_row", 2);
    assert.containsNone(
        document.querySelectorAll(".o_data_row .o_activity_exception_cell")[0],
        ".o_ActivityException"
    );
    assert.containsOnce(
        document.querySelectorAll(".o_data_row .o_activity_exception_cell")[1],
        ".o_ActivityException"
    );
});
