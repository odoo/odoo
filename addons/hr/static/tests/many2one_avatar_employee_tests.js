odoo.define('hr.Many2OneAvatarEmployeeTests', function (require) {
"use strict";

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

const FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
const ListView = require('web.ListView');
const { Many2OneAvatarEmployee } = require('hr.Many2OneAvatarEmployee');
const { dom, mock } = require('web.test_utils');

QUnit.module('hr', {}, function () {
    QUnit.module('Many2OneAvatarEmployee', {
        beforeEach() {
            beforeEach(this);

            // reset the cache before each test
            Many2OneAvatarEmployee.prototype.partnerIds = {};

            Object.assign(this.data, {
                'foo': {
                    fields: {
                        employee_id: { string: "Employee", type: 'many2one', relation: 'hr.employee.public' },
                    },
                    records: [
                        { id: 1, employee_id: 11 },
                        { id: 2, employee_id: 7 },
                        { id: 3, employee_id: 11 },
                        { id: 4, employee_id: 23 },
                    ],
                },
            });
            this.data['hr.employee.public'].records.push(
                { id: 11, name: "Mario", user_id: 11, user_partner_id: 11 },
                { id: 7, name: "Luigi", user_id: 12, user_partner_id: 12 },
                { id: 23, name: "Yoshi", user_id: 13, user_partner_id: 13 }
            );
            this.data['res.users'].records.push(
                { id: 11, partner_id: 11 },
                { id: 12, partner_id: 12 },
                { id: 13, partner_id: 13 }
            );
            this.data['res.partner'].records.push(
                { id: 11, display_name: "Mario" },
                { id: 12, display_name: "Luigi" },
                { id: 13, display_name: "Yoshi" }
            );
        },
        afterEach() {
            afterEach(this);
        },
    });

    QUnit.test('many2one_avatar_employee widget in list view', async function (assert) {
        assert.expect(11);

        const { widget: list } = await start({
            hasChatWindow: true,
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

        // click on first employee
        await afterNextRender(() =>
            dom.click(list.$('.o_data_cell:nth(0) .o_m2o_avatar'))
        );
        assert.verifySteps(
            ['read hr.employee.public 11'],
            "first employee should have been read to find its partner"
        );
        assert.containsOnce(
            document.body,
            '.o_ChatWindowHeader_name',
            'should have opened chat window'
        );
        assert.strictEqual(
            document.querySelector('.o_ChatWindowHeader_name').textContent,
            "Mario",
            'chat window should be with clicked employee'
        );

        // click on second employee
        await afterNextRender(() =>
            dom.click(list.$('.o_data_cell:nth(1) .o_m2o_avatar')
        ));
        assert.verifySteps(
            ['read hr.employee.public 7'],
            "second employee should have been read to find its partner"
        );
        assert.containsN(
            document.body,
            '.o_ChatWindowHeader_name',
            2,
            'should have opened second chat window'
        );
        assert.strictEqual(
            document.querySelectorAll('.o_ChatWindowHeader_name')[1].textContent,
            "Luigi",
            'chat window should be with clicked employee'
        );

        // click on third employee (same as first)
        await afterNextRender(() =>
            dom.click(list.$('.o_data_cell:nth(2) .o_m2o_avatar'))
        );
        assert.verifySteps(
            [],
            "employee should not have been read again because we already know its partner"
        );
        assert.containsN(
            document.body,
            '.o_ChatWindowHeader_name',
            2,
            "should still have only 2 chat windows because third is the same partner as first"
        );

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
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(0)').data('src'), '/web/image/hr.employee.public/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(1)').data('src'), '/web/image/hr.employee.public/7/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(2)').data('src'), '/web/image/hr.employee.public/11/image_128');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(3)').data('src'), '/web/image/hr.employee.public/23/image_128');

        kanban.destroy();
    });

    QUnit.test('many2one_avatar_employee: click on an employee not associated with a user', async function (assert) {
        assert.expect(6);

        this.data['hr.employee.public'].records[0].user_id = false;
        this.data['hr.employee.public'].records[0].user_partner_id = false;
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
            'read hr.employee.public 11',
        ]);

        assert.containsOnce(
            document.body,
            '.toast .o_notification_content',
            "should display a toast notification after failing to open chat"
        );
        assert.strictEqual(
            document.querySelector('.o_notification_content').textContent,
            "You can only chat with employees that have a dedicated user.",
            "should display the correct information in the notification"
        );

        form.destroy();
    });
});
});
