/** @odoo-module **/

import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity_mark_done_popover', {}, function () {
QUnit.module('activity_mark_done_popover_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { apps, env, widget } = res;
            this.apps = apps;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('activity mark done popover simplest layout', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start();
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');

    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_feedback',
        "Popover component should contain the feedback textarea"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_buttons',
        "Popover component should contain the action buttons"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_doneScheduleNextButton',
        "Popover component should contain the done & schedule next button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_doneButton',
        "Popover component should contain the done button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_discardButton',
        "Popover component should contain the discard button"
    );
});

QUnit.test('activity with force next mark done popover simplest layout', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        chaining_type: 'trigger',
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start();
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');

    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_feedback',
        "Popover component should contain the feedback textarea"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_buttons',
        "Popover component should contain the action buttons"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_doneScheduleNextButton',
        "Popover component should contain the done & schedule next button"
    );
    assert.containsNone(
        document.body,
        '.o_ActivityMarkDonePopover_doneButton',
        "Popover component should NOT contain the done button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_discardButton',
        "Popover component should contain the discard button"
    );
});

QUnit.test('activity mark done popover mark done without feedback', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.step('action_feedback');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.notOk(args.kwargs.feedback);
                return;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
            return this._super(...arguments);
        },
    });
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');
    await click('.o_ActivityMarkDonePopover_doneButton');
    assert.verifySteps(
        ['action_feedback'],
        "Mark done and schedule next button should call the right rpc"
    );
});

QUnit.test('activity mark done popover mark done with feedback', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.step('action_feedback');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.strictEqual(args.kwargs.feedback, 'This task is done');
                return;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
            return this._super(...arguments);
        },
    });
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');

    let feedbackTextarea = document.querySelector('.o_ActivityMarkDonePopover_feedback');
    feedbackTextarea.focus();
    document.execCommand('insertText', false, 'This task is done');
    document.querySelector('.o_ActivityMarkDonePopover_doneButton').click();
    assert.verifySteps(
        ['action_feedback'],
        "Mark done and schedule next button should call the right rpc"
    );
});

QUnit.test('activity mark done popover mark done and schedule next', async function (assert) {
    assert.expect(6);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('activity_action');
        throw new Error("The do-action event should not be triggered when the route doesn't return an action");
    });
    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                assert.step('action_feedback_schedule_next');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
                assert.strictEqual(args.kwargs.feedback, 'This task is done');
                return false;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
            return this._super(...arguments);
        },
        env: { bus },
    });
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');

    let feedbackTextarea = document.querySelector('.o_ActivityMarkDonePopover_feedback');
    feedbackTextarea.focus();
    document.execCommand('insertText', false, 'This task is done');
    await click('.o_ActivityMarkDonePopover_doneScheduleNextButton');
    assert.verifySteps(
        ['action_feedback_schedule_next'],
        "Mark done and schedule next button should call the right rpc and not trigger an action"
    );
});

QUnit.test('[technical] activity mark done & schedule next with new action', async function (assert) {
    assert.expect(3);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('activity_action');
        assert.deepEqual(
            payload.action,
            { type: 'ir.actions.act_window' },
            "The content of the action should be correct"
        );
    });
    this.data['res.partner'].records.push({
        activity_ids: [12],
        id: 100,
    });
    this.data['mail.activity'].records.push({
        activity_category: 'not_upload_file',
        can_write: true,
        id: 12,
        res_id: 100,
        res_model: 'res.partner',
    });
    const { click, createChatterContainerComponent } = await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                return { type: 'ir.actions.act_window' };
            }
            return this._super(...arguments);
        },
    });
    await createChatterContainerComponent({
        threadId: 100,
        threadModel: 'res.partner',
    });
    await click('.o_Activity_markDoneButton');

    await click('.o_ActivityMarkDonePopover_doneScheduleNextButton');
    assert.verifySteps(
        ['activity_action'],
        "The action returned by the route should be executed"
    );
});

});
});
});
