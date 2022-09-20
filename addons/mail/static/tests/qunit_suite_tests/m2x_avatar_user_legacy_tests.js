/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';
import { click, getFixture, legacyExtraNextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { registry } from "@web/core/registry";
import { makeLegacyCommandService } from "@web/legacy/utils";
import core from 'web.core';
import session from 'web.session';
import makeTestEnvironment from "web.test_env";
import { dom, nextTick } from 'web.test_utils';

let target;

QUnit.module('mail', {}, function () {
    QUnit.module('M2XAvatarUserLegacy', {
        beforeEach() {
            target = getFixture();
        },
    });

    QUnit.test('many2many_avatar_user widget in form view', async function (assert) {
        assert.expect(2);

        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv['res.partner'].create({ display_name: 'Partner 1' });
        const resUsersId1 = pyEnv['res.users'].create({ name: "Mario", partner_id: resPartnerId1 });
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_ids: [resUsersId1] });
        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_ids" widget="many2many_avatar_user"/></form>',
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'm2x.avatar.user',
            res_id: m2xAvatarUserId1,
            views: [[false, 'form']],
        });

        await dom.click(document.querySelector('.o_field_many2manytags.avatar .badge .o_m2m_avatar'));
        assert.containsOnce(document.body, '.o_ChatWindow', 'Chat window should be opened');
        assert.strictEqual(
            document.querySelector('.o_ChatWindowHeader_name').textContent,
            'Partner 1',
            'First chat window should be related to partner 1'
        );
    });

    QUnit.test('many2one_avatar_user widget edited by the smart action "Assign to..."', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const [resUsersId1] = pyEnv['res.users'].create(
            [{ name: "Mario" }, { name: "Luigi" }, { name: "Yoshi" }],
        );
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_id: resUsersId1 });
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_id" widget="many2one_avatar_user"/></form>',
        };
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_id: m2xAvatarUserId1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'm2x.avatar.user',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        assert.strictEqual(target.querySelector(".o_m2o_avatar > span").textContent, "Mario")

        triggerHotkey("control+k")
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign to ...ALT + I")
        assert.ok(idx >= 0);

        await click([...target.querySelectorAll(".o_command")][idx])
        await nextTick();
        assert.deepEqual([...target.querySelectorAll(".o_command")].map(el => el.textContent), [
            "Your Company, Mitchell Admin",
            "Public user",
            "Mario",
            "Luigi",
            "Yoshi",
          ])
        await click(target, "#o_command_3")
        await legacyExtraNextTick();
        assert.strictEqual(target.querySelector(".o_m2o_avatar > span").textContent, "Luigi")
    });

    QUnit.test('many2one_avatar_user widget edited by the smart action "Assign to me"', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2] = pyEnv['res.users'].create([{ name: "Mario" }, { name: "Luigi" }]);
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_id: resUsersId1 });
        patchWithCleanup(session, { user_id: [resUsersId2] });
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_id" widget="many2one_avatar_user"/></form>',
        };
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_id: m2xAvatarUserId1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'm2x.avatar.user',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        assert.strictEqual(target.querySelector(".o_m2o_avatar > span").textContent, "Mario")
        triggerHotkey("control+k")
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign/unassign to meALT + SHIFT + I")
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i")
        await legacyExtraNextTick();
        assert.strictEqual(target.querySelector(".o_m2o_avatar > span").textContent, "Luigi")

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...target.querySelectorAll(".o_command")][idx])
        await legacyExtraNextTick();
        assert.strictEqual(target.querySelector(".o_m2o_avatar > span").textContent, "")
    });

    QUnit.test('many2many_avatar_user widget edited by the smart action "Assign to..."', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2] = pyEnv['res.users'].create(
            [{ name: "Mario" }, { name: "Yoshi" }, { name: "Luigi" }],
        );
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_ids: [resUsersId1, resUsersId2] });
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_ids" widget="many2many_avatar_user"/></form>',
        };
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_id: m2xAvatarUserId1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'm2x.avatar.user',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        let userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k")
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign to ...ALT + I")
        assert.ok(idx >= 0);

        await click([...target.querySelectorAll(".o_command")][idx])
        await nextTick();
        assert.deepEqual([...target.querySelectorAll(".o_command")].map(el => el.textContent), [
            "Your Company, Mitchell Admin",
            "Public user",
            "Luigi"
          ]);

        await click(target, "#o_command_2");
        await legacyExtraNextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map(el => el.textContent);
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Luigi"]);
    });

    QUnit.test('many2many_avatar_user widget edited by the smart action "Assign to me"', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const [resUsersId1, resUsersId2, resUsersId3] = pyEnv['res.users'].create(
            [{ name: "Mario" }, { name: "Luigi" }, { name: "Yoshi" }],
        );
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_ids: [resUsersId1, resUsersId3] });
        patchWithCleanup(session, { user_id: [resUsersId2] });
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_ids" widget="many2many_avatar_user"/></form>',
        };
        const { openView } = await start({ serverData: { views } });
        await openView({
            res_id: m2xAvatarUserId1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'm2x.avatar.user',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        let userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...target.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign/unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i");
        await legacyExtraNextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Luigi"]);

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...target.querySelectorAll(".o_command")][idx]);
        await legacyExtraNextTick();
        userNames = [...target.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);
    });

    QUnit.test('avatar_user widget displays the appropriate user image in form view', async function (assert) {
        assert.expect(1);

        const pyEnv = await startServer();
        const resUsersId1 = pyEnv['res.users'].create({ name: "Mario" });
        const m2xAvatarUserId1 = pyEnv['m2x.avatar.user'].create({ user_ids: [resUsersId1] });
        const views = {
            'm2x.avatar.user,false,form': '<form js_class="legacy_form"><field name="user_ids" widget="many2many_avatar_user"/></form>',
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'm2x.avatar.user',
            res_id: m2xAvatarUserId1,
            views: [[false, 'form']],
        });
        assert.strictEqual(
            document.querySelector('.o_field_many2manytags.avatar.o_field_widget .badge img').getAttribute('data-src'),
            `/web/image/res.users/${resUsersId1}/avatar_128`,
            'Should have correct avatar image'
        );
    });
});
