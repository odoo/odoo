/** @odoo-module **/

import { Many2OneAvatarUser } from '@mail/js/m2x_avatar_user';
import { afterEach, beforeEach, start } from '@mail/utils/test_utils';
import { click, getFixture, legacyExtraNextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { doAction } from '@web/../tests/webclient/helpers';
import { registry } from "@web/core/registry";
import { makeLegacyCommandService } from "@web/legacy/utils";
import core from 'web.core';
import FormView from 'web.FormView';
import KanbanView from 'web.KanbanView';
import ListView from 'web.ListView';
import session from 'web.session';
import makeTestEnvironment from "web.test_env";
import { dom, nextTick } from 'web.test_utils';

let target;

QUnit.module('mail', {}, function () {
    QUnit.module('M2XAvatarUser', {
        async beforeEach() {
            await beforeEach(this);

            // reset the cache before each test
            Many2OneAvatarUser.prototype.partnerIds = {};

            Object.assign(this.data, {
                'foo': {
                    fields: {
                        user_id: { string: "User", type: 'many2one', relation: 'res.users' },
                        user_ids: { string: "Users", type: "many2many", relation: 'res.users',  default:[] },
                    },
                    records: [
                        { id: 1, user_id: 11, user_ids: [11, 23], },
                        { id: 2, user_id: 7 },
                        { id: 3, user_id: 11 },
                        { id: 4, user_id: 23 },
                    ],
                },
            });

            this.data['res.partner'].records.push(
                { id: 11, display_name: "Partner 1" },
                { id: 12, display_name: "Partner 2" },
                { id: 13, display_name: "Partner 3" }
            );
            this.data['res.users'].records.push(
                { id: 11, name: "Mario", partner_id: 11 },
                { id: 7, name: "Luigi", partner_id: 12 },
                { id: 23, name: "Yoshi", partner_id: 13 }
            );

            target = getFixture();
        },
        afterEach() {
            afterEach(this);
        },
    });

    QUnit.test('many2one_avatar_user widget in list view', async function (assert) {
        assert.expect(2);

        const { widget: list } = await start({
            hasChatWindow: true,
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
        });

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar > img'));
        assert.containsOnce(document.body, '.o_ChatWindow', 'Chat window should be opened');
        assert.strictEqual(
            document.querySelector('.o_ChatWindowHeader_name').textContent,
            'Partner 1',
            'Chat window should be related to partner 1'
        );

        list.destroy();
    });

    QUnit.test('many2many_avatar_user widget in form view', async function (assert) {
        assert.expect(2);

        const { widget: form } = await start({
            hasChatWindow: true,
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
            res_id: 1,
        });

        await dom.click(form.$('.o_field_many2manytags.avatar .badge:first .o_m2m_avatar'));
        assert.containsOnce(document.body, '.o_ChatWindow', 'Chat window should be opened');
        assert.strictEqual(
            document.querySelector('.o_ChatWindowHeader_name').textContent,
            'Partner 1',
            'First chat window should be related to partner 1'
        );

        form.destroy();
    });

    QUnit.test('many2many_avatar_user in kanban view', async function (assert) {
        assert.expect(4);

        this.data['res.users'].records.push({ id: 15, name: "Tapu", partner_id: 11 },);
        this.data.foo.records[2].user_ids = [11, 23, 7, 15];

        const { widget: kanban } = await start({
            hasView: true,
            View: KanbanView,
            model: 'foo',
            data: this.data,
            arch: `
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
        });

        assert.containsOnce(kanban, '.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty',
            "should have o_m2m_avatar_empty span");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty').text().trim(), "+2",
            "should have +2 in o_m2m_avatar_empty");

        kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags .o_m2m_avatar_empty').trigger($.Event('mouseenter'));
        await nextTick();
        assert.containsOnce(kanban, '.popover',
            "should open a popover hover on o_m2m_avatar_empty");
        assert.strictEqual(kanban.$('.popover .popover-body > div').text().trim(), "LuigiTapu",
            "should have a right text in popover");

        kanban.destroy();
    });

    QUnit.test('many2one_avatar_user widget edited by the smart action "Assign to..."', async function (assert) {
        assert.expect(4);

        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'foo,false,form': '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
            'foo,false,search': '<search></search>',
        };
        const serverData = { models: this.data, views };
        const { widget: webClient } = await start({ hasWebClient: true, serverData });
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
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

        patchWithCleanup(session, { user_id: [7] })
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'foo,false,form': '<form><field name="user_id" widget="many2one_avatar_user"/></form>',
            'foo,false,search': '<search></search>',
        };
        const serverData = { models: this.data, views };
        const { widget: webClient } = await start({ hasWebClient: true, serverData });
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
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

        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'foo,false,form': '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
            'foo,false,search': '<search></search>',
        };
        const serverData = { models: this.data, views };
        const { widget: webClient } = await start({ hasWebClient: true, serverData });
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
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

        patchWithCleanup(session, { user_id: [7] })
        const legacyEnv = makeTestEnvironment({ bus: core.bus });
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

        const views = {
            'foo,false,form': '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
            'foo,false,search': '<search></search>',
        };
        const serverData = { models: this.data, views };
        const { widget: webClient } = await start({ hasWebClient: true, serverData });
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
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

    QUnit.test('avatar_user widget displays the appropriate user image in list view', async function (assert) {
        assert.expect(1);

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
            res_id: 1,
        });
        assert.strictEqual(
            list.$('.o_m2o_avatar > img').data('src'),
            '/web/image/res.users/11/avatar_128',
            'Should have correct avatar image'
        );
        list.destroy();
    });

    QUnit.test('avatar_user widget displays the appropriate user image in kanban view', async function (assert) {
        assert.expect(1);

        const { widget: kanban } = await start({
            hasView: true,
            View: KanbanView,
            model: 'foo',
            data: this.data,
            arch: `<kanban>
                        <templates>
                            <t t-name="kanban-box">
                                <div>
                                    <field name="user_id" widget="many2one_avatar_user"/>
                                </div>
                            </t>
                        </templates>
                    </kanban>`,
            res_id: 1,
        });
        assert.strictEqual(
            kanban.$('.o_m2o_avatar > img').data('src'),
            '/web/image/res.users/11/avatar_128',
            'Should have correct avatar image'
        );
        kanban.destroy();
    });

    QUnit.test('avatar_user widget displays the appropriate user image in form view', async function (assert) {
        assert.expect(1);

        const { widget: form } = await start({
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
            res_id: 1,
        });
        assert.strictEqual(
            form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img').data('src'),
            '/web/image/res.users/11/avatar_128',
            'Should have correct avatar image'
        );
        form.destroy();
    });
});
