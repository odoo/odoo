/* @odoo-module */

import { contains, start, startServer } from "@mail/../tests/helpers/test_utils";
import {
    click,
    patchWithCleanup,
    triggerHotkey,
    triggerEvent,
    getNodesTextContent,
} from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { nextTick } from "@web/../tests/legacy/helpers/test_utils";
import { popoverService } from "@web/core/popover/popover_service";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { browser } from "@web/core/browser/browser";
import { EventBus } from "@odoo/owl";

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

QUnit.test("many2many_avatar_user in kanban view", async (assert) => {
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
    await contains(".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty");
    assert.strictEqual(
        $(
            ".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty"
        )[0].innerText.trim(),
        "+2"
    );
    await click(
        document.querySelector(
            ".o_kanban_record .o_field_many2many_avatar_user .o_m2m_avatar_empty"
        )
    );
    const tags = document.querySelectorAll(".o_popover > .o_field_tags > .o_tag");
    assert.strictEqual(tags.length, 4);
    assert.strictEqual(tags[0].innerText.trim(), "Tapu");
    assert.strictEqual(tags[1].innerText.trim(), "Luigi");
    assert.strictEqual(tags[2].innerText.trim(), "Yoshi");
    assert.strictEqual(tags[3].innerText.trim(), "Mario");
});

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to..."',
    async (assert) => {
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
        await contains(".o_field_many2one_avatar_user input", 1, { value: "Mario" });

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...document.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign to ...ALT + I");
        assert.ok(idx >= 0);

        await click([...document.querySelectorAll(".o_command")][idx]);
        await nextTick();
        assert.deepEqual(
            [...document.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["Your Company, Mitchell Admin", "Public user", "Mario", "Luigi", "Yoshi"]
        );
        await click(document.body, "#o_command_3");
        await nextTick();
        await contains(".o_field_many2one_avatar_user input", 1, { value: "Luigi" });
    }
);

QUnit.test(
    'many2one_avatar_user widget edited by the smart action "Assign to me"',
    async (assert) => {
        const pyEnv = await startServer();
        const [userId_1, userId_2] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Luigi" },
        ]);
        const avatarUserId_1 = pyEnv["m2x.avatar.user"].create({ user_id: userId_1 });
        patchWithCleanup(session, { uid: userId_2, name: "Luigi" });
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
        await contains(".o_field_many2one_avatar_user input", 1, { value: "Mario" });
        triggerHotkey("control+k");
        await nextTick();
        const idx = [...document.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign/Unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i");
        await nextTick();
        await contains(".o_field_many2one_avatar_user input", 1, { value: "Luigi" });

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...document.querySelectorAll(".o_command")][idx]);
        await nextTick();
        await contains(".o_field_many2one_avatar_user input", 1, { value: "" });
    }
);

QUnit.test(
    'many2many_avatar_user widget edited by the smart action "Assign to..."',
    async (assert) => {
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
        let userNames = [...document.querySelectorAll(".o_tag_badge_text")].map(
            (el) => el.textContent
        );
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...document.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign to ...ALT + I");
        assert.ok(idx >= 0);

        await click([...document.querySelectorAll(".o_command")][idx]);
        await nextTick();
        assert.deepEqual(
            [...document.querySelectorAll(".o_command")].map((el) => el.textContent),
            ["Your Company, Mitchell Admin", "Public user", "Luigi"]
        );

        await click(document.body, "#o_command_2");
        await nextTick();
        userNames = [...document.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Luigi"]);
    }
);

QUnit.test(
    'many2many_avatar_user widget edited by the smart action "Assign to me"',
    async (assert) => {
        const pyEnv = await startServer();
        const [userId_1, userId_2] = pyEnv["res.users"].create([
            { name: "Mario" },
            { name: "Yoshi" },
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
        let userNames = [...document.querySelectorAll(".o_tag_badge_text")].map(
            (el) => el.textContent
        );
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...document.querySelectorAll(".o_command")]
            .map((el) => el.textContent)
            .indexOf("Assign/Unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me
        triggerHotkey("alt+shift+i");
        await nextTick();
        userNames = [...document.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Your Company, Mitchell Admin"]);

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...document.querySelectorAll(".o_command")][idx]);
        await nextTick();
        userNames = [...document.querySelectorAll(".o_tag_badge_text")].map((el) => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);
    }
);

QUnit.test(
    "avatar_user widget displays the appropriate user image in list view",
    async (assert) => {
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
        assert.strictEqual(
            $(".o_m2o_avatar > img")[0].getAttribute("data-src"),
            `/web/image/res.users/${userId}/avatar_128`
        );
    }
);

QUnit.test(
    "avatar_user widget displays the appropriate user image in kanban view",
    async (assert) => {
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
        assert.strictEqual(
            $(".o_m2o_avatar > img")[0].getAttribute("data-src"),
            `/web/image/res.users/${userId}/avatar_128`
        );
    }
);

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
            assert.deepEqual(args.args[1], ["name", "email", "phone", "im_status"]);
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
    await triggerEvent(document, ".o_m2o_avatar > img", "mouseover");
    assert.verifySteps(["setTimeout of 350ms", "setTimeout of 250ms", "user read"]);
    await contains(".o_avatar_card");
    assert.deepEqual(getNodesTextContent(document.querySelectorAll(".o_card_user_infos > *")), [
        "Mario",
        " Mario@odoo.test",
        " +78786987",
    ]);
    // Close card
    await triggerEvent(document, ".o_control_panel", "mouseover");
    assert.verifySteps(["setTimeout of 400ms"]);
    await contains(".o_avatar_card", 0);
});

QUnit.test(
    "avatar_user widget displays the appropriate user image in form view",
    async (assert) => {
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
        assert.strictEqual(
            document.body
                .querySelector(".o_field_many2many_avatar_user.o_field_widget .o_avatar img")
                .getAttribute("data-src"),
            `/web/image/res.users/${userId}/avatar_128`
        );
    }
);

QUnit.test("many2one_avatar_user widget in list view", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({ name: "Mario", partner_id: partnerId });
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
    await click(document.body, ".o_data_cell .o_m2o_avatar > img");
    await contains(".o-mail-ChatWindow");
    assert.strictEqual($(".o-mail-ChatWindow-name").text(), "Partner 1");
});

QUnit.test("many2many_avatar_user widget in form view", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Partner 1" });
    const userId = pyEnv["res.users"].create({ name: "Mario", partner_id: partnerId });
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
    await click(document.body, ".o_field_many2many_avatar_user .o_avatar img");
    await contains(".o-mail-ChatWindow");
    assert.strictEqual($(".o-mail-ChatWindow-name").text(), "Partner 1");
});
