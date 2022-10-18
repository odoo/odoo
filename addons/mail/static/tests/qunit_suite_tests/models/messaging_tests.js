/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('messaging_tests.js', {}, function () {

QUnit.test('openChat: display notification for partner without user', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const { messaging } = await start({
        services: {
            notification: makeFakeNotificationService(message => {
                assert.ok(
                    true,
                    "should display a toast notification after failing to open chat"
                );
                assert.strictEqual(
                    message,
                    "You can only chat with partners that have a dedicated user.",
                    "should display the correct information in the notification"
                );
            }),
        },
    });

    await messaging.openChat({ partnerId: resPartnerId1 });
});

QUnit.test('openChat: display notification for wrong user', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['res.users'].create({});
    const { messaging } = await start({
        services: {
            notification: makeFakeNotificationService(message => {
                assert.ok(
                    true,
                    "should display a toast notification after failing to open chat"
                );
                assert.strictEqual(
                    message,
                    "You can only chat with existing users.",
                    "should display the correct information in the notification"
                );
            }),
        },
    });

    // userId not in the server data
    await messaging.openChat({ userId: 4242 });
});

QUnit.test('openChat: open new chat for user', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });

    const { messaging } = await start({ data: this.data });
    const partner = messaging.models['Partner'].findFromIdentifyingData({ id: resPartnerId1 });
    const existingChat = partner ? partner.dmChatWithCurrentPartner : undefined;
    assert.notOk(existingChat, 'a chat should not exist with the target partner initially');

    await messaging.openChat({ partnerId: resPartnerId1 });
    const chat = messaging.models['Partner'].findFromIdentifyingData({ id: resPartnerId1 }).dmChatWithCurrentPartner;
    assert.ok(chat, 'a chat should exist with the target partner');
    assert.strictEqual(chat.thread.threadViews.length, 1, 'the chat should be displayed in a `ThreadView`');
});

QUnit.test('openChat: open existing chat for user', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
    });
    const { messaging } = await start();
    const existingChat = messaging.models['Partner'].findFromIdentifyingData({ id: resPartnerId1 }).dmChatWithCurrentPartner;
    assert.ok(existingChat, 'a chat should initially exist with the target partner');
    assert.strictEqual(existingChat.thread.threadViews.length, 0, 'the chat should not be displayed in a `ThreadView`');

    await messaging.openChat({ partnerId: resPartnerId1 });
    assert.ok(existingChat, 'a chat should still exist with the target partner');
    assert.strictEqual(existingChat.id, mailChannelId1, 'the chat should be the existing chat');
    assert.strictEqual(existingChat.thread.threadViews.length, 1, 'the chat should now be displayed in a `ThreadView`');
});

QUnit.test('rpc: read', async function (assert) {
    assert.expect(6);

    const { env, messaging } = await start();
    const readIds = [1, 2];
    const readFields = ['foo', 'bar'];
    patchWithCleanup(env.services.orm, {
        read(model, ids, fields, kwargs) {
            assert.strictEqual(ids, readIds);
            assert.strictEqual(fields, readFields);
            // kwargs does not contain fields since it is passed
            // as an argument to the orm service.
            assert.notOk('fields' in kwargs);
        },
    });

    // relay ids/fields from args to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'read',
        args: [readIds, readFields],
    });
    // relay ids/fields from kwargs to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'read',
        args: [readIds],
        kwargs: { fields: readFields },
    });
});

QUnit.test('rpc: readGroup', async function (assert) {
    assert.expect(12);

    const { env, messaging } = await start();
    const readGroupDomain = ['id', 'in', [1, 2]];
    const readGroupFields = ['foo', 'bar'];
    const readGroupGroupBy = ['id'];

    patchWithCleanup(env.services.orm, {
        readGroup(model, domain, fields, groupBy, kwargs) {
            assert.strictEqual(domain, readGroupDomain);
            assert.strictEqual(fields, readGroupFields);
            assert.strictEqual(groupBy, readGroupGroupBy);
            // kwargs does not contain fields/domain/groupby since they
            // are passed as arguments to the orm service.
            assert.notOk('fields' in kwargs);
            assert.notOk('groupBy' in kwargs);
            assert.notOk('domain' in kwargs);
        },
    });

    // relay domain/fields/groupBy from args to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'read_group',
        args: [readGroupDomain, readGroupFields, readGroupGroupBy],
    });
    // relay domain/fields/groupBy from kwargs to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'read_group',
        kwargs: {
            domain: readGroupDomain,
            fields: readGroupFields,
            groupBy: readGroupGroupBy,
        },
    });
});

QUnit.test('rpc: search', async function (assert) {
    assert.expect(4);

    const { env, messaging } = await start();
    const searchDomain = ['id', 'in', [1, 2]];

    patchWithCleanup(env.services.orm, {
        search(model, domain, kwargs) {
            assert.strictEqual(domain, searchDomain);
            // kwargs does not contain domain since it is passed as an
            // argument to the orm service.
            assert.notOk('domain' in kwargs);
        },
    });

    // relay domain from args to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'search',
        args: [searchDomain],
    });
    // relay domain from kwargs to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'search',
        kwargs: { domain: searchDomain },
    });
});

QUnit.test('rpc: searchRead', async function (assert) {
    assert.expect(8);

    const { env, messaging } = await start();
    const searchReadDomain = ['id', 'in', [1, 2]];
    const searchReadFields = ['foo', 'bar'];

    patchWithCleanup(env.services.orm, {
        searchRead(model, domain, fields, kwargs) {
            assert.strictEqual(domain, searchReadDomain);
            assert.strictEqual(fields, searchReadFields);
            // kwargs does not contain fields/domain since they are
            // passed as arguments to the orm service.
            assert.notOk('domain' in kwargs);
            assert.notOk('fields' in kwargs);
        },
    });

    // relay domain/fields from args to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'search_read',
        args: [searchReadDomain, searchReadFields],
    });
    // relay domain/fields from kwargs to the orm service
    messaging.rpc({
        model: 'some.model',
        method: 'search_read',
        kwargs: {
            domain: searchReadDomain,
            fields: searchReadFields,
        },
    });
});

});
});
});
