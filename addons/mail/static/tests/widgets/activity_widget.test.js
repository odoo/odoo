import {
    click,
    contains,
    defineMailModels,
    listenStoreFetch,
    openListView,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { Deferred, tick } from "@odoo/hoot-dom";
import {
    asyncStep,
    onRpc,
    patchWithCleanup,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { serializeDate } from "@web/core/l10n/dates";

defineMailModels();
describe.current.tags("desktop");

test("list activity widget with no activity", async () => {
    onRpc("res.users", "web_search_read", ({ kwargs }) => {
        expect(kwargs).toMatchObject({
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
            context: { bin_size: true },
            count_limit: 10001,
            domain: [],
        });
        asyncStep("web_search_read");
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openListView("res.users", {
        arch: `<list><field name="activity_ids" widget="list_activity"/></list>`,
    });
    await waitForSteps(["web_search_read"]);
    await contains(".o-mail-ActivityButton i.fa-clock-o");
    await contains(".o-mail-ListActivity-summary", { text: "" });
});

test("list activity widget with activities", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([
        { name: "Type 1", icon: "fa-phone" },
        { name: "Type 2" },
    ]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        { activity_type_id: activityTypeId_1, summary: "Call with Al" },
        { activity_type_id: activityTypeId_2 },
    ]);
    pyEnv["res.partner"].write([serverState.partnerId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
    });
    pyEnv["res.users"].write([serverState.userId], { activity_ids: [activityId_1, activityId_2] });
    pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({
            activity_ids: [activityId_2],
            activity_state: "planned",
        }),
    });
    await start();
    await openListView("res.users", {
        arch: "<list><field name='activity_ids' widget='list_activity'/></list>",
    });
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
    const activityId = pyEnv["mail.activity"].create({
        summary: "Call with Al",
        activity_type_id: pyEnv["mail.activity.type"].create({
            icon: "fa-warning",
        }),
    });
    pyEnv["res.partner"].write([serverState.partnerId], {
        activity_ids: [activityId],
        activity_state: "today",
        activity_exception_decoration: "warning",
        activity_exception_icon: "fa-warning",
    });
    pyEnv["res.users"].write([serverState.userId], { activity_ids: [activityId] });
    await start();
    await openListView("res.users", {
        arch: "<list><field name='activity_ids' widget='list_activity'/></list>",
    });
    await contains(".o-mail-ActivityButton i.text-warning.fa-warning");
    await contains(".o-mail-ListActivity-summary", { text: "Warning" });
});

test("list activity widget: open dropdown", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            summary: "Call with Al",
            date_deadline: serializeDate(luxon.DateTime.now()),
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_1,
        },
        {
            summary: "Meet FP",
            date_deadline: serializeDate(luxon.DateTime.now().plus({ days: 1 })),
            can_write: true,
            state: "planned",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
        },
    ]);
    pyEnv["res.partner"].write([serverState.partnerId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
        activity_type_id: activityTypeId_2,
    });
    pyEnv["res.users"].write([serverState.userId], {
        activity_type_id: activityTypeId_2,
    });
    onRpc("mail.activity", "activity_format", (params) => {
        expect(params.args).toEqual([[activityId_1, activityId_2]]);
        asyncStep("activity_format");
    });
    onRpc("mail.activity", "action_feedback", (params) => {
        pyEnv["res.partner"].write([serverState.partnerId], {
            activity_ids: [activityId_2],
            activity_state: "planned",
            activity_summary: "Meet FP",
            activity_type_id: activityTypeId_1,
        });
        pyEnv["res.users"].write([serverState.userId], {
            activity_type_id: activityTypeId_2,
        });
        expect(params.args).toEqual([[activityId_1]]);
        asyncStep("action_feedback");
    });
    await start();
    await openListView("res.users", {
        arch: "<list><field name='name'/><field name='activity_ids' widget='list_activity'/></list>",
    });
    await contains(".o-mail-ListActivity-summary", { text: "Call with Al" });
    await click(".o-mail-ActivityButton");
    await waitForSteps(["activity_format"]);
    await click(
        ":nth-child(1 of .o-mail-ActivityListPopoverItem) .o-mail-ActivityListPopoverItem-markAsDone"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await waitForSteps(["action_feedback"]);
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
    const env = await start();
    let scheduleWizardContext = null;
    let wizardOpened = new Deferred();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            if (action.res_model === "mail.activity.schedule") {
                scheduleWizardContext = action.context;
                asyncStep("do_action_activity");
                options.onClose();
                wizardOpened.resolve();
                return true;
            }
            return super.doAction(action);
        },
    });
    await openListView("res.partner", {
        arch: `
            <list>
                <field name="name"/>
                <field name="activity_ids" widget="list_activity"/>
            </list>
        `,
    });
    const marioRow = selectContaining(document.body, ".o_data_row", "Mario")[0];
    const matildeRow = selectContaining(document.body, ".o_data_row", "Matilde")[0];
    const alexanderRow = selectContaining(document.body, ".o_data_row", "Alexander")[0];
    expect(Boolean(marioRow)).toBe(true);
    expect(Boolean(matildeRow)).toBe(true);
    expect(Boolean(alexanderRow)).toBe(true);
    // Clicking on the clock of a partner without selection, open the wizard for that record only
    await click(".o-mail-ActivityButton", { target: matildeRow });
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    await tick();
    expect(scheduleWizardContext).toEqual({
        active_ids: [matildeId],
        active_id: matildeId,
        active_model: "res.partner",
    });
    await waitForSteps(["do_action_activity"]);
    // We select 2 among the 3 partners created above and click on the clock of one of them
    await click(".o_list_record_selector .o-checkbox", { target: matildeRow });
    await click(".o_list_record_selector .o-checkbox", { target: marioRow });
    await contains(".o_selection_box", { text: "2 selected" });
    await click(".o-mail-ActivityButton", { target: matildeRow });
    await contains(".o-mail-ActivityListPopover button", {
        text: "Schedule an activity on selected records",
    });
    await contains(".o-mail-ActivityListPopover button", {
        text: "Schedule an activity on selected records",
    });
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    expect(scheduleWizardContext).toEqual({
        active_ids: [matildeId, marioId],
        active_id: matildeId,
        active_model: "res.partner",
    });
    // But when clicking on the clock of one of the non-selected row, it applies to only that row
    wizardOpened = new Deferred();
    await click(".o-mail-ActivityButton", { target: alexanderRow });
    await contains(".o-mail-ActivityListPopover button", { text: "Schedule an activity" });
    await contains(
        ".o-mail-ActivityListPopover button:not(:contains('Schedule an activity on selected records'))"
    );
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    expect(scheduleWizardContext).toEqual({
        active_ids: [alexanderId],
        active_id: alexanderId,
        active_model: "res.partner",
    });
    // We now check that when clicking on the clock of the other selected row, it applies to both row
    wizardOpened = new Deferred();
    await click(".o-mail-ActivityButton", { target: marioRow });
    await contains(".o-mail-ActivityListPopover", {
        text: "Schedule an activity on selected records",
    });
    await contains(".o-mail-ActivityListPopover button", {
        text: "Schedule an activity on selected records",
    });
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    expect(scheduleWizardContext).toEqual({
        active_ids: [matildeId, marioId],
        active_id: matildeId,
        active_model: "res.partner",
    });
    await waitForSteps(["do_action_activity", "do_action_activity", "do_action_activity"]);
});

test("list activity exception widget with activity", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(luxon.DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_1,
        },
        {
            display_name: "An exception activity",
            date_deadline: serializeDate(luxon.DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
        },
    ]);

    pyEnv["res.partner"].write([serverState.partnerId], { activity_ids: [activityId_1] });
    pyEnv["res.users"].create({
        message_attachment_count: 3,
        display_name: "second partner",
        message_follower_ids: [],
        message_ids: [],
        partner_id: pyEnv["res.partner"].create({
            activity_ids: [activityId_2],
            activity_exception_decoration: "warning",
            activity_exception_icon: "fa-warning",
        }),
    });
    await start();
    await openListView("res.users", {
        arch: `
            <list>
                <field name="activity_exception_decoration" widget="activity_exception"/>
            </list>
        `,
    });
    await contains(".o_data_row", { count: 2 });
    await contains(":nth-child(1 of .o_data_row) .o_activity_exception_cell", {
        contains: [".o-mail-ActivityException", { count: 0 }],
    });
    await contains(":nth-child(2 of .o_data_row) .o_activity_exception_cell", {
        contains: [".o-mail-ActivityException"],
    });
});
