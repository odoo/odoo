/** @odoo-module alias=@mail/../tests/web/fields/m2x_avatar_user_tests default=false */
const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { EventBus } from "@odoo/owl";

import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, step } from "@web/../tests/utils";
import { getOrigin } from "@web/core/utils/urls";

const fakeMultiTab = {
    start() {
        const bus = new EventBus();
        return {
            bus,
            get currentTabId() {
                return null;
            },
            isOnMainTab() {
                return true;
            },
            getSharedValue(key, defaultValue) {
                return "";
            },
            setSharedValue(key, value) {},
            removeSharedValue(key) {},
        };
    },
};

const fakeImStatusService = {
    start() {
        return {
            registerToImStatus() {},
            unregisterFromImStatus() {},
        };
    },
};

QUnit.module("M2XAvatarUser");

test("many2many_avatar_user in kanban view", async () => {
    const pyEnv = await startServer();
    const userIds = pyEnv["res.users"].create([
        { name: "Mario" },
        { name: "Yoshi" },
        { name: "Luigi" },
        { name: "Tapu" },
    ]);
    pyEnv["m2x.avatar.user"].create({ user_ids: userIds });
    registry.category("services").add("popover", popoverService);
    registry.category("services").add("tooltip", tooltipService);
    const views = {
        "m2x.avatar.user,false,kanban": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="user_id"/>
                        <field name="user_ids" widget="many2many_avatar_user"/>
                    </t>
                </templates>
            </kanban>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        views: [[false, "kanban"]],
    });
    await click(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty", {
        text: "+2",
    });
    await click(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty");
    await contains(".o_popover > .o_field_tags > .o_tag", { count: 4 });
    await contains(".o_popover > .o_field_tags > :nth-child(1 of .o_tag)", { text: "Tapu" });
    await contains(".o_popover > .o_field_tags > :nth-child(2 of .o_tag)", { text: "Luigi" });
    await contains(".o_popover > .o_field_tags > :nth-child(3 of .o_tag)", { text: "Yoshi" });
    await contains(".o_popover > .o_field_tags > :nth-child(4 of .o_tag)", { text: "Mario" });
});

test('many2one_avatar_user widget edited by the smart action "Assign to..."', async () => {
    const pyEnv = await startServer();
    const [userId_1] = pyEnv["res.users"].create([
        { name: "Mario" },
        { name: "Luigi" },
        { name: "Yoshi" },
    ]);
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", avatarUserId_1);
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await click(".o_command", { text: "Assign to ...ALT + I" });
    await contains(".o_command", { count: 6 });
    await contains(":nth-child(1 of .o_command)", { text: "OdooBot" });
    await contains(":nth-child(2 of .o_command)", { text: "Your Company, Mitchell Admin" });
    await contains(":nth-child(3 of .o_command)", { text: "Public user" });
    await contains(":nth-child(4 of .o_command)", { text: "Mario" });
    await contains(":nth-child(5 of .o_command)", { text: "Luigi" });
    await contains(":nth-child(6 of .o_command)", { text: "Yoshi" });
    await click(".o_command", { text: "Luigi" });
    await contains(".o_field_many2one_avatar_user input", { value: "Luigi" });
});

test('many2one_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const userId_1 = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", avatarUserId_1);
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });
    // Assign me
    triggerHotkey("alt+shift+i");
    await contains(".o_field_many2one_avatar_user input", {
        value: "Mitchell Admin", // should be "Mitchell Admin" but session is not sync with currentUser
    });
    // Unassign me
    triggerHotkey("control+k");
    await click(".o_command", { text: "Unassign from meALT + SHIFT + I" });
    await contains(".o_field_many2one_avatar_user input", { value: "" });
});

test('many2many_avatar_user widget edited by the smart action "Assign to..."', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { name: "Mario" },
        { name: "Yoshi" },
        { name: "Luigi" },
    ]);
    const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
        user_ids: [userId_1, userId_2],
    });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", m2xAvatarUserId1);
    await contains(".o_tag_badge_text", { count: 2 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to ...ALT + I" });
    triggerHotkey("alt+i");
    await contains(".o_command", { count: 4 });
    await contains(":nth-child(1 of .o_command)", { text: "OdooBot" });
    await contains(":nth-child(2 of .o_command)", { text: "Your Company, Mitchell Admin" });
    await contains(":nth-child(3 of.o_command)", { text: "Public user" });
    await contains(":nth-child(4 of.o_command)", { text: "Luigi" });
    await click(".o_command", { text: "Luigi" });
    await contains(".o_tag_badge_text", { count: 3 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    await contains(":nth-child(3 of .o_tag) .o_tag_badge_text", { text: "Luigi" });
});

test('many2one_avatar_user widget edited by the smart action "Assign to me" in form view', async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { name: "Mario", partner_id: partnerId_1 },
        { name: "Luigi", partner_id: partnerId_2 },
    ]);
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
    };
    await pyEnv.withUser(userId_2, async () => {
        await start({ serverData: { views } });
        await openFormView("m2x.avatar.user", avatarUserId_1);
        await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
        await triggerHotkey("control+k");
        await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });

        // Assign me (Luigi)
        await triggerHotkey("alt+shift+i");
        await contains(".o_field_many2one_avatar_user input", { value: "Luigi" });

        // Unassign me
        await triggerHotkey("control+k");
        await click(".o_command", { text: "Unassign from meALT + SHIFT + I" });
        await contains(".o_field_many2one_avatar_user input", { value: "" });
    });
});

test('many2one_avatar_user widget edited by the smart action "Assign to me" in list view', async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    const [userId_1, userId_2] = pyEnv["res.users"].create([
        { name: "Mario", partner_id: partnerId_1 },
        { name: "Luigi", partner_id: partnerId_2 },
    ]);
    pyEnv["m2x.avatar.user"].create([{ user_id: userId_2 }, { user_id: userId_1 }]);
    const views = {
        "m2x.avatar.user,false,list":
            '<list multi_edit="1"><field name="user_id" widget="many2one_avatar_user"/></list>',
    };
    await pyEnv.withUser(userId_2, async () => {
        const { openView } = await start({ serverData: { views } });
        await openView({
            type: "ir.actions.act_window",
            target: "current",
            res_model: "m2x.avatar.user",
            view_mode: "list",
            views: [[false, "list"]],
        });
        await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Luigi",
        });
        await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Mario",
        });
        // Select all
        await click(".o_list_table > thead .o_list_controller input");
        await triggerHotkey("control+k");
        await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });

        // Assign me (Luigi)
        await triggerHotkey("alt+shift+i");
        // Multi-edit confirmation dialog
        await contains(".o_dialog");
        // Cancel
        await click(".o_dialog .modal-footer button:nth-child(2)");
        await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Luigi",
        });
        await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Mario",
        });

        // Assign me (Luigi)
        await triggerHotkey("alt+shift+i");
        // Multi-edit confirmation dialog
        await contains(".o_dialog");
        // Confirm
        await click(".o_dialog .modal-footer button:nth-child(1)");
        await contains(".o_dialog", { count: 0 });
        await contains(":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Luigi",
        });
        await contains(":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span", {
            text: "Luigi",
        });

        // Unassign me (Luigi)
        await triggerHotkey("alt+shift+u");
        // Multi-edit confirmation dialog
        await contains(".o_dialog");
        // Confirm
        await click(".o_dialog .modal-footer button:nth-child(1)");
        await contains(".o_field_many2one_avatar_user .o_form_uri span", { count: 0 });
    });
});

test('many2many_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([{ name: "Mario" }, { name: "Yoshi" }]);
    const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
        user_ids: [userId_1, userId_2],
    });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", m2xAvatarUserId1);
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
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,list":
            '<list><field name="user_id" widget="many2one_avatar_user"/></list>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "list"]],
    });
    await contains(`.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128"]`);
});

test("avatar_user widget displays the appropriate user image in kanban view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="user_id" widget="many2one_avatar_user"/>
                        </t>
                    </templates>
                </kanban>`,
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "kanban"]],
    });
    await contains(`.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128"]`);
});

test("avatar card preview", async (assert) => {
    registry.category("services").add("multi_tab", fakeMultiTab, { force: true });
    registry.category("services").add("im_status", fakeImStatusService, { force: true });
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({
        name: "Mario",
        email: "Mario@odoo.test",
        phone: "+78786987",
        im_status: "online",
    });
    const mockRPC = (route, args) => {
        if (route === "/web/dataset/call_kw/res.users/read") {
            assert.deepEqual(args.args[1], [
                "name",
                "email",
                "phone",
                "im_status",
                "share",
                "partner_id",
            ]);
            step("user read");
        }
    };
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="user_id" widget="many2one_avatar_user"/>
                        </t>
                    </templates>
                </kanban>`,
    };
    const { openView } = await start({ serverData: { views }, mockRPC });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "kanban"]],
    });

    // Open card
    await click(".o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+78786987" });
    await assertSteps(["user read"]);
    // Close card
    await click(".o_action_manager");
    await contains(".o_avatar_card", { count: 0 });
});

test("avatar_user widget displays the appropriate user image in form view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", avatarUserId);
    await contains(
        `.o_field_many2many_avatar_user.o_field_widget .o_avatar img[data-src="${getOrigin()}/web/image/res.users/${userId}/avatar_128"]`
    );
});

test("many2one_avatar_user widget in list view", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({
        name: "Mario",
        partner_id: partnerId,
        email: "Mario@partner.com",
        phone: "+45687468",
    });
    pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,list":
            '<list><field name="user_id" widget="many2one_avatar_user"/></list>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        views: [[false, "list"]],
    });
    await click(".o_data_cell .o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});

test("many2many_avatar_user widget in form view", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({
        name: "Mario",
        partner_id: partnerId,
        email: "Mario@partner.com",
        phone: "+45687468",
    });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    const views = {
        "m2x.avatar.user,false,form": `
            <form>
                <field name="user_ids" widget="many2many_avatar_user"/>
            </form>`,
    };
    await start({ serverData: { views } });
    await openFormView("m2x.avatar.user", avatarUserId);
    await click(".o_field_many2many_avatar_user .o_avatar img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});
