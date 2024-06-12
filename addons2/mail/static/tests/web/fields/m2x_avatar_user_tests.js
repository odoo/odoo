/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { EventBus } from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

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

QUnit.test("many2many_avatar_user in kanban view", async () => {
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
                    <t t-name="kanban-box">
                        <div>
                            <field name="user_id"/>
                            <div class="oe_kanban_footer">
                                <div class="o_kanban_record_bottom">
                                    <div class="oe_kanban_bottom_right">
                                        <field name="user_ids" widget="many2many_avatar_user"/>
                                    </div>
                                </div>
                            </div>
                        </div>
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

QUnit.test('many2one_avatar_user widget edited by the smart action "Assign to..."', async () => {
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
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_id: avatarUserId_1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "m2x.avatar.user",
        view_mode: "form",
        views: [[false, "form"]],
    });
    await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
    triggerHotkey("control+k");
    await click(".o_command", { text: "Assign to ...ALT + I" });
    await contains(".o_command", { count: 5 });
    await contains(":nth-child(1 of .o_command)", { text: "Your Company, Mitchell Admin" });
    await contains(":nth-child(2 of .o_command)", { text: "Public user" });
    await contains(":nth-child(3 of .o_command)", { text: "Mario" });
    await contains(":nth-child(4 of .o_command)", { text: "Luigi" });
    await contains(":nth-child(5 of .o_command)", { text: "Yoshi" });
    await click("#o_command_3");
    await contains(".o_field_many2one_avatar_user input", { value: "Luigi" });
});

QUnit.test('many2one_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const userId_1 = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_id: avatarUserId_1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "m2x.avatar.user",
        view_mode: "form",
        views: [[false, "form"]],
    });
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

QUnit.test('many2many_avatar_user widget edited by the smart action "Assign to..."', async () => {
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
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_id: m2xAvatarUserId1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "m2x.avatar.user",
        view_mode: "form",
        views: [[false, "form"]],
    });
    await contains(".o_tag_badge_text", { count: 2 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    triggerHotkey("control+k");
    await contains(".o_command", { text: "Assign to ...ALT + I" });
    triggerHotkey("alt+i");
    await contains(".o_command", { count: 3 });
    await contains(":nth-child(1 of .o_command)", { text: "Your Company, Mitchell Admin" });
    await contains(":nth-child(2 of.o_command)", { text: "Public user" });
    await contains(":nth-child(3 of.o_command)", { text: "Luigi" });
    await click("#o_command_2");
    await contains(".o_tag_badge_text", { count: 3 });
    await contains(":nth-child(1 of .o_tag) .o_tag_badge_text", { text: "Mario" });
    await contains(":nth-child(2 of .o_tag) .o_tag_badge_text", { text: "Yoshi" });
    await contains(":nth-child(3 of .o_tag) .o_tag_badge_text", { text: "Luigi" });
});

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to me" in form view',
    async (assert) => {
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
            const { openView } = await start({ serverData: { views } });
            await openView({
                res_id: avatarUserId_1,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "m2x.avatar.user",
                view_mode: "form",
                views: [[false, "form"]],
            });
            await contains(".o_field_many2one_avatar_user input", { value: "Mario" });
            await triggerHotkey("control+k");
            await contains(".o_command", { text: "Assign to meALT + SHIFT + I" });

            // Assign me (Luigi)
            await triggerHotkey("alt+shift+i");
            await contains(".o_field_many2one_avatar_user input", { value: "Luigi" });

            // Unassign me
            await triggerHotkey("control+k");
            await click("#o_command_2");
            await contains(".o_field_many2one_avatar_user input", { value: "" });
        });
    }
);

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to me" in list view',
    async (assert) => {
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
                '<tree multi_edit="1"><field name="user_id" widget="many2one_avatar_user"/></tree>',
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
            await contains(
                ":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Luigi" }
            );
            await contains(
                ":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Mario" }
            );
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
            await contains(
                ":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Luigi" }
            );
            await contains(
                ":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Mario" }
            );

            // Assign me (Luigi)
            await triggerHotkey("alt+shift+i");
            // Multi-edit confirmation dialog
            await contains(".o_dialog");
            // Confirm
            await click(".o_dialog .modal-footer button:nth-child(1)");
            await contains(".o_dialog", { count: 0 });
            await contains(
                ":nth-child(1 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Luigi" }
            );
            await contains(
                ":nth-child(2 of .o_data_row) .o_field_many2one_avatar_user span > span",
                { text: "Luigi" }
            );

            // Select all
            await click(".o_list_table > thead .o_list_controller input");

            // Unassign me (Luigi)
            await triggerHotkey("alt+shift+u");
            // Multi-edit confirmation dialog
            await contains(".o_dialog");
            // Confirm
            await click(".o_dialog .modal-footer button:nth-child(1)");
            await contains(".o_field_many2one_avatar_user .o_form_uri span", { count: 0 });
        });
    }
);

QUnit.test('many2many_avatar_user widget edited by the smart action "Assign to me"', async () => {
    const pyEnv = await startServer();
    const [userId_1, userId_2] = pyEnv["res.users"].create([{ name: "Mario" }, { name: "Yoshi" }]);
    const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
        user_ids: [userId_1, userId_2],
    });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_id: m2xAvatarUserId1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "m2x.avatar.user",
        view_mode: "form",
        views: [[false, "form"]],
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

QUnit.test("avatar_user widget displays the appropriate user image in list view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,list":
            '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
    };
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "list"]],
    });
    await contains(`.o_m2o_avatar > img[data-src="/web/image/res.users/${userId}/avatar_128"]`);
});

QUnit.test("avatar_user widget displays the appropriate user image in kanban view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="user_id" widget="many2one_avatar_user"/>
                            </div>
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

QUnit.test("avatar card preview", async (assert) => {
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
            assert.deepEqual(args.args[1], ["name", "email", "phone", "im_status", "share"]);
            assert.step("user read");
        }
    };
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="user_id" widget="many2one_avatar_user"/>
                            </div>
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

    patchWithCleanup(browser, {
        setTimeout: (callback, delay) => {
            assert.step(`setTimeout of ${delay}ms`);
            callback();
        },
    });
    // Open card
    await click(".o_m2o_avatar > img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@odoo.test" });
    await contains(".o_card_user_infos > a", { text: "+78786987" });
    assert.verifySteps(["setTimeout of 250ms", "user read"]);
    // Close card
    await click(".o_action_manager");
    await contains(".o_avatar_card", { count: 0 });
});

QUnit.test("avatar_user widget displays the appropriate user image in form view", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Mario" });
    const avatarUserId = pyEnv["m2x.avatar.user"].create({ user_ids: [userId] });
    const views = {
        "m2x.avatar.user,false,form":
            '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "form"]],
    });
    await contains(
        `.o_field_many2many_avatar_user.o_field_widget .o_avatar img[data-src="/web/image/res.users/${userId}/avatar_128"]`
    );
});

QUnit.test("many2one_avatar_user widget in list view", async () => {
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
            '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
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

QUnit.test("many2many_avatar_user widget in form view", async () => {
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
    const { openView } = await start({ serverData: { views } });
    await openView({
        res_model: "m2x.avatar.user",
        res_id: avatarUserId,
        views: [[false, "form"]],
    });
    await click(".o_field_many2many_avatar_user .o_avatar img");
    await contains(".o_avatar_card");
    await contains(".o_card_user_infos > span", { text: "Mario" });
    await contains(".o_card_user_infos > a", { text: "Mario@partner.com" });
    await contains(".o_card_user_infos > a", { text: "+45687468" });
});
