odoo.define('mail.Many2OneAvatarUserTests', function (require) {
"use strict";

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

const KanbanView = require('web.KanbanView');
const ListView = require('web.ListView');
const { Many2OneAvatarUser } = require('mail.Many2OneAvatarUser');
const { dom, mock } = require('web.test_utils');


QUnit.module('mail', {}, function () {
    QUnit.module('Many2OneAvatarUser', {
        beforeEach() {
            beforeEach(this);

            // reset the cache before each test
            Many2OneAvatarUser.prototype.partnerIds = {};

            Object.assign(this.data, {
                'foo': {
                    fields: {
                        user_id: { string: "User", type: 'many2one', relation: 'res.users' },
                    },
                    records: [
                        { id: 1, user_id: 11 },
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

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar'));
        await dom.click(list.$('.o_data_cell:nth(1) .o_m2o_avatar'));
        await dom.click(list.$('.o_data_cell:nth(2) .o_m2o_avatar'));


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
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(0)').data('src'), '/web/image/res.users/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(1)').data('src'), '/web/image/res.users/7/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(2)').data('src'), '/web/image/res.users/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(3)').data('src'), '/web/image/res.users/23/image_128');

        kanban.destroy();
    });
});
});
