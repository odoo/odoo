odoo.define('account.kanban_activity', function (require) {
"use strict";

const KanbanView = require('web.KanbanView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('kanban_vat_activity', {
    beforeEach: function () {
        this.data = {
            'account.journal': {
                fields: {
                    json_activity_data: { string: "json_activity_data", type: "text"},
                },
                records: [{
                    id: 1,
                    json_activity_data: '{"activities": [' +
                        '{"id": 1, "res_id": 1, "res_model": "account.move", "status": "late", "name": "Todo", "activity_category": "todo", "date": "2017-04-25"},' +
                        '{"id": 2, "res_id": 2, "res_model": "account.move", "status": "green", "name": "Todo2", "activity_category": "todo", "date": "2017-04-25"},' +
                        '{"id": 1, "res_id": 1, "res_model": "account.move", "status": "green", "name": "Todo", "activity_category": "todo", "date": "2017-04-25"},' +
                        '{"id": 1, "res_id": 1, "res_model": "account.move", "status": "green", "name": "Todo", "activity_category": "todo", "date": "2017-04-25"},' +
                        '{"id": 1, "res_id": 1, "res_model": "account.move", "status": "green", "name": "Todo", "activity_category": "todo", "date": "2017-04-25"},' +
                        '{"id": 1, "res_id": 1, "res_model": "account.move", "status": "green", "name": "Todo", "activity_category": "todo", "date": "2017-04-25"}' +
                    ']}',
                }],
            },
        };
    }
}, function () {
    QUnit.module('Kanban VAT Activity');

    QUnit.test('kanban activity field', async function (assert) {
        assert.expect(6);

        let counter = 0;
        const kanban = await createView({
            View: KanbanView,
            model: 'account.journal',
            data: this.data,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="json_activity_data" widget="kanban_vat_activity"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            res_id: 1,
            intercepts: {
                do_action: function (event) {
                    counter++;
                    if (counter === 1) {
                        assert.deepEqual(event.data.action, {
                                name: 'Journal Entry',
                                type: 'ir.actions.act_window',
                                res_model: 'account.move',
                                res_id: 1,
                                views: [[false, 'form']],
                                target: 'current',
                            },
                            "should open the form view");
                    } else if (counter === 2) {
                        assert.deepEqual(event.data.action, {
                                name: 'Journal Entries',
                                type: 'ir.actions.act_window',
                                res_model: 'account.move',
                                domain: [['journal_id', '=', 1], ['activity_ids', '!=', false]],
                                search_view_id: [false],
                                views: [[false, 'kanban'], [false, 'form']],
                            },
                            "should open list view for all activities");
                    }
                },
            },
        });

        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_journal_activity_kanban',
            "should have kanban_vat_activity widget");
        assert.containsN(kanban, '.o_mail_activity > a', 5,
            "should have 5 activity links");
        assert.containsOnce(kanban, 'a.o_activity_color_overdue',
            "should contain one overdue activity link in the kanban record");
        assert.containsOnce(kanban, 'a.see_all_activities',
            "should contain one tax report activity link in the kanban record");
        await testUtils.dom.click(kanban.el.querySelector('a.see_activity'));
        await testUtils.dom.click(kanban.el.querySelector('a.see_all_activities'));

        kanban.destroy();
    });
});
});
