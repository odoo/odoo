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
import { tick } from "@odoo/hoot-dom";
import { onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
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
        expect.step("web_search_read");
    });
    listenStoreFetch("init_messaging");
    await start();
    await waitStoreFetch("init_messaging");
    await openListView("res.users", {
        arch: `<list><field name="activity_ids" widget="list_activity"/></list>`,
    });
    await expect.waitForSteps(["web_search_read"]);
    await contains(".o-mail-ActivityButton i.fa-clock-o");
    await contains(".o-mail-ListActivity-summary", { textContent: "" });
});

test("list activity widget with activities", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([
        { name: "Type 1", icon: "fa-phone" },
        { name: "Type 2" },
    ]);
    const user2Id = pyEnv["res.users"].create({});
    const [activityId_1, activityId_2, activityId_3] = pyEnv["mail.activity"].create([
        {
            activity_type_id: activityTypeId_1,
            summary: "Call with Al",
            res_model: "res.users",
            res_id: serverState.userId,
        },
        {
            activity_type_id: activityTypeId_2,
            res_model: "res.users",
            res_id: serverState.userId,
        },
        {
            activity_type_id: activityTypeId_2,
            res_model: "res.users",
            res_id: user2Id,
        },
    ]);
    pyEnv["res.users"].write([serverState.userId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
    });
    pyEnv["res.users"].write([user2Id], {
        activity_ids: [activityId_3],
        activity_state: "planned",
    });
    pyEnv["res.users"]._applyComputesAndValidate();
    await start();
    await openListView("res.users", {
        arch: "<list><field name='activity_ids' widget='list_activity'/></list>",
    });
    await contains(":nth-child(1 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-warning.fa-phone"],
            [".o-mail-ListActivity-summary:text('Call with Al')"],
        ],
    });
    await contains(":nth-child(2 of .o_data_row)", {
        contains: [
            [".o-mail-ActivityButton i.text-success.fa-tasks"],
            [".o-mail-ListActivity-summary:text('Type 2')"],
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
        res_model: "res.users",
        res_id: serverState.userId,
    });
    pyEnv["res.users"].write([serverState.userId], {
        activity_ids: [activityId],
        activity_state: "today",
        activity_exception_decoration: "warning",
        activity_exception_icon: "fa-warning",
    });
    pyEnv["res.users"]._applyComputesAndValidate();
    await start();
    await openListView("res.users", {
        arch: "<list><field name='activity_ids' widget='list_activity'/></list>",
    });
    await contains(".o-mail-ActivityButton i.text-warning.fa-warning");
    await contains(".o-mail-ListActivity-summary:text('Warning')");
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
            res_model: "res.users",
            res_id: serverState.userId,
        },
        {
            summary: "Meet FP",
            date_deadline: serializeDate(luxon.DateTime.now().plus({ days: 1 })),
            can_write: true,
            state: "planned",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
            res_model: "res.users",
            res_id: serverState.userId,
        },
    ]);
    pyEnv["res.users"].write([serverState.userId], {
        activity_ids: [activityId_1, activityId_2],
        activity_state: "today",
        activity_type_id: activityTypeId_2,
    });
    pyEnv["res.users"]._applyComputesAndValidate();

    listenStoreFetch("mail.activity");
    onRpc("mail.activity", "action_feedback", (params) => {
        pyEnv["res.users"].write([serverState.userId], {
            activity_ids: [activityId_2],
            activity_state: "planned",
            activity_summary: "Meet FP",
            activity_type_id: activityTypeId_1,
        });
        expect(params.args).toEqual([[activityId_1]]);
        expect.step("action_feedback");
    });
    await start();
    await openListView("res.users", {
        arch: "<list><field name='name'/><field name='activity_ids' widget='list_activity'/></list>",
    });
    await contains(".o-mail-ListActivity-summary:text('Call with Al')");
    await click(".o-mail-ActivityButton");
    await waitStoreFetch("mail.activity");
    await click(
        ":nth-child(1 of .o-mail-ActivityListPopoverItem) .o-mail-ActivityListPopoverItem-markAsDone"
    );
    await click(".o-mail-ActivityMarkAsDone button[aria-label='Done']");
    await expect.waitForSteps(["action_feedback"]);
    await contains(".o-mail-ListActivity-summary:text('Meet FP')");
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
    let { promise: wizardOpened, resolve: resolveWizardOpened } = Promise.withResolvers();
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            if (action.res_model === "mail.activity.schedule") {
                scheduleWizardContext = action.context;
                expect.step("do_action_activity");
                options.onClose();
                resolveWizardOpened();
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
    await expect.waitForSteps(["do_action_activity"]);
    // We select 2 among the 3 partners created above and click on the clock of one of them
    await click(".o_list_record_selector .o-checkbox", { target: matildeRow });
    await click(".o_list_record_selector .o-checkbox", { target: marioRow });
    await contains(".o_selection_box:text('2 selected')");
    await click(".o-mail-ActivityButton", { target: matildeRow });
    await contains(
        ".o-mail-ActivityListPopover button:text('Schedule an activity on selected records')"
    );
    await contains(
        ".o-mail-ActivityListPopover button:text('Schedule an activity on selected records')"
    );
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    expect(scheduleWizardContext).toEqual({
        // res.partner is ordered "complete_name ASC" so Mario sorts before Matilde, and active_id
        // is the first selected record (resIds[0]).
        active_ids: [marioId, matildeId],
        active_id: marioId,
        active_model: "res.partner",
    });
    // But when clicking on the clock of one of the non-selected row, it applies to only that row
    ({ promise: wizardOpened, resolve: resolveWizardOpened } = Promise.withResolvers());
    await click(".o-mail-ActivityButton", { target: alexanderRow });
    await contains(".o-mail-ActivityListPopover button:text('Schedule an activity')");
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
    ({ promise: wizardOpened, resolve: resolveWizardOpened } = Promise.withResolvers());
    await click(".o-mail-ActivityButton", { target: marioRow });
    await contains(
        ".o-mail-ActivityListPopover button:text('Schedule an activity on selected records')"
    );
    await contains(
        ".o-mail-ActivityListPopover button:text('Schedule an activity on selected records')"
    );
    await click(".o-mail-ActivityListPopover button");
    await wizardOpened;
    expect(scheduleWizardContext).toEqual({
        // res.partner is ordered "complete_name ASC" so Mario sorts before Matilde, and active_id
        // is the first selected record (resIds[0]).
        active_ids: [marioId, matildeId],
        active_id: marioId,
        active_model: "res.partner",
    });
    await expect.waitForSteps(["do_action_activity", "do_action_activity", "do_action_activity"]);
});

test("list activity exception widget with activity", async () => {
    const pyEnv = await startServer();
    const [activityTypeId_1, activityTypeId_2] = pyEnv["mail.activity.type"].create([{}, {}]);
    const user2Id = pyEnv["res.users"].create({
        message_attachment_count: 3,
        display_name: "second user",
        message_follower_ids: [],
        message_ids: [],
    });
    const [activityId_1, activityId_2] = pyEnv["mail.activity"].create([
        {
            display_name: "An activity",
            date_deadline: serializeDate(luxon.DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_1,
            res_model: "res.users",
            res_id: serverState.userId,
        },
        {
            display_name: "An exception activity",
            date_deadline: serializeDate(luxon.DateTime.now()), // now
            can_write: true,
            state: "today",
            user_id: serverState.userId,
            create_uid: serverState.userId,
            activity_type_id: activityTypeId_2,
            res_model: "res.users",
            res_id: user2Id, // Target the second user
        },
    ]);
    pyEnv["res.users"].write([serverState.userId], {
        activity_ids: [activityId_1],
    });
    pyEnv["res.users"].write([user2Id], {
        activity_ids: [activityId_2],
        activity_exception_decoration: "warning",
        activity_exception_icon: "fa-warning",
    });
    pyEnv["res.users"]._applyComputesAndValidate();

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
