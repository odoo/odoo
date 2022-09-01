/** @odoo-module **/

import {
    afterNextRender,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js');

QUnit.test('receive other member typing status "is typing"', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Demo' });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );
});

QUnit.test('receive other member typing status "is typing" then "no longer is typing"', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Demo' });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is no longer typing"
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': false,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should no longer display that demo user is typing"
    );
});

QUnit.test('assume other member typing status becomes "no longer is typing" after 60 seconds without any updated typing status', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Demo' });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { advanceTime, messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
        hasTimeControl: true,
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    await afterNextRender(() => advanceTime(60 * 1000));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should no longer display that demo user is typing"
    );
});

QUnit.test ('other member typing status "is typing" refreshes 60 seconds timer of assuming no longer typing', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Demo' });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { advanceTime, messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
        hasTimeControl: true,
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is typing" again after 50s.
    await advanceTime(50 * 1000);
    messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    });
    await advanceTime(50 * 1000);
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should still display that demo user is typing after 100 seconds (refreshed is typing status at 50s => (100 - 50) = 50s < 60s after assuming no-longer typing)"
    );

    await afterNextRender(() => advanceTime(11 * 1000));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should no longer display that demo user is typing after 111 seconds (refreshed is typing status at 50s => (111 - 50) = 61s > 60s after assuming no-longer typing)"
    );
});

QUnit.test('receive several other members typing status "is typing"', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3] = pyEnv['res.partner'].create([
        { name: 'Other 10' },
        { name: 'Other 11' },
        { name: 'Other 12' },
    ]);
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
            [0, 0, { partner_id: resPartnerId3 }],
        ],
    });
    const { messaging, openDiscuss } = await start({
        discuss: {
            context: { active_id: mailChannelId1 },
        },
    });
    await openDiscuss();

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from other 10 (is typing)
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other 10 is typing...",
        "Should display that 'Other 10' member is typing"
    );

    // simulate receive typing notification from other 11 (is typing)
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId2,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other 10 and Other 11 are typing...",
        "Should display that members 'Other 10' and 'Other 11' are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other 12 (is typing)
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId3,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other 10, Other 11 and more are typing...",
        "Should display that members 'Other 10', 'Other 11' and more (at least 1 extra member) are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other 10 (no longer is typing)
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': false,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other 11 and Other 12 are typing...",
        "Should display that members 'Other 11' and 'Other 12' are typing ('Other 10' stopped typing)"
    );

    // simulate receive typing notification from other 10 (is typing again)
    await afterNextRender(() => messaging.rpc({
        route: '/mail/channel/notify_typing',
        params: {
            'channel_id': mailChannelId1,
            'context': {
                'mockedPartnerId': resPartnerId1,
            },
            'is_typing': true,
        },
    }));
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other 11, Other 12 and more are typing...",
        "Should display that members 'Other 11' and 'Other 12' and more (at least 1 extra member) are typing (order by longer typer, 'Other 10' just recently restarted typing)"
    );
});

});
});
