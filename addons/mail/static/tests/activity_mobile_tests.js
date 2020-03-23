odoo.define('mail.activity_view_mobile_tests', function (require) {
'use strict';

const testUtils = require('web.test_utils');
const createActionManager = testUtils.createActionManager;

QUnit.module('mail mobile', {}, function () {
QUnit.module('activity view mobile', {
    beforeEach: function () {
        this.data = {
            task: {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    foo: {string: "Foo", type: "char"},
                    activity_ids: {
                        string: 'Activities',
                        type: 'one2many',
                        relation: 'mail.activity',
                        relation_field: 'res_id',
                    },
                },
                records: [
                    {id: 13, foo: 'Meeting Room Furnitures', activity_ids: [1]},
                ],
            },
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                },
                records: [{
                    id: 2,
                    display_name: "first partner",
                }]
            },
            'mail.activity': {
                fields: {
                    res_id: { string: 'Related document id', type: 'integer' },
                    activity_type_id: { string: "Activity type", type: "many2one", relation: "mail.activity.type" },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    can_write: { string: "Can write", type: "boolean" },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    mail_template_ids: { string: "Mail templates", type: "many2many", relation: "mail.template" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                },
                records:[
                    {
                        id: 1,
                        res_id: 13,
                        display_name: "An activity",
                        date_deadline: moment().add(3, "days").format("YYYY-MM-DD"), // now
                        can_write: true,
                        state: "planned",
                        activity_type_id: 1,
                        mail_template_ids: [9],
                        user_id:2,
                    },
                ],
            },
            'mail.template': {
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 9, name: "Template1" },
                ],
            },
            'mail.activity.type': {
                fields: {
                    mail_template_ids: { string: "Mail templates", type: "many2many", relation: "mail.template" },
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 1, name: "Email", mail_template_ids: [9]},
                    { id: 2, name: "Call" },
                ],
            },
        };
    }
});

QUnit.test('Activity view: in mobile, open fullscreen activity creation dialog', async function (assert) {
    assert.expect(2);

    const actionManager = await createActionManager({
        actions: [{
            id: 1,
            name: 'Task Action',
            res_model: 'task',
            type: 'ir.actions.act_window',
            views: [[false, 'activity']],
        }],
        archs: {
            'task,false,activity': `
                <activity string="Task">
                    <templates>
                        <div t-name="activity-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </activity>`,
            'task,false,search': '<search></search>',
            'mail.activity,false,form': `
                <form>
                    <field name="display_name"/>
                    <footer>
                        <button string="Discard" class="btn-secondary" special="cancel"/>
                    </footer>
                </form>`
        },
        data: this.data,
        intercepts: {
            do_action(ev) {
                assert.ok(ev.data.options.fullscreen, "'fullscreen' options should be there with true value set");
                actionManager.doAction(ev.data.action, ev.data.options);
            }
        },
    });
    await actionManager.doAction(1);

    await testUtils.dom.click(actionManager.$('.o_activity_view .o_data_row .o_activity_empty_cell:first'));
    assert.containsOnce($, '.modal.o_technical_modal.o_modal_full.show',
        "A fullscreen activity modal should be opened");

    actionManager.destroy();
});

});
});
