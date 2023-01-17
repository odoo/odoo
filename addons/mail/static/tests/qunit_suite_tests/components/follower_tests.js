/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import { start, startServer } from '@mail/../tests/helpers/test_utils';
import { editInput, patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_tests.js');

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args, performRpc) {
            if (route === '/mail/thread/data') {
                // mimic user without write access
                const res = await performRpc(...arguments);
                res['hasWriteAccess'] = false;
                return res;
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_avatar',
        "should display the avatar of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_name',
        "should display the name of the follower"
    );
    assert.containsNone(
        document.body,
        '.o_Follower_button',
        "should have no button as follower is not editable"
    );
});

QUnit.test('base rendering editable', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const { click, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_avatar',
        "should display the avatar of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_name',
        "should display the name of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_editButton',
        "should have an edit button"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_removeButton',
        "should have a remove button"
    );
});

QUnit.test('click on partner follower details', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const openFormDef = makeDeferred();
    const { click, env, openView } = await start();
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.step('do_action');
            assert.strictEqual(
                action.res_id,
                partnerId,
                "The redirect action should redirect to the right res id (partnerId)"
            );
            assert.strictEqual(
                action.res_model,
                'res.partner',
                "The redirect action should redirect to the right res model (res.partner)"
            );
            assert.strictEqual(
                action.type,
                "ir.actions.act_window",
                "The redirect action should be of type 'ir.actions.act_window'"
            );
            openFormDef.resolve();
        },
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );

    document.querySelector('.o_Follower_details').click();
    await openFormDef;
    assert.verifySteps(
        ['do_action'],
        "clicking on follower should redirect to partner form view"
    );
});

QUnit.test('click on edit follower', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const { click, messaging, openView } = await start({
        async mockRPC(route, args) {
            if (route.includes('/mail/read_subscription_data')) {
                assert.step('fetch_subtypes');
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    const thread = messaging.models['Thread'].insert({
        id: threadId,
        model: 'res.partner',
    });
    await thread.fetchData(['followers']);
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_editButton',
        "should display an edit button"
    );

    await click('.o_Follower_editButton');
    assert.verifySteps(
        ['fetch_subtypes'],
        "clicking on edit follower should fetch subtypes"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtypeList',
        "A dialog allowing to edit follower subtypes should have been created"
    );
});

QUnit.test('edit follower and close subtype dialog', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args) {
            if (route.includes('/mail/read_subscription_data')) {
                assert.step('fetch_subtypes');
                return [{
                    default: true,
                    followed: true,
                    internal: false,
                    id: 1,
                    name: "Dummy test",
                    res_model: 'res.partner'
                }];
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_editButton',
        "should display an edit button"
    );

    await click('.o_Follower_editButton');
    assert.verifySteps(
        ['fetch_subtypes'],
        "clicking on edit follower should fetch subtypes"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtypeList',
        "dialog allowing to edit follower subtypes should have been created"
    );

    await click('.o_FollowerSubtypeList_closeButton');
    assert.containsNone(
        document.body,
        '.o_DialogManager_dialog',
        "follower subtype dialog should be closed after clicking on close button"
    );
});

QUnit.test('remove a follower in a dirty form view', async function (assert) {
    const pyEnv = await startServer();
    const [threadId, partnerId] = pyEnv['res.partner'].create([{}, {}]);
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: partnerId,
        res_id: threadId,
        res_model: 'res.partner',
    });
    const { click, openView } = await start({
        async mockRPC(route, args) {
            if (args.method === 'read') {
                assert.step(`read ${args.args[0][0]}`);
            }
        },
    });
    await openView({
        res_id: threadId,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.body.querySelector(".o_FollowerListMenu_buttonFollowersCount").innerText,
        "1"
    );
    assert.verifySteps([`read ${threadId}`]);

    await editInput(document.body, ".o_field_char[name=name] input", "some value");
    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(document.body, ".o_FollowerListMenu_dropdown .o_Follower");

    await click('.o_FollowerListMenu_dropdown .o_Follower .o_Follower_removeButton');
    assert.strictEqual(
        document.body.querySelector(".o_FollowerListMenu_buttonFollowersCount").innerText,
        "0"
    );
    assert.strictEqual(
        document.body.querySelector(".o_field_char[name=name] input").value,
        "some value"
    );
    assert.verifySteps([`read ${threadId}`]);
});

});
});
