odoo.define('hr.Many2OneAvatarEmployeeTests', function (require) {
"use strict";

const { start } = require('mail/static/src/utils/test_utils.js');

const FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
const ListView = require('web.ListView');
const { Many2OneAvatarEmployee } = require('hr.Many2OneAvatarEmployee');
const { createView, dom, mock } = require('web.test_utils');


QUnit.module('hr', {}, function () {
    QUnit.module('Many2OneAvatarEmployee', {
        beforeEach: function () {
            // reset the cache before each test
            Many2OneAvatarEmployee.prototype.partnerIds = {};

            this.data = {
                'foo': {
                    fields: {
                        employee_id: { string: "Employee", type: 'many2one', relation: 'hr.employee' },
                    },
                    records: [
                        { id: 1, employee_id: 11 },
                        { id: 2, employee_id: 7 },
                        { id: 3, employee_id: 11 },
                        { id: 4, employee_id: 23 },
                    ],
                },
                'hr.employee': {
                    fields: {
                        display_name: { string: "Name", type: "char" },
                        user_partner_id: { string: "Partner", type: "many2one", relation: 'res.partner' },
                    },
                    records: [{
                        id: 11,
                        name: "Mario",
                        user_partner_id: 1,
                    }, {
                        id: 7,
                        name: "Luigi",
                        user_partner_id: 2,
                    }, {
                        id: 23,
                        name: "Yoshi",
                        user_partner_id: 3,
                    }],
                },
                'res.partner': {
                    fields: {
                        display_name: { string: "Name", type: "char" },
                    },
                    records: [{
                        id: 1,
                        display_name: "Partner 1",
                    }, {
                        id: 2,
                        display_name: "Partner 2",
                    }, {
                        id: 3,
                        display_name: "Partner 3",
                    }],
                },
            };
        },
    });

    QUnit.test('many2one_avatar_employee widget in list view', async function (assert) {
        assert.expect(4);

        const { widget: list } = await start({
            hasView: true,
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="employee_id" widget="many2one_avatar_employee"/></tree>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
        });

        assert.strictEqual(list.$('.o_data_cell span').text(), 'MarioLuigiMarioYoshi');

        await dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar'));
        await dom.click(list.$('.o_data_cell:nth(1) .o_m2o_avatar'));
        await dom.click(list.$('.o_data_cell:nth(2) .o_m2o_avatar'));


        assert.verifySteps([
            'read hr.employee 11',
            // 'call service openDMChatWindow 1',
            'read hr.employee 7',
            // 'call service openDMChatWindow 2',
            // 'call service openDMChatWindow 1',
        ]);

        list.destroy();
    });

    QUnit.test('many2one_avatar_employee widget in kanban view', async function (assert) {
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
                                <field name="employee_id" widget="many2one_avatar_employee"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.strictEqual(kanban.$('.o_kanban_record').text().trim(), '');
        assert.containsN(kanban, '.o_m2o_avatar', 4);
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(0)').data('src'), '/web/image/hr.employee/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(1)').data('src'), '/web/image/hr.employee/7/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(2)').data('src'), '/web/image/hr.employee/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(3)').data('src'), '/web/image/hr.employee/23/image_128');

        kanban.destroy();
    });

    QUnit.test('many2one_avatar_employee: click on an employee not associated with a user', async function (assert) {
        assert.expect(5);

        this.data['hr.employee'].records[0].user_partner_id = false;
        const { widget: form } = await start({
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><field name="employee_id" widget="many2one_avatar_employee"/></form>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
            res_id: 1,
        });

        mock.intercept(form, 'call_service', (ev) => {
            if (ev.data.service === 'notification') {
                assert.step(`display notification "${ev.data.args[0].message}"`);
            }
        }, true);

        assert.strictEqual(form.$('.o_field_widget[name=employee_id]').text().trim(), 'Mario');

        await dom.click(form.$('.o_m2o_avatar'));

        assert.verifySteps([
            'read foo 1',
            'read hr.employee 11',
            'display notification "You can only chat with employees that have a dedicated user"',
        ]);

        form.destroy();
    });

    QUnit.test('many2one_avatar_employee: click on self', async function (assert) {
        assert.expect(5);

        const { widget: form } = await start({
            hasView: true,
            View: FormView,
            model: 'foo',
            data: this.data,
            arch: '<form><field name="employee_id" widget="many2one_avatar_employee"/></form>',
            mockRPC(route, args) {
                if (args.method === 'read') {
                    assert.step(`read ${args.model} ${args.args[0]}`);
                }
                return this._super(...arguments);
            },
            session: {
                partner_id: 1,
            },
            res_id: 1,
        });

        mock.intercept(form, 'call_service', (ev) => {
            if (ev.data.service === 'notification') {
                assert.step(`display notification "${ev.data.args[0].message}"`);
            }
        }, true);

        assert.strictEqual(form.$('.o_field_widget[name=employee_id]').text().trim(), 'Mario');

        await dom.click(form.$('.o_m2o_avatar'));

        assert.verifySteps([
            'read foo 1',
            'read hr.employee 11',
            'display notification "You cannot chat with yourself"',
        ]);

        form.destroy();
    });
});
});
