/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity_mark_done_popover_tests.js');

QUnit.test('activity mark done popover simplest layout', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    await click('.o_Activity_markDoneButton');

    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_feedback',
        "Popover component should contain the feedback textarea"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_buttons',
        "Popover component should contain the action buttons"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_doneScheduleNextButton',
        "Popover component should contain the done & schedule next button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_doneButton',
        "Popover component should contain the done button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_discardButton',
        "Popover component should contain the discard button"
    );
});

QUnit.test('activity with force next mark done popover simplest layout', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        chaining_type: 'trigger',
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    await click('.o_Activity_markDoneButton');

    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent',
        "Popover component should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_feedback',
        "Popover component should contain the feedback textarea"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_buttons',
        "Popover component should contain the action buttons"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_doneScheduleNextButton',
        "Popover component should contain the done & schedule next button"
    );
    assert.containsNone(
        document.body,
        '.o_ActivityMarkDonePopoverContent_doneButton',
        "Popover component should NOT contain the done button"
    );
    assert.containsOnce(
        document.body,
        '.o_ActivityMarkDonePopoverContent_discardButton',
        "Popover component should contain the discard button"
    );
});

QUnit.test('activity mark done popover mark done without feedback', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.step('action_feedback');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], mailActivityId1);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.notOk(args.kwargs.feedback);
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    await click('.o_Activity_markDoneButton');
    await click('.o_ActivityMarkDonePopoverContent_doneButton');
    assert.verifySteps(
        ['action_feedback'],
        "Mark done and schedule next button should call the right rpc"
    );
});

QUnit.test('activity mark done popover mark done with feedback', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.step('action_feedback');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], mailActivityId1);
                assert.strictEqual(args.kwargs.attachment_ids.length, 0);
                assert.strictEqual(args.kwargs.feedback, 'This task is done');
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    await click('.o_Activity_markDoneButton');

    let feedbackTextarea = document.querySelector('.o_ActivityMarkDonePopoverContent_feedback');
    feedbackTextarea.focus();
    document.execCommand('insertText', false, 'This task is done');
    document.querySelector('.o_ActivityMarkDonePopoverContent_doneButton').click();
    assert.verifySteps(
        ['action_feedback'],
        "Mark done and schedule next button should call the right rpc"
    );
});

QUnit.test('activity mark done popover mark done and schedule next', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailActivityId1 = pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, env, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                assert.step('action_feedback_schedule_next');
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], mailActivityId1);
                assert.strictEqual(args.kwargs.feedback, 'This task is done');
                return false;
            }
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                // 'unlink' on non-existing record raises a server crash
                throw new Error("'unlink' RPC on activity must not be called (already unlinked from mark as done)");
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction() {
            assert.step('activity_action');
            throw new Error("The do-action event should not be triggered when the route doesn't return an action");
        },
    });
    await click('.o_Activity_markDoneButton');

    let feedbackTextarea = document.querySelector('.o_ActivityMarkDonePopoverContent_feedback');
    feedbackTextarea.focus();
    document.execCommand('insertText', false, 'This task is done');
    await click('.o_ActivityMarkDonePopoverContent_doneScheduleNextButton');
    assert.verifySteps(
        ['action_feedback_schedule_next'],
        "Mark done and schedule next button should call the right rpc and not trigger an action"
    );
});

QUnit.test('[technical] activity mark done & schedule next with new action', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['mail.activity'].create({
        activity_category: 'not_upload_file',
        can_write: true,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, env, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                return { type: 'ir.actions.act_window' };
            }
        },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('activity_action');
            assert.deepEqual(
                action,
                { type: 'ir.actions.act_window' },
                "The content of the action should be correct"
            );
        },
    });
    await click('.o_Activity_markDoneButton');

    await click('.o_ActivityMarkDonePopoverContent_doneScheduleNextButton');
    assert.verifySteps(
        ['activity_action'],
        "The action returned by the route should be executed"
    );
});

});
});
