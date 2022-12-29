/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import {
    click,
    getFixture,
    mouseEnter,
    patchWithCleanup,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { nextTick } from "web.test_utils";
import { popoverService } from "@web/core/popover/popover_service";
import { tooltipService } from "@web/core/tooltip/tooltip_service";

let target;

QUnit.module("M2XAvatarUser", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("many2many_avatar_user in kanban view", async function (assert) {
    const pyEnv = await startServer();
    const resUsersIds = pyEnv["res.users"].create([
        { name: "Mario" },
        { name: "Yoshi" },
        { name: "Luigi" },
        { name: "Tapu" },
    ]);
    pyEnv["m2x.avatar.user"].create({ user_ids: resUsersIds });
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
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.user",
        views: [[false, "kanban"]],
    });

    assert.containsOnce(
        target,
        ".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty"
    );
    assert.strictEqual(
        target
            .querySelector(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty")
            .innerText.trim(),
        "+2"
    );

    await mouseEnter(target, ".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty");
    assert.containsOnce(target, ".popover");
    assert.strictEqual(target.querySelector(".popover .o-tooltip > div").innerText.trim(), "Luigi");
    assert.strictEqual(
        target.querySelectorAll(".popover .o-tooltip > div")[1].innerText.trim(),
        "Tapu"
    );
});

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to..."',
    async function (assert) {
        const pyEnv = await startServer();
        const [resUsersId1] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Luigi" },
            { name: "Yoshi" },
        ]);
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_id: resUsersId1 });
        const views = {
            "m2x.avatar.user,false,form":
                '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
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
        assert.strictEqual(
            target.querySelector(".o_field_many2one_avatar_user input").value,
            "Mario"
        );

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign to ...ALT + I");
        assert.ok(idx >= 0);

        await click([...target.querySelectorAll(".o_command")][idx]);
        await nextTick();
        assert.deepEqual(
            [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["Your Company, Mitchell Admin", "Public user", "Mario", "Luigi", "Yoshi"]
        );
        await click(target, "#o_command_3");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_field_many2one_avatar_user input").value,
            "Luigi"
        );
    }
);

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to me"',
    async function (assert) {
        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Luigi" },
        ]);
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_id: resUsersId1 });
        patchWithCleanup(session, { uid: resUsersId2, name: "Luigi" });

        const views = {
            "m2x.avatar.user,false,form":
                '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
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
        assert.strictEqual(
            target.querySelector(".o_field_many2one_avatar_user input").value,
            "Mario"
        );
        triggerHotkey("control+k");
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign/Unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i");
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_field_many2one_avatar_user input").value,
            "Luigi"
        );

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...target.querySelectorAll(".o_command")][idx]);
        await nextTick();
        assert.strictEqual(target.querySelector(".o_field_many2one_avatar_user input").value, "");
    }
);

QUnit.test(
    'many2many_avatar_user widget edited by the smart action "Assign to..."',
    async function (assert) {
        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Yoshi" },
            { name: "Luigi" },
        ]);
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
            user_ids: [resUsersId1, resUsersId2],
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
        let userNames = [...target.querySelectorAll(".o_tag_badge_text")].map(
            (el) => el.textContent
        );
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign to ...ALT + I");
        assert.ok(idx >= 0);

        await click([...target.querySelectorAll(".o_command")][idx]);
        await nextTick();
        assert.deepEqual(
            [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["Your Company, Mitchell Admin", "Public user", "Luigi"]
        );

        await click(target, "#o_command_2");
        await nextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Luigi"]);
    }
);

QUnit.test(
    'many2many_avatar_user widget edited by the smart action "Assign to me"',
    async function (assert) {
        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Yoshi" },
        ]);
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({
            user_ids: [resUsersId1, resUsersId2],
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
        let userNames = [...target.querySelectorAll(".o_tag_badge_text")].map(
            (el) => el.textContent
        );
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign/Unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me
        triggerHotkey("alt+shift+i");
        await nextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Your Company, Mitchell Admin"]);

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...target.querySelectorAll(".o_command")][idx]);
        await nextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);
    }
);

QUnit.test(
    "avatar_user widget displays the appropriate user image in list view",
    async function (assert) {
        const pyEnv = await startServer();
        const resUsersId1 = pyEnv["res.users"].create({ name: "Mario" });
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_id: resUsersId1 });
        const views = {
            "m2x.avatar.user,false,list":
                '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "m2x.avatar.user",
            res_id: m2xAvatarUserId1,
            views: [[false, "list"]],
        });
        assert.strictEqual(
            target.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
            `/web/image/res.users/${resUsersId1}/avatar_128`
        );
    }
);

QUnit.test(
    "avatar_user widget displays the appropriate user image in kanban view",
    async function (assert) {
        const pyEnv = await startServer();
        const resUsersId1 = pyEnv["res.users"].create({ name: "Mario" });
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_id: resUsersId1 });
        const views = {
            "m2x.avatar.user,false,kanban": `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="user_id" widget="many2one_avatar_user"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "m2x.avatar.user",
            res_id: m2xAvatarUserId1,
            views: [[false, "kanban"]],
        });
        assert.strictEqual(
            target.querySelector(".o_m2o_avatar > img").getAttribute("data-src"),
            `/web/image/res.users/${resUsersId1}/avatar_128`
        );
    }
);

QUnit.test(
    "avatar_user widget displays the appropriate user image in form view",
    async function (assert) {
        const pyEnv = await startServer();
        const resUsersId1 = pyEnv["res.users"].create({ name: "Mario" });
        const m2xAvatarUserId1 = pyEnv["m2x.avatar.user"].create({ user_ids: [resUsersId1] });
        const views = {
            "m2x.avatar.user,false,form":
                '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: "m2x.avatar.user",
            res_id: m2xAvatarUserId1,
            views: [[false, "form"]],
        });
        assert.strictEqual(
            target
                .querySelector(".o_field_many2many_avatar_user.o_field_widget .badge img")
                .getAttribute("data-src"),
            `/web/image/res.users/${resUsersId1}/avatar_128`
        );
    }
);

QUnit.test("many2one_avatar_user widget in list view", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({ name: "Mario", partner_id: partnerId });
    pyEnv["m2x.avatar.user"].create({ user_id: userId });
    const views = {
        "m2x.avatar.user,false,list":
            '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: "m2x.avatar.user",
        views: [[false, "list"]],
    });
    await click(target, ".o_data_cell .o_m2o_avatar > img");
    assert.containsOnce(target, ".o-mail-chat-window");
    assert.strictEqual(
        target.querySelector(".o-mail-chat-window-header-name").textContent,
        "Partner 1"
    );
});

QUnit.test("many2many_avatar_user widget in form view", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({ name: "Mario", partner_id: partnerId });
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
    await click(target, ".o_field_many2many_avatar_user .badge .o_m2m_avatar");
    assert.containsOnce(target, ".o-mail-chat-window");
    assert.strictEqual(
        document.querySelector(".o-mail-chat-window-header-name").textContent,
        "Partner 1"
    );
});
