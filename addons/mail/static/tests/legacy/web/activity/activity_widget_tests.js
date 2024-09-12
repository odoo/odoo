/** @odoo-module alias=@mail/../tests/web/activity/activity_widget_tests default=false */
const test = QUnit.test; // QUnit.test()

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { ROUTES_TO_IGNORE } from "@mail/../tests/helpers/webclient_setup";

import { serializeDate } from "@web/core/l10n/dates";
import { ListController } from "@web/views/list/list_controller";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, step } from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("activity widget");

test("list activity widget with no activity", async () => {
    await startServer();
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
                !["/bus/im_status", ...ROUTES_TO_IGNORE].includes(route)
            ) {
                step(`${route} - ${JSON.stringify(args)}`);
            }
        },
        serverData: { views },
        session: { uid: serverState.userId },
    });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    await assertSteps([
        `/web/dataset/call_kw/res.users/web_search_read - ${JSON.stringify({
            model: "res.users",
            method: "web_search_read",
            args: [],
            kwargs: {
                specification: {
                    activity_ids: { fields: {} },
                    activity_exception_decoration: {},
                    activity_exception_icon: {},
                    activity_state: {},
                    activity_summary: {},
                    activity_type_icon: {},
                    activity_type_id: { fields: { display_name: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: { lang: "en", tz: "taht", uid: serverState.userId, bin_size: true },
                count_limit: 10001,
                domain: [],
            },
        })}`,
    ]);
    await contains(".o-mail-ActivityButton i.text-muted");
    await contains(".o-mail-ListActivity-summary", { text: "" });
});

test("list activity widget with activities", async () => {
    const pyEnv = await startServer();
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([{}, {}]);
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([
        { name: "Type 1" },
        { name: "Type 2" },
    ]);
    pyEnv["res.users"].write([serverState.userId], {
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
                !["/bus/im_status", ...ROUTES_TO_IGNORE].includes(route)
            ) {
                step(`${route} - ${JSON.stringify(args)}`);
            }
        },
        serverData: { views },
    });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    await assertSteps([
        `/web/dataset/call_kw/res.users/web_search_read - ${JSON.stringify({
            model: "res.users",
            method: "web_search_read",
            args: [],
            kwargs: {
                specification: {
                    activity_ids: { fields: {} },
                    activity_exception_decoration: {},
                    activity_exception_icon: {},
                    activity_state: {},
                    activity_summary: {},
                    activity_type_icon: {},
                    activity_type_id: { fields: { display_name: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: { lang: "en", tz: "taht", uid: serverState.userId, bin_size: true },
                count_limit: 10001,
                domain: [],
            },
        })}`,
    ]);
    await contains(":nth-child(1 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-warning.fa-phone"],
            [".o-mail-ListActivity-summary", { text: "Call with Al" }],
        ],
    });
    await contains(":nth-child(2 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-success.fa-tasks"],
            [".o-mail-ListActivity-summary", { text: "Type 2" }],
        ],
    });
});

test("list activity widget with exception", async () => {
    const pyEnv = await startServer();
    const activityId = pyEnv["mail.activity"].create({});
    const activityTypeId = pyEnv["mail.activity.type"].create({});
    pyEnv["res.users"].write([serverState.userId], {
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
                !["/bus/im_status", ...ROUTES_TO_IGNORE].includes(route)
            ) {
                step(`${route} - ${JSON.stringify(args)}`);
            }
        },
        serverData: { views },
    });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    await assertSteps([
        `/web/dataset/call_kw/res.users/web_search_read - ${JSON.stringify({
            model: "res.users",
            method: "web_search_read",
            args: [],
            kwargs: {
                specification: {
                    activity_ids: { fields: {} },
                    activity_exception_decoration: {},
                    activity_exception_icon: {},
                    activity_state: {},
                    activity_summary: {},
                    activity_type_icon: {},
                    activity_type_id: { fields: { display_name: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: { lang: "en", tz: "taht", uid: serverState.userId, bin_size: true },
                count_limit: 10001,
                domain: [],
            },
        })}`,
    ]);
    await contains(".o-mail-ActivityButton i.text-warning.fa-warning");
    await contains(".o-mail-ListActivity-summary", { text: "Warning" });
});

test("list activity widget: open dropdown", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "Call with Al",
            date_deadline: serializeDate(DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "Meet FP",
            date_deadline: serializeDate(DateTime.now().plus({ days: 1 })), // tomorrow
            can_write: true,
            state: "planned",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
        },
    ]);
    pyEnv["res.users"].write([serverState.userId], {
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
                !["/mail/", "/bus/im_status", ...ROUTES_TO_IGNORE].includes(route)
            ) {
                step(`${route} - ${JSON.stringify(args)}`);
            }
            if (args.method === "action_feedback") {
                pyEnv["res.users"].write([serverState.userId], {
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
                step(`select_record ${JSON.stringify(args)}`);
                return selectRecord(...args);
            };
        },
    });
    await assertSteps([
        `/mail/data - ${JSON.stringify({
            init_messaging: {},
            failures: true,
            systray_get_activities: true,
            context: { lang: "en", tz: "taht", uid: serverState.userId },
        })}`,
    ]);
    await openView({
        res_model: "res.users",
        views: [[false, "list"]],
    });
    await assertSteps([
        `/web/dataset/call_kw/res.users/web_search_read - ${JSON.stringify({
            model: "res.users",
            method: "web_search_read",
            args: [],
            kwargs: {
                specification: {
                    activity_ids: { fields: {} },
                    activity_exception_decoration: {},
                    activity_exception_icon: {},
                    activity_state: {},
                    activity_summary: {},
                    activity_type_icon: {},
                    activity_type_id: { fields: { display_name: {} } },
                },
                offset: 0,
                order: "",
                limit: 80,
                context: { lang: "en", tz: "taht", uid: serverState.userId, bin_size: true },
                count_limit: 10001,
                domain: [],
            },
        })}`,
    ]);
    await contains(".o-mail-ListActivity-summary", { text: "Call with Al" });
    await click(".o-mail-ActivityButton");
    await assertSteps([
        `/web/dataset/call_kw/mail.activity/activity_format - ${JSON.stringify({
            model: "mail.activity",
            method: "activity_format",
            args: [[activityId_1, activityId_2]],
            kwargs: { context: { lang: "en", tz: "taht", uid: serverState.userId } },
        })}`,
    ]);
    await click(
        ":nth-child(1 of .o-mail-ActivityListPopoverItem) .o-mail-ActivityListPopoverItem-markAsDone"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await assertSteps([
        `/web/dataset/call_kw/mail.activity/action_feedback - ${JSON.stringify({
            model: "mail.activity",
            method: "action_feedback",
            args: [[activityId_1]],
            kwargs: {
                attachment_ids: [],
                context: { lang: "en", tz: "taht", uid: serverState.userId },
            },
        })}`,
        `/web/dataset/call_kw/res.users/web_read - ${JSON.stringify({
            model: "res.users",
            method: "web_read",
            args: [[activityId_2]],
            kwargs: {
                context: { lang: "en", tz: "taht", uid: serverState.userId, bin_size: true },
                specification: {
                    activity_ids: { fields: {} },
                    activity_exception_decoration: {},
                    activity_exception_icon: {},
                    activity_state: {},
                    activity_summary: {},
                    activity_type_icon: {},
                    activity_type_id: { fields: { display_name: {} } },
                },
            },
        })}`,
    ]);
    await contains(".o-mail-ListActivity-summary", { text: "Meet FP" });
});

test("list activity widget: batch selection from list", async (assert) => {
    function selectContaining(domElement, selector, containing) {
        return Array.from(domElement.querySelectorAll(selector)).filter((sel) =>
            sel.textContent.includes(containing)
        );
    }

    const pyEnv = await startServer();
    const [marioId, matildeId, alexanderId] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Matilde" },
        { name: "Alexander" },
    ]);
    const views = {
        "res.partner,false,list": `
            <list>
                <field name="name"/>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
    };
    const { env, openView } = await start({
        serverData: { views },
    });
    let scheduleWizardContext = null;
    let wizardOpened = makeDeferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            if (action.res_model === "mail.activity.schedule") {
                scheduleWizardContext = action.context;
                step("do_action_activity");
                options.onClose();
                wizardOpened.resolve();
                return true;
            }
            return super.doAction(action);
        },
    });
    await openView({
        res_model: "res.partner",
        views: [[false, "list"]],
    });
    const marioRow = selectContaining(document.body, ".o_data_row", "Mario")[0];
    const matildeRow = selectContaining(document.body, ".o_data_row", "Matilde")[0];
    const alexanderRow = selectContaining(document.body, ".o_data_row", "Alexander")[0];
    assert.ok(marioRow);
    assert.ok(matildeRow);
    assert.ok(alexanderRow);

    // Clicking on the clock of a partner without selection, open the wizard for that record only
    await click(".o-mail-ActivityButton", { target: matildeRow });
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    assert.deepEqual(scheduleWizardContext, {
        active_ids: [matildeId],
        active_id: matildeId,
        active_model: "res.partner",
    });

    // We select 2 among the 3 partners created above and click on the clock of one of them
    await click(".o_list_record_selector .o-checkbox", { target: matildeRow });
    await click(".o_list_record_selector .o-checkbox", { target: marioRow });
    await contains(".o_list_selection_box", { text: "2 selected" });
    await click(".o-mail-ActivityButton", { target: matildeRow });
    await contains(".o-mail-ActivityListPopover button", {
        text: "Schedule an activity on selected records",
    });
    assert.equal(
        document.body.querySelector(".o-mail-ActivityListPopover button").textContent,
        "Schedule an activity on selected records"
    );
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    assert.deepEqual(scheduleWizardContext, {
        active_ids: [marioId, matildeId],
        active_id: marioId,
        active_model: "res.partner",
    });
    // But when clicking on the clock of one of the non-selected row, it applies to only that row
    wizardOpened = makeDeferred();
    await click(".o-mail-ActivityButton", { target: alexanderRow });
    await contains(".o-mail-ActivityListPopover button", { text: "Schedule an activity" });
    // await contains(".o-mail-ActivityListPopover button:not(:contains('Schedule an activity on selected records'))");
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    assert.deepEqual(scheduleWizardContext, {
        active_ids: [alexanderId],
        active_id: alexanderId,
        active_model: "res.partner",
    });
    // We now check that when clicking on the clock of the other selected row, it applies to both row
    wizardOpened = makeDeferred();
    await click(".o-mail-ActivityButton", { target: marioRow });
    await contains(".o-mail-ActivityListPopover", {
        text: "Schedule an activity on selected records",
    });
    assert.equal(
        document.body.querySelector(".o-mail-ActivityListPopover button").textContent,
        "Schedule an activity on selected records"
    );
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    assert.deepEqual(scheduleWizardContext, {
        active_ids: [marioId, matildeId],
        active_id: marioId,
        active_model: "res.partner",
    });
    await assertSteps(Array(4).fill("do_action_activity"));
});

test("list activity exception widget with activity", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "An exception activity",
            date_deadline: serializeDate(DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
        },
    ]);

    pyEnv["res.users"].write([serverState.userId], { activity_ids: [activityId_1] });
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
            <list>
                <field name="activity_exception_decoration" widget="activity_exception"/>
            </list>
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
