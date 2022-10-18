/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";

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

QUnit.test('rpc: create from args', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerId = await messaging.rpc({
        method: 'create',
        model: 'res.partner',
        args: [[{ name: 'foo' }]],
    });
    const [partner] = pyEnv['res.partner'].searchRead([['id', '=', partnerId]]);
    assert.strictEqual('foo', partner.name);
});

QUnit.test('rpc: create from kwargs', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerId = await messaging.rpc({
        method: 'create',
        model: 'res.partner',
        kwargs: {
            vals_list: [{ name: 'foo' }],
        },
    });
    const [partner] = pyEnv['res.partner'].searchRead([['id', '=', partnerId]]);
    assert.strictEqual('foo', partner.name);
});

QUnit.test('rpc: read from args', async function (assert) {
    assert.expect(2);

    const { messaging, pyEnv } = await start();
    const partnerId = pyEnv['res.partner'].create({ name: 'foo' });
    const [partner] = await messaging.rpc({
        method: 'read',
        model: 'res.partner',
        args: [[partnerId], ['id', 'name']],
    });
    assert.strictEqual(partner.name, 'foo');
    assert.strictEqual(Object.keys(partner).length, 2);
});

QUnit.test('rpc: read from kwargs', async function (assert) {
    assert.expect(2);

    const { messaging, pyEnv } = await start();
    const partnerId = pyEnv['res.partner'].create({ name: 'foo' });
    const [partner] = await messaging.rpc({
        method: 'read',
        model: 'res.partner',
        args: [[partnerId]],
        kwargs: {
            fields: ['id', 'name'],
        }
    });
    assert.strictEqual(partner.name, 'foo');
    assert.strictEqual(Object.keys(partner).length, 2);
});

QUnit.test('rpc: readGroup from args', async function (assert) {
    assert.expect(4);

    const { messaging, pyEnv } = await start();
    const partnerIds = pyEnv['res.partner'].create([
        { name: 'foo' },
        { name: 'foo' },
        { name: 'bar' },
        { name: 'bar' },
    ]);
    const readGroupDomain = [['id', 'in', partnerIds]];
    const readGroupFields = ['name'];
    const readGroupGroupBy = ['name'];

    const [firstGroup, secondGroup] = await messaging.rpc({
        method: 'read_group',
        model: 'res.partner',
        args: [readGroupDomain, readGroupFields, readGroupGroupBy],
    });
    assert.strictEqual(firstGroup.name, 'bar');
    assert.strictEqual(firstGroup.name_count, 2);
    assert.strictEqual(secondGroup.name, 'foo');
    assert.strictEqual(secondGroup.name_count, 2);
});

QUnit.test('rpc: readGroup from kwargs', async function (assert) {
    assert.expect(4);

    const { messaging, pyEnv } = await start();
    const partnerIds = pyEnv['res.partner'].create([
        { name: 'foo' },
        { name: 'foo' },
        { name: 'bar' },
        { name: 'bar' },
    ]);
    const readGroupDomain = [['id', 'in', partnerIds]];
    const readGroupFields = ['name'];
    const readGroupGroupBy = ['name'];

    const [firstGroup, secondGroup] = await messaging.rpc({
        method: 'read_group',
        model: 'res.partner',
        kwargs: {
            domain: readGroupDomain,
            fields: readGroupFields,
            groupBy: readGroupGroupBy,
        },
    });
    assert.strictEqual(firstGroup.name, 'bar');
    assert.strictEqual(firstGroup.name_count, 2);
    assert.strictEqual(secondGroup.name, 'foo');
    assert.strictEqual(secondGroup.name_count, 2);
});

QUnit.test('rpc: search from args', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerIds = pyEnv['res.partner'].create([{ name: 'foo' }, { name: 'bar' }]);
    const searchDomain = [['id', 'in', partnerIds]];

    const serverPartnerIds = await messaging.rpc({
        model: 'res.partner',
        method: 'search',
        args: [searchDomain],
    });
    assert.deepEqual(partnerIds, serverPartnerIds);
});

QUnit.test('rpc: search from kwargs', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerIds = pyEnv['res.partner'].create([{ name: 'foo' }, { name: 'bar' }]);
    const searchDomain = [['id', 'in', partnerIds]];

    const serverPartnerIds = await messaging.rpc({
        model: 'res.partner',
        method: 'search',
        kwargs: {
            domain: searchDomain,
        },
    });
    assert.deepEqual(partnerIds, serverPartnerIds);
});

QUnit.test('rpc: searchRead from args', async function (assert) {
    assert.expect(2);

    const { messaging, pyEnv } = await start();
    const partnerIds = pyEnv['res.partner'].create([{ name: 'foo' }, { name: 'bar' }]);
    const searchReadDomain = [['id', 'in', partnerIds]];
    const searchReadFields = ['id', 'name'];

    const [firstPartner, secondPartner] = await messaging.rpc({
        model: 'res.partner',
        method: 'search_read',
        args: [searchReadDomain, searchReadFields],
    });
    assert.strictEqual(firstPartner.name, 'foo');
    assert.strictEqual(secondPartner.name, 'bar');
});

QUnit.test('rpc: write from args', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerId = pyEnv['res.partner'].create({ name: 'foo' });
    await messaging.rpc({
        method: 'write',
        model: 'res.partner',
        args: [[partnerId], { name: 'bar' }],
    });
    const [partner] = pyEnv['res.partner'].searchRead([['id', '=', partnerId]]);
    assert.strictEqual(partner.name, 'bar');
});

QUnit.test('rpc: write from kwargs', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerId = pyEnv['res.partner'].create({ name: 'foo' });
    await messaging.rpc({
        method: 'write',
        model: 'res.partner',
        args: [[partnerId]],
        kwargs: {
            vals: { name: 'bar' },
        },
    });
    const [partner] = pyEnv['res.partner'].searchRead([['id', '=', partnerId]]);
    assert.strictEqual(partner.name, 'bar');
});

QUnit.test('rpc: unlink', async function (assert) {
    assert.expect(1);

    const { messaging, pyEnv } = await start();
    const partnerId = pyEnv['res.partner'].create({ name: 'foo' });
    await messaging.rpc({
        method: 'unlink',
        model: 'res.partner',
        args: [[partnerId]],
    });
    const searchReadResults = pyEnv['res.partner'].searchRead([['id', '=', partnerId]]);
    assert.strictEqual(searchReadResults.length, 0);
});

});
});
});
