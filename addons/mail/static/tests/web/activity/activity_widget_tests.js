/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { ROUTES_TO_IGNORE } from "@mail/../tests/helpers/webclient_setup";

import { serializeDate } from "@web/core/l10n/dates";
import { ListController } from "@web/views/list/list_controller";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("activity widget");

QUnit.test("list activity widget with no activity", async (assert) => {
    const pyEnv = await startServer();
    const views = {
        "res.users,false,list": `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({
        mockRPC(route, args) {
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
    await contains(".o-mail-ActivityButton i.text-muted");
    await contains(".o-mail-ListActivity-summary", { text: "" });
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget with activities", async (assert) => {
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
        "res.users,false,list": `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({
        mockRPC(route, args) {
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
    await contains(":nth-child(1 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-warning.fa-phone"],
            [".o-mail-ListActivity-summary", { text: "Call with Al" }],
        ],
    });
    await contains(":nth-child(2 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-success.fa-clock-o"],
            [".o-mail-ListActivity-summary", { text: "Type 2" }],
        ],
    });
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget with exception", async (assert) => {
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
        "res.users,false,list": `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({
        mockRPC(route, args) {
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
    await contains(".o-mail-ActivityButton i.text-warning.fa-warning");
    await contains(".o-mail-ListActivity-summary", { text: "Warning" });
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget: open dropdown", async (assert) => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "Call with Al",
            date_deadline: serializeDate(DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "Meet FP",
            date_deadline: serializeDate(DateTime.now().plus({ days: 1 })), // tomorrow
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
        "res.users,false,list": `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { openView } = await start({
        mockRPC(route, args) {
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
            super.setup();
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
    await contains(".o-mail-ListActivity-summary", { text: "Call with Al" });
    await click(".o-mail-ActivityButton");
    await click(
        ":nth-child(1 of .o-mail-ActivityListPopoverItem) .o-mail-ActivityListPopoverItem-markAsDone"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await contains(".o-mail-ListActivity-summary", { text: "Meet FP" });
    assert.verifySteps(["web_search_read", "activity_format", "action_feedback", "web_read"]);
});

QUnit.test("list activity exception widget with activity", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: pyEnv.currentUserId,
            create_uid: pyEnv.currentUserId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "An exception activity",
            date_deadline: serializeDate(DateTime.now()), // now
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
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    await contains(".o_data_row", { count: 2 });
    await contains(":nth-child(1 of .o_data_row) .o_activity_exception_cell", {
        contains: [".o-mail-ActivityException", { count: 0 }],
    });
    await contains(":nth-child(2 of .o_data_row) .o_activity_exception_cell", {
        contains: [".o-mail-ActivityException"],
    });
});
