/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

import ListView from 'web.ListView';
import testUtils from 'web.test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('list_view', {}, function () {
QUnit.module('list_view_tests.js', {
    beforeEach: function () {
        beforeEach(this);

        Object.assign(this.data['res.users'].fields, {
            activity_ids: {
                string: 'Activities',
                type: 'one2many',
                relation: 'mail.activity',
                relation_field: 'res_id',
            },
            activity_state: {
                string: 'State',
                type: 'selection',
                selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
            },
            activity_summary: {
                string: "Next Activity Summary",
                type: 'char',
            },
            activity_type_id: {
                string: "Activity type",
                type: "many2one",
                relation: "mail.activity.type",
            }
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('list activity widget: done the acitivty with "ENTER" keyboard shortcut', async function (assert) {
    assert.expect(2);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    Object.assign(currentUser, {
        activity_ids: [1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: 3,
    });
    this.data['mail.activity'].records.push({
        activity_type_id: 3,
        can_write: true,
        create_uid: this.data.currentUserId,
        display_name: "Call with Al",
        date_deadline: moment().format("YYYY-MM-DD"),
        id: 1,
        state: "today",
        user_id: this.data.currentUserId,
    });

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
        mockRPC(route, args) {
            if (args.method === 'action_feedback') {
                assert.step('action_feedback');
            }
            return this._super(route, args);
        },
    });
    await testUtils.dom.click(list.$('.o_activity_btn span'));
    await testUtils.dom.click(list.$('.o_mark_as_done:first'));
    await testUtils.fields.triggerKeydown(list.$('.o_activity_popover_done'), 'enter');
    assert.verifySteps(['action_feedback']);

    list.destroy();
});

QUnit.test('list activity widget: done and schedule the next acitivty with "ENTER" keyboard shortcut', async function (assert) {
    assert.expect(2);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    Object.assign(currentUser, {
        activity_ids: [1],
        activity_state: 'today',
        activity_summary: 'Call with Al',
        activity_type_id: 3,
    });
    this.data['mail.activity'].records.push({
        activity_type_id: 3,
        can_write: true,
        create_uid: this.data.currentUserId,
        display_name: "Call with Al",
        date_deadline: moment().format("YYYY-MM-DD"),
        id: 1,
        state: "today",
        user_id: this.data.currentUserId,
    });

    const { widget: list } = await start({
        hasView: true,
        View: ListView,
        model: 'res.users',
        data: this.data,
        arch: `
            <list>
                <field name="activity_ids" widget="list_activity"/>
            </list>`,
        mockRPC(route, args) {
            if (args.method === 'action_feedback_schedule_next') {
                assert.step('action_feedback_schedule_next');
            }
            return this._super(route, args);
        },
    });
    await testUtils.dom.click(list.$('.o_activity_btn span'));
    await testUtils.dom.click(list.$('.o_mark_as_done:first'));
    await testUtils.fields.triggerKeydown(list.$('.o_activity_popover_done_next'), 'enter');
    assert.verifySteps(['action_feedback_schedule_next']);

    list.destroy();
});

});
});
});
