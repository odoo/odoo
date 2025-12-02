import {
    click,
    contains,
    defineMailModels,
    openFormView,
    openKanbanView,
    openListView,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
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
    expect(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty").toHaveText("+2");
    await click(".o_kanban_record .o_field_many2many_avatar_user .o_quick_assign");
    await contains(".o_popover > .o_field_tags > .o_tag", { count: 4 });
    await contains(".o_popover > .o_field_tags > :nth-child(1 of .o_tag)", { text: "Tapu" });
    await contains(".o_popover > .o_field_tags > :nth-child(2 of .o_tag)", { text: "Luigi" });
    await contains(".o_popover > .o_field_tags > :nth-child(3 of .o_tag)", { text: "Yoshi" });
    await contains(".o_popover > .o_field_tags > :nth-child(4 of .o_tag)", { text: "Mario" });
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
    await contains(".o_field_many2one_avatar_user .o_external_button");
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await click(".o_command", { text: "Assign to ...ALT + I" });
    await contains(".o_command", { count: 6 });
    await contains(":nth-child(1 of .o_command)", { text: "Mitchell Admin" });
    await contains(":nth-child(2 of .o_command)", { text: "Public user" });
    await contains(":nth-child(3 of .o_command)", { text: "OdooBot" });
    await contains(":nth-child(4 of .o_command)", { text: "Mario" });
    await contains(":nth-child(5 of .o_command)", { text: "Luigi" });
    await contains(":nth-child(6 of .o_command)", { text: "Yoshi" });
    await click(".o_command", { text: "Luigi" });
    await contains(".o_field_many2one_avatar_user input", { value: "Luigi" });
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
    await contains(".o_tag_badge_text", { count: 2 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to ...ALT + I" });
    // Assign Luigi
    triggerHotkey("alt+i");
    await contains(".o_command", { count: 4 });
    await contains(":nth-child(1 of .o_command)", { text: "Mitchell Admin" });
    await contains(":nth-child(2 of .o_command)", { text: "Public user" });
    await contains(":nth-child(3 of .o_command)", { text: "OdooBot" });
    await contains(":nth-child(4 of .o_command)", { text: "Luigi" });
    await click(".o_command", { text: "Luigi" });
    await contains(".o_tag_badge_text", { count: 3 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    await contains(":nth-child(3 of .o_tag) .o_tag_badge_text", { text: "Luigi" });
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
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    await triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });
    await triggerHotkey("alt+shift+i");
    await contains(".o_field_many2one_avatar_user input", { value: "Mitchell Admin" });
    // Unassign me
    await triggerHotkey("control+k");
    await click(".o_command", { text: "Unassign from meALT + SHIFT + I" });
    await contains(".o_field_many2one_avatar_user input", { value: "" });
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
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });
    // Assign to me
    triggerHotkey("alt+shift+i");
    await contains(".o_field_many2one_avatar_user input", { value: "Mitchell Admin" });
    // Unassign from me
    triggerHotkey("control+k");
    await click(".o_command", { text: "Unassign from meALT + SHIFT + I" });
    await contains(".o_field_many2one_avatar_user input", { value: "" });
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
    await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Luigi",
    });
    await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Mario",
    });
    // Select all
    await click(".o_list_table > thead .o_list_controller input");
    await triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });
    // Assign me
    await triggerHotkey("alt+shift+i");
    // Multi-edit confirmation dialog
    await contains(".o_dialog");
    // Cancel
    await click(".o_dialog .modal-footer button:nth-child(2)");
    await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Luigi",
    });
    await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Mario",
    });
    // Assign me
    await triggerHotkey("alt+shift+i");
    // Multi-edit confirmation dialog
    await contains(".o_dialog");
    // Confirm
    await click(".o_dialog .modal-footer button:nth-child(1)");
    await contains(".o_dialog", { count: 0 });
    await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Mitchell Admin",
    });
    await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user .o_many2one", {
        text: "Mitchell Admin",
    });
    // Unassign me
    await triggerHotkey("alt+shift+u");
    // Multi-edit confirmation dialog
    await contains(".o_dialog");
    // Confirm
    await click(".o_dialog .modal-footer button:nth-child(1)");
    await contains(".o_field_many2one_avatar_user .o_form_uri", { count: 0 });
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
    await contains(".o_tag_badge_text", { count: 2 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });
    // Assign me
    triggerHotkey("alt+shift+i");
    await contains(".o_tag_badge_text", { count: 3 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    await contains(":nth-child(3 of .o_tag) .o_tag_badge_text", { text: "Mitchell Admin" });
    // Unassign me
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Unassign from meALT + SHIFT + I" });
    triggerHotkey("alt+shift+i");
    await contains(".o_tag_badge_text", { count: 2 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
});

test("avatar_user widget displays the appropriate user image in list view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    await start();
    await openListView("m2x.avatar.user", {
        res_id: avatarUserId,
        arch: "<list><field name='user_id' widget='many2one_avatar_user'/></list>",
    });

    await contains(`.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128"]`);
});

test("avatar_user widget displays the appropriate user image in kanban view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
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
    await start();
    await contains(`.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128"]`);
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
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+78786987" });
    // Close card
    await click(".o_action_manager");
    await contains(".o_avatar_card", { count: 0 });
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
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+78786987" });
    // Close card
    await click(".o_action_manager");
    await contains(".o_avatar_card", { count: 0 });
});

test("avatar_user widget displays the appropriate user image in form view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        partner_id: pyEnv["res.partner"].create({ name: "Mario" }),
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId, {
        arch: "<form><field name='user_ids' widget='many2many_avatar_user'/></form>",
    });
    await contains(
        `.o_field_many2many_avatar_user.o_field_widget .o_avatar img[data-src="${getOrigin()}/web/image/res.users/${userId}/avatar_128"]`
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
    await contains(".o_data_cell .o_many2one span");
    await contains(".o_data_cell .o_many2one a", { count: 0 });
    await click(".o_data_cell .o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
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
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});
