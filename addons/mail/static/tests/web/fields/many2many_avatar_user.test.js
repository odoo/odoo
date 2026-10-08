import {
    click,
    contains as mailContains,
    defineMailModels,
    openFormView,
    openKanbanView,
    openListView,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { registry } from "@web/core/registry";
import { getOrigin } from "@web/core/utils/urls";

defineMailModels();
describe.current.tags("desktop");

test("many2many_avatar_user in kanban view", async () => {
    const pyEnv = await startServer();
    const userIds = pyEnv["res.users"].create([
        { partner_id: pyEnv["res.partner"].create({ name: "Mario" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Yoshi" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Luigi" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Tapu" }) },
    ]);
    pyEnv["m2x.avatar.user"].create({ user_ids: userIds });
    await start();
    await openKanbanView("m2x.avatar.user", {
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="user_id"/>
                        <field name="user_ids" widget="many2many_avatar_user"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    expect(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty").toHaveText("+3");
    await click(".o_kanban_record .o_field_many2many_avatar_user .o_quick_assign");
    await waitFor(".o_popover > .o_field_tags > .o_tag:count(4)");
    await waitFor(".o_popover > .o_field_tags > .o_tag:eq(0):text('Mario'):count(1)");
    await waitFor(".o_popover > .o_field_tags > .o_tag:eq(1):text('Yoshi'):count(1)");
    await waitFor(".o_popover > .o_field_tags > .o_tag:eq(2):text('Luigi'):count(1)");
    await waitFor(".o_popover > .o_field_tags > .o_tag:eq(3):text('Tapu'):count(1)");
});

test('many2one_avatar_user widget edited by the smart action "Assign to..."', async () => {
    const pyEnv = await startServer();
    const [userId_1] = pyEnv["res.users"].create([
        { partner_id: pyEnv["res.partner"].create({ name: "Mario" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Luigi" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Yoshi" }) },
    ]);
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId_1, {
        arch: "<form><field name='user_id' widget='many2one_avatar_user'/></form>",
    });
    await waitFor(".o_field_many2one_avatar_user .o_external_button:count(1)");
    await mailContains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await click(".o_command:text('Assign to ... ALT + I')");
    await waitFor(".o_command:count(6)");
    await waitFor(".o_command:eq(0):text('Mitchell Admin'):count(1)");
    await waitFor(".o_command:eq(1):text('Public user'):count(1)");
    await waitFor(".o_command:eq(2):text('OdooBot'):count(1)");
    await waitFor(".o_command:eq(3):text('Mario'):count(1)");
    await waitFor(".o_command:eq(4):text('Luigi'):count(1)");
    await waitFor(".o_command:eq(5):text('Yoshi'):count(1)");
    await click(".o_command:text('Luigi')");
    await mailContains(".o_field_many2one_avatar_user input", { value: "Luigi" });
});

test('many2many_avatar_user widget edited by the smart action "Assign to..."', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: pyEnv["res.partner"].create({ name: "Mario" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Yoshi" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Luigi" }) },
    ]);
    const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_ids: [userId_1, userId_2] });
    await start();
    await openFormView("m2x.avatar.user", m2xAvatarUserId1, {
        arch: "<form><field name='user_ids' widget='many2many_avatar_user'/></form>",
    });
    await waitFor(".o_tag_badge_text:count(2)");
    await waitFor(".o_tag:eq(0) .o_tag_badge_text:text('Mario'):count(1)");
    await waitFor(".o_tag:eq(1) .o_tag_badge_text:text('Yoshi'):count(1)");
    triggerHotkey("control+k");
    await waitFor(".o_command:text('Assign to ... ALT + I'):count(1)");
    // Assign Luigi
    triggerHotkey("alt+i");
    await waitFor(".o_command:count(4)");
    await waitFor(".o_command:eq(0):text('Mitchell Admin'):count(1)");
    await waitFor(".o_command:eq(1):text('Public user'):count(1)");
    await waitFor(".o_command:eq(2):text('OdooBot'):count(1)");
    await waitFor(".o_command:eq(3):text('Luigi'):count(1)");
    await click(".o_command:text('Luigi')");
    await waitFor(".o_tag_badge_text:count(3)");
    await waitFor(".o_tag:eq(0) .o_tag_badge_text:text('Mario'):count(1)");
    await waitFor(".o_tag:eq(1) .o_tag_badge_text:text('Yoshi'):count(1)");
    await waitFor(".o_tag:eq(2) .o_tag_badge_text:text('Luigi'):count(1)");
});

test('many2one_avatar_user widget edited by the smart action "Assign to me" in form view', async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
    });
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId_1, {
        arch: "<form><field name='user_id' widget='many2one_avatar_user'/></form>",
    });
    await mailContains(".o_field_many2one_avatar_user input", { value: "Mario" });
    await triggerHotkey("control+k");
    await waitFor(".o_command:text('Assign to me ALT + SHIFT + I'):count(1)");
    await triggerHotkey("alt+shift+i");
    await mailContains(".o_field_many2one_avatar_user input", { value: "Mitchell Admin" });
    // Unassign me
    await triggerHotkey("control+k");
    await click(".o_command:text('Unassign from me ALT + SHIFT + I')");
    await mailContains(".o_field_many2one_avatar_user input", { value: "" });
});

test('many2one_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const userId_1 = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
    });
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId_1, {
        arch: "<form><field name='user_id' widget='many2one_avatar_user'/></form>",
    });
    await mailContains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await waitFor(".o_command:text('Assign to me ALT + SHIFT + I'):count(1)");
    // Assign to me
    triggerHotkey("alt+shift+i");
    await mailContains(".o_field_many2one_avatar_user input", { value: "Mitchell Admin" });
    // Unassign from me
    triggerHotkey("control+k");
    await click(".o_command:text('Unassign from me ALT + SHIFT + I')");
    await mailContains(".o_field_many2one_avatar_user input", { value: "" });
});

test('many2one_avatar_user widget edited by the smart action "Assign to me" in list view', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: pyEnv["res.partner"].create({ name: "Mario" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Luigi" }) },
    ]);

    pyEnv["m2x.avatar.user"].create([{ user_id: userId_2 }, { user_id: userId_1 }]);
    await start();
    await openListView("m2x.avatar.user", {
        arch: "<list multi_edit='1'><field name='user_id' widget='many2one_avatar_user'/></list>",
    });
    await waitFor(
        ".o_data_row:eq(0) .o_field_many2one_avatar_user .o_many2one:text('Luigi'):count(1)"
    );
    await waitFor(
        ".o_data_row:eq(1) .o_field_many2one_avatar_user .o_many2one:text('Mario'):count(1)"
    );
    // Select all
    await click(".o_list_table > thead .o_list_controller input");
    await triggerHotkey("control+k");
    await waitFor(".o_command:text('Assign to me ALT + SHIFT + I'):count(1)");
    // Assign me
    await triggerHotkey("alt+shift+i");
    // Multi-edit confirmation dialog
    await waitFor(".o_dialog:count(1)");
    // Cancel
    await click(".o_dialog .modal-footer button:eq(1)");
    await waitFor(
        ".o_data_row:eq(0) .o_field_many2one_avatar_user .o_many2one:text('Luigi'):count(1)"
    );
    await waitFor(
        ".o_data_row:eq(1) .o_field_many2one_avatar_user .o_many2one:text('Mario'):count(1)"
    );
    // Assign me
    await triggerHotkey("alt+shift+i");
    // Multi-edit confirmation dialog
    await waitFor(".o_dialog:count(1)");
    // Confirm
    await click(".o_dialog .modal-footer button:eq(0)");
    await waitForNone(".o_dialog");
    await waitFor(
        ".o_data_row:eq(0) .o_field_many2one_avatar_user .o_many2one:text('Mitchell Admin'):count(1)"
    );
    await waitFor(
        ".o_data_row:eq(1) .o_field_many2one_avatar_user .o_many2one:text('Mitchell Admin'):count(1)"
    );
    // Unassign me
    await triggerHotkey("alt+shift+u");
    // Multi-edit confirmation dialog
    await waitFor(".o_dialog:count(1)");
    // Confirm
    await click(".o_dialog .modal-footer button:eq(0)");
    await waitForNone(".o_field_many2one_avatar_user .o_form_uri");
});

test('many2many_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { partner_id: pyEnv["res.partner"].create({ name: "Mario" }) },
        { partner_id: pyEnv["res.partner"].create({ name: "Yoshi" }) },
    ]);
    const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
        user_ids: [userId_1, userId_2],
    });
    await start();
    await openFormView("m2x.avatar.user", m2xAvatarUserId1, {
        arch: "<form><field name='user_ids' widget='many2many_avatar_user'/></form>",
    });
    await waitFor(".o_tag_badge_text:count(2)");
    await waitFor(".o_tag:eq(0) .o_tag_badge_text:text('Mario'):count(1)");
    await waitFor(".o_tag:eq(1) .o_tag_badge_text:text('Yoshi'):count(1)");
    triggerHotkey("control+k");
    await waitFor(".o_command:text('Assign to me ALT + SHIFT + I'):count(1)");
    // Assign me
    triggerHotkey("alt+shift+i");
    await waitFor(".o_tag_badge_text:count(3)");
    await waitFor(".o_tag:eq(0) .o_tag_badge_text:text('Mario'):count(1)");
    await waitFor(".o_tag:eq(1) .o_tag_badge_text:text('Yoshi'):count(1)");
    await waitFor(".o_tag:eq(2) .o_tag_badge_text:text('Mitchell Admin'):count(1)");
    // Unassign me
    triggerHotkey("control+k");
    await waitFor(".o_command:text('Unassign from me ALT + SHIFT + I'):count(1)");
    triggerHotkey("alt+shift+i");
    await waitFor(".o_tag_badge_text:count(2)");
    await waitFor(".o_tag:eq(0) .o_tag_badge_text:text('Mario'):count(1)");
    await waitFor(".o_tag:eq(1) .o_tag_badge_text:text('Yoshi'):count(1)");
});

test("avatar_user widget displays the appropriate user image in list view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
        write_date: "2023-02-13 10:00:00",
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openListView("m2x.avatar.user", {
        res_id: avatarUserId,
        arch: "<list><field name='user_id' widget='many2one_avatar_user'/></list>",
    });

    await waitFor(
        `.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128?unique=1676282400000"]:count(1)`
    );
});

test("avatar_user widget displays the appropriate user image in kanban view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario", write_date: "2023-02-13 10:00:00" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openKanbanView("m2x.avatar.user", {
        res_id: avatarUserId,
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="user_id" widget="many2one_avatar_user"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    await waitFor(
        `.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128?unique=1676282400000"]:count(1)`
    );
});

test("avatar card preview", async () => {
    registry.category("services").add(
        "im_status",
        {
            start() {
                return {
                    registerToImStatus() {},
                    unregisterFromImStatus() {},
                    updateBusPresence() {},
                };
            },
        },
        { force: true }
    );
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({
            email: "Mario@odoo.test",
            name: "Mario",
            phone: "+78786987",
        }),
        im_status: "online",
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openKanbanView("m2x.avatar.user", {
        res_id: avatarUserId,
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="user_id" widget="many2one_avatar_user"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    // Open card
    await click(".o_m2o_avatar > img");
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('Mario'):count(1)");
    await waitFor(".o_card_user_infos > a:text('Mario@odoo.test'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+78786987'):count(1)");
    // Close card
    await click(".o_action_manager");
    await waitForNone(".o_avatar_card");
});

test("avatar card preview (partner_id field)", async () => {
    registry.category("services").add(
        "im_status",
        {
            start() {
                return {
                    registerToImStatus() {},
                    unregisterFromImStatus() {},
                    updateBusPresence() {},
                };
            },
        },
        { force: true }
    );
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        im_status: "online",
    });
    const partnerId = pyEnv["res.partner"].create({
        email: "Mario@odoo.test",
        name: "Mario",
        phone: "+78786987",
        user_ids: [userId],
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ partner_id: partnerId });
    await start();
    await openKanbanView("m2x.avatar.user", {
        res_id: avatarUserId,
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="partner_id" widget="many2one_avatar_user"/>
                    </t>
                </templates>
            </kanban>
        `,
    });
    // Open card
    await click(".o_m2o_avatar > img");
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('Mario'):count(1)");
    await waitFor(".o_card_user_infos > a:text('Mario@odoo.test'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+78786987'):count(1)");
    // Close card
    await click(".o_action_manager");
    await waitForNone(".o_avatar_card");
});

test("avatar_user widget displays the appropriate user image in form view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
        write_date: "2023-02-13 10:00:00",
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId, {
        arch: "<form><field name='user_ids' widget='many2many_avatar_user'/></form>",
    });
    await waitFor(
        `.o_field_many2many_avatar_user.o_field_widget .o_avatar img[data-src="${getOrigin()}/web/image/res.users/${userId}/avatar_128?unique=1676282400000"]:count(1)`
    );
});

test("many2one_avatar_user widget in list view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({
            email: "Mario@partner.com",
            name: "Mario",
            phone: "+45687468",
        }),
    });
    pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openListView("m2x.avatar.user", {
        arch: "<list><field name='user_id' widget='many2one_avatar_user'/></list>",
    });
    await waitFor(".o_data_cell .o_many2one span:count(1)");
    await waitForNone(".o_data_cell .o_many2one a");
    await click(".o_data_cell .o_m2o_avatar > img");
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('Mario'):count(1)");
    await waitFor(".o_card_user_infos > a:text('Mario@partner.com'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+45687468'):count(1)");
});

test("many2many_avatar_user widget in form view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        name: "Mario",
        partner_id: pyEnv["res.partner"].create({
            email: "Mario@partner.com",
            name: "Mario",
            phone: "+45687468",
        }),
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId, {
        arch: "<form><field name='user_ids' widget='many2many_avatar_user'/></form>",
    });
    await click(".o_field_many2many_avatar_user .o_avatar img");
    await waitFor(".o_avatar_card:count(1)");
    await waitFor(".o-mail-avatar-card-name:text('Mario'):count(1)");
    await waitFor(".o_card_user_infos > a:text('Mario@partner.com'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+45687468'):count(1)");
});
