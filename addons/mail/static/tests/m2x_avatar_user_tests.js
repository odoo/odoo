/** @odoo-module **/

import { Many2OneAvatarUser } from '@mail/js/m2x_avatar_user';
import { afterEach, beforeEach, start } from '@mail/utils/test_utils';
import { click, legacyExtraNextTick, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from '@web/../tests/webclient/helpers';
import { registry } from "@web/core/registry";
import { makeLegacyCommandService } from "@web/legacy/utils";
import core from 'web.core';
import FormView from 'web.FormView';
import KanbanView from 'web.KanbanView';
import ListView from 'web.ListView';
import session from 'web.session';
import makeTestEnvironment from "web.test_env";
import { dom, mock, nextTick } from 'web.test_utils';


QUnit.module('mail', {}, function () {
    QUnit.module('M2XAvatarUser', {
        beforeEach() {
            beforeEach(this);

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
        },
        afterEach() {
            afterEach(this);
        },
    });

    QUnit.test('many2one_avatar_user widget in list view', async function (assert) {
        assert.expect(5);

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="user_id" widget="many2one_avatar_user"/></tree>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
        });

        mock.intercept(list, 'open_record', () => {
            assert.step('open record');
        });

        assert.strictEqual(list.$('.o_data_cell span').text(), 'MarioLuigiMarioYoshi');

        // sanity check: later on, we'll check that clicking on the avatar doesn't open the record
        await dom.click(list.$('.o_data_row:first span'));

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar > img'));
        await dom.click(list.$('.o_data_cell:nth(1) .o_m2o_avatar > img'));
        await dom.click(list.$('.o_data_cell:nth(2) .o_m2o_avatar > img'));


        assert.verifySteps([
            'open record',
            'read res.users 11',
            // 'call service openDMChatWindow 1',
            'read res.users 7',
            // 'call service openDMChatWindow 2',
            // 'call service openDMChatWindow 1',
        ]);

        list.destroy();
    });

    QUnit.test('many2one_avatar_user widget in kanban view', async function (assert) {
        assert.expect(6);

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
                                <field name="user_id" widget="many2one_avatar_user"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.strictEqual(kanban.$('.o_kanban_record').text().trim(), '');
        assert.containsN(kanban, '.o_m2o_avatar', 4);
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(0) > img').data('src'), '/web/image/res.users/11/avatar_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(1) > img').data('src'), '/web/image/res.users/7/avatar_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(2) > img').data('src'), '/web/image/res.users/11/avatar_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(3) > img').data('src'), '/web/image/res.users/23/avatar_128');

        kanban.destroy();
    });

    QUnit.test('many2many_avatar_user widget in form view', async function (assert) {
        assert.expect(7);

        const { widget: form } = await start({
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><field name="user_ids" widget="many2many_avatar_user"/></form>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
            res_id: 1,
        });

        assert.containsN(form, '.o_field_many2manytags.avatar.o_field_widget .badge', 2,
            "should have 2 records");
        assert.strictEqual(form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img').data('src'), '/web/image/res.users/11/avatar_128',
            "should have correct avatar image");

        await dom.click(form.$('.o_field_many2manytags.avatar .badge:first .o_m2m_avatar'));
        await dom.click(form.$('.o_field_many2manytags.avatar .badge:nth(1) .o_m2m_avatar'));

        assert.verifySteps([
            "read foo 1",
            'read res.users 11,23',
            "read res.users 11",
            "read res.users 23",
        ]);

        form.destroy();
    });

    QUnit.test('many2many_avatar_user widget with single record in list view', async function (assert) {
        assert.expect(4);

        this.data.foo.records[1].user_ids = [11];

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree editable="top"><field name="user_ids" widget="many2many_avatar_user"/></tree>',
            res_id: 1,
        });

        assert.containsN(list, '.o_data_row:eq(0) .o_field_many2manytags.avatar.o_field_widget .o_m2m_avatar', 2,
            "should have 2 records");
        assert.containsN(list, '.o_data_row:eq(1) .o_field_many2manytags.avatar.o_field_widget > div > span', 1,
            "should have 1 record in second row");
        assert.containsN(list, '.o_data_row:eq(1) .o_field_many2manytags.avatar.o_field_widget > div > span', 1,
            "should have img and span in second record");

        await dom.click(list.$('.o_data_row:eq(1) .o_field_many2manytags.avatar:first > div > span'));
        assert.containsOnce(list, '.o_selected_row');

        list.destroy();
    });

    QUnit.test('many2many_avatar_user widget in list view', async function (assert) {
        assert.expect(8);

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="user_ids" widget="many2many_avatar_user"/></tree>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
        });

        mock.intercept(list, 'open_record', () => {
            assert.step('open record');
        });

        assert.containsN(list.$(".o_data_cell:first"), '.o_field_many2manytags.avatar.o_field_widget span', 2,
            "should have 2 records");
        assert.strictEqual(list.$(".o_data_cell:first .o_field_many2manytags.avatar img.o_m2m_avatar:first").data('src'),
            "/web/image/res.users/11/avatar_128",
            "should have right image");
        assert.strictEqual(list.$(".o_data_cell:eq(0) .o_field_many2manytags.avatar img.o_m2m_avatar:eq(1)").data('src'),
            "/web/image/res.users/23/avatar_128",
            "should have right image");

        // sanity check: later on, we'll check that clicking on the avatar doesn't open the record
        await dom.click(list.$('.o_data_row:first .o_field_many2manytags'));

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2m_avatar:nth(0)'));
        await dom.click(list.$('.o_data_cell:nth(0) .o_m2m_avatar:nth(1)'));

        assert.verifySteps([
            'read res.users 11,23',
            "open record",
            "read res.users 11",
            "read res.users 23",
        ]);

        list.destroy();
    });

    QUnit.test('many2many_avatar_user in kanban view', async function (assert) {
        assert.expect(11);

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
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
        });

        mock.intercept(kanban, 'open_record', () => {
            assert.step('open record');
        });

        assert.strictEqual(kanban.$('.o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar:first').data('src'),
            "/web/image/res.users/11/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(kanban.$('.o_kanban_record:first .o_field_many2manytags img.o_m2m_avatar:eq(1)').data('src'),
            "/web/image/res.users/23/avatar_128",
            "should have correct avatar image");

        assert.containsN(kanban, '.o_kanban_record:eq(2) .o_field_many2manytags > span:not(.o_m2m_avatar_empty)', 2,
            "should have 2 records");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:first').data('src'),
            "/web/image/res.users/11/avatar_128",
            "should have correct avatar image");
        assert.strictEqual(kanban.$('.o_kanban_record:eq(2) .o_field_many2manytags img.o_m2m_avatar:eq(1)').data('src'),
            "/web/image/res.users/23/avatar_128",
            "should have correct avatar image");
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

        assert.verifySteps([
            "read res.users 7,11,15,23",
        ]);

        kanban.destroy();
    });

    QUnit.test('many2one_avatar_user widget in list view with no_open_chat set to true', async function (assert) {
        assert.expect(3);

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: `<tree><field name="user_id" widget="many2one_avatar_user" options="{'no_open_chat': 1}"/></tree>`,
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
        });

        mock.intercept(list, 'open_record', () => {
            assert.step('open record');
        });

        assert.strictEqual(list.$('.o_data_cell span').text(), 'MarioLuigiMarioYoshi');

        // sanity check: later on, we'll check that clicking on the avatar doesn't open the record
        await dom.click(list.$('.o_data_row:first span'));

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar > img'));
        await dom.click(list.$('.o_data_cell:nth(1) .o_m2o_avatar > img'));
        await dom.click(list.$('.o_data_cell:nth(2) .o_m2o_avatar > img'));


        assert.verifySteps([
            'open record',
        ]);

        list.destroy();
    });

    QUnit.test('many2one_avatar_user widget in kanban view', async function (assert) {
        assert.expect(3);

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
                                <field name="user_id" widget="many2one_avatar_user" options="{'no_open_chat': 1}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.strictEqual(kanban.$('.o_kanban_record').text().trim(), '');
        assert.containsN(kanban, '.o_m2o_avatar', 4);
        dom.click(kanban.$('.o_m2o_avatar:nth(0) > img'));
        dom.click(kanban.$('.o_m2o_avatar:nth(1) > img'));
        dom.click(kanban.$('.o_m2o_avatar:nth(2) > img'));
        dom.click(kanban.$('.o_m2o_avatar:nth(3) > img'));

        assert.verifySteps([], "no read res.user should be done since we don't want to open chat when the user clicks on avatar.");

        kanban.destroy();
    });

    QUnit.test('many2many_avatar_user widget in form view', async function (assert) {
        assert.expect(5);

        const { widget: form } = await start({
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: `<form><field name="user_ids" widget="many2many_avatar_user" options="{'no_open_chat': 1}"/></form>`,
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
            res_id: 1,
        });

        assert.containsN(form, '.o_field_many2manytags.avatar.o_field_widget .badge', 2,
            "should have 2 records");
        assert.strictEqual(form.$('.o_field_many2manytags.avatar.o_field_widget .badge:first img').data('src'), '/web/image/res.users/11/avatar_128',
            "should have correct avatar image");

        await dom.click(form.$('.o_field_many2manytags.avatar .badge:first .o_m2m_avatar'));
        await dom.click(form.$('.o_field_many2manytags.avatar .badge:nth(1) .o_m2m_avatar'));

        assert.verifySteps([
            "read foo 1",
            'read res.users 11,23',
        ]);

        form.destroy();
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
        const models = {
            'foo': this.data.foo,
            'res.partner': this.data['res.partner'],
            'res.users': this.data['res.users'],
        }
        const serverData = { models, views}
        const webClient = await createWebClient({serverData});
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        assert.strictEqual(webClient.el.querySelector(".o_m2o_avatar > span").textContent, "Mario")

        triggerHotkey("control+k")
        await nextTick();
        const idx = [...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign to ...ALT + I")
        assert.ok(idx >= 0);

        await click([...webClient.el.querySelectorAll(".o_command")][idx])
        await nextTick();
        assert.deepEqual([...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent), [
            "Your Company, Mitchell Admin",
            "Public user",
            "Mario",
            "Luigi",
            "Yoshi",
          ])
        await click(webClient.el, "#o_command_3")
        await legacyExtraNextTick();
        assert.strictEqual(webClient.el.querySelector(".o_m2o_avatar > span").textContent, "Luigi")
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
        const models = {
            'foo': this.data.foo,
            'res.partner': this.data['res.partner'],
            'res.users': this.data['res.users'],
        }
        const serverData = { models, views}
        const webClient = await createWebClient({serverData});
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        assert.strictEqual(webClient.el.querySelector(".o_m2o_avatar > span").textContent, "Mario")
        triggerHotkey("control+k")
        await nextTick();
        const idx = [...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign/unassign to meALT + SHIFT + I")
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i")
        await legacyExtraNextTick();
        assert.strictEqual(webClient.el.querySelector(".o_m2o_avatar > span").textContent, "Luigi")

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...webClient.el.querySelectorAll(".o_command")][idx])
        await legacyExtraNextTick();
        assert.strictEqual(webClient.el.querySelector(".o_m2o_avatar > span").textContent, "")
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
        const models = {
            'foo': this.data.foo,
            'res.partner': this.data['res.partner'],
            'res.users': this.data['res.users'],
        }
        const serverData = { models, views}
        const webClient = await createWebClient({serverData});
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        let userNames = [...webClient.el.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k")
        await nextTick();
        const idx = [...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign to ...ALT + I")
        assert.ok(idx >= 0);

        await click([...webClient.el.querySelectorAll(".o_command")][idx])
        await nextTick();
        assert.deepEqual([...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent), [
            "Your Company, Mitchell Admin",
            "Public user",
            "Luigi"
          ]);

        await click(webClient.el, "#o_command_2");
        await legacyExtraNextTick();
        userNames = [...webClient.el.querySelectorAll(".o_tag_badge_text")].map(el => el.textContent);
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
        const models = {
            'foo': this.data.foo,
            'res.partner': this.data['res.partner'],
            'res.users': this.data['res.users'],
        }
        const serverData = { models, views}
        const webClient = await createWebClient({serverData});
        await doAction(webClient, {
            res_id: 1,
            type: 'ir.actions.act_window',
            target: 'current',
            res_model: 'foo',
            'view_mode': 'form',
            'views': [[false, 'form']],
        });
        let userNames = [...webClient.el.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);

        triggerHotkey("control+k");
        await nextTick();
        const idx = [...webClient.el.querySelectorAll(".o_command")].map(el => el.textContent).indexOf("Assign/unassign to meALT + SHIFT + I");
        assert.ok(idx >= 0);

        // Assign me (Luigi)
        triggerHotkey("alt+shift+i");
        await legacyExtraNextTick();
        userNames = [...webClient.el.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi", "Luigi"]);

        // Unassign me
        triggerHotkey("control+k");
        await nextTick();
        await click([...webClient.el.querySelectorAll(".o_command")][idx]);
        await legacyExtraNextTick();
        userNames = [...webClient.el.querySelectorAll(".o_tag_badge_text")].map((el => el.textContent));
        assert.deepEqual(userNames, ["Mario", "Yoshi"]);
    });

});
