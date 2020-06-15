odoo.define('mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover_tests.js', function (require) {
'use strict';

const components = {
    ActivityMarkDonePopover: require('mail/static/src/components/activity_mark_done_popover/activity_mark_done_popover.js'),
};

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity_mark_done_popover', {}, function () {
QUnit.module('activity_mark_done_popover_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createActivityMarkDonePopoverComponent = async activity => {
            const ActivityMarkDonePopoverComponent = components.ActivityMarkDonePopover;
            ActivityMarkDonePopoverComponent.env = this.env;
            this.component = new ActivityMarkDonePopoverComponent(null, {
                activityLocalId: activity.localId,
            });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
    },
});

QUnit.test('activity mark done popover simplest layout', async function (assert) {
    assert.expect(6);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);

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

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        force_next: true,
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);

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
    assert.containsNone(
        document.body,
        '.o_ActivityMarkDonePopover_discardButton',
        "Popover component should NOT contain the discard button"
    );
});

QUnit.test('activity mark done popover click on discard', async function (assert) {
    assert.expect(4);

    await this.start();
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);
    function onPopoverClose(ev) {
        assert.step('event_triggered');
    }
    document.addEventListener('o-popover-close', onPopoverClose);

    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopover_discardButton',
        "Popover component should contain the discard button"
    );
    document.querySelector('.o_ActivityMarkDonePopover_discardButton').click();
    assert.verifySteps(['event_triggered'], 'Discard clicked should trigger the right event');

    document.removeEventListener('o-popover-close', onPopoverClose);
});

QUnit.test('activity mark done popover mark done without feedback', async function (assert) {
    assert.expect(7);

    await this.start({
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
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);

    document.querySelector('.o_ActivityMarkDonePopover_doneButton').click();
    assert.verifySteps(
        ['action_feedback'],
        "Mark done and schedule next button should call the right rpc"
    );
});

QUnit.test('activity mark done popover mark done with feedback', async function (assert) {
    assert.expect(7);

    await this.start({
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
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);

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

    await this.start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                assert.step('action_feedback_schedule_next');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 12);
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
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        category: 'not_upload_file',
        id: 12,
    });
    await this.createActivityMarkDonePopoverComponent(activity);

    let feedbackTextarea = document.querySelector('.o_ActivityMarkDonePopover_feedback');
    feedbackTextarea.focus();
    document.execCommand('insertText', false, 'This task is done');
    document.querySelector('.o_ActivityMarkDonePopover_doneScheduleNextButton').click();
    assert.verifySteps(
        ['action_feedback_schedule_next'],
        "Mark done and schedule next button should call the right rpc"
    );
});

});
});
});

});
