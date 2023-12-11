/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { ROUTES_TO_IGNORE } from "@mail/../tests/helpers/webclient_setup";

import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { ListController } from "@web/views/list/list_controller";

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
    assert.containsOnce($, ".o-mail-ActivityButton i.text-muted");
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "");
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
    assert.containsOnce($(".o_data_row:eq(0)"), ".o-mail-ActivityButton i.text-warning.fa-phone");
    assert.strictEqual(
        $(".o_data_row:eq(0) .o-mail-ListActivity-summary")[0].innerText,
        "Call with Al"
    );
    assert.containsOnce($(".o_data_row:eq(1)"), ".o-mail-ActivityButton i.text-success.fa-clock-o");
    assert.strictEqual($(".o_data_row:eq(1) .o-mail-ListActivity-summary")[0].innerText, "Type 2");
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget with activities, two pages, mark done", async function (assert) {
    patchDate(2023, 0, 11, 12, 0, 0);
    const pyEnv = await startServer();
    const mailActivityTypeId = pyEnv["mail.activity.type"].create({});
    const mailActivityId = pyEnv["mail.activity"].create({
        display_name: "Meet FP",
        date_deadline: moment().add(1, "day").format("YYYY-MM-DD"), // tomorrow
        can_write: true,
        state: "planned",
        user_id: pyEnv.currentUserId,
        create_uid: pyEnv.currentUserId,
        activity_type_id: mailActivityTypeId,
    });

    pyEnv["res.users"].create({ display_name: "User 1" });
    pyEnv["res.users"].create({ display_name: "User 2" });
    const userId = pyEnv["res.users"].create({
        display_name: "User 3",
        activity_ids: [mailActivityId],
        activity_state: "planned",
        activity_summary: "Something to do",
        activity_type_id: mailActivityTypeId,
    });
    pyEnv["mail.activity"].write([mailActivityId], { res_id: userId, res_model: "res.users" });
    const views = {
        "res.users,false,list": `
            <list limit="2">
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };

    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });

    assert.containsOnce(document.body, ".o_list_view");
    assert.strictEqual(document.querySelector(".o_cp_pager").innerText, "1-2 / 4");

    await click(document.querySelector(".o_pager_next"));
    assert.strictEqual(document.querySelector(".o_cp_pager").innerText, "3-4 / 4");
    assert.strictEqual(
        document.querySelectorAll(".o_data_row")[1].querySelector("[name=activity_ids]").innerText,
        "Something to do"
    );

    await click(document.querySelectorAll(".o-mail-ActivityButton")[1]); // open the popover
    await click(".o-mail-ActivityListPopoverItem-markAsDone"); // mark the first activity as done
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']"); // confirm
    assert.strictEqual(document.querySelector(".o_cp_pager").innerText, "3-4 / 4");
    assert.strictEqual(
        document.querySelectorAll(".o_data_row")[1].querySelector("[name=activity_ids]").innerText,
        ""
    );
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
    assert.containsOnce($, ".o-mail-ActivityButton i.text-warning.fa-warning");
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "Warning");
    assert.verifySteps(["/web/dataset/call_kw/res.users/web_search_read"]);
});

QUnit.test("list activity widget: open dropdown", async (assert) => {
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
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "Call with Al");

    await click(".o-mail-ActivityButton"); // open the popover
    await click(".o-mail-ActivityListPopoverItem-markAsDone"); // mark the first activity as done
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']"); // confirm
    assert.strictEqual($(".o-mail-ListActivity-summary")[0].innerText, "Meet FP");
    assert.verifySteps([
        "web_search_read",
        "activity_format",
        "action_feedback",
        "web_search_read",
    ]);
});

QUnit.test("list activity exception widget with activity", async (assert) => {
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
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    assert.containsN($, ".o_data_row", 2);
    assert.containsNone(
        $(".o_data_row .o_activity_exception_cell")[0],
        ".o-mail-ActivityException"
    );
    assert.containsOnce(
        $(".o_data_row .o_activity_exception_cell")[1],
        ".o-mail-ActivityException"
    );
});
