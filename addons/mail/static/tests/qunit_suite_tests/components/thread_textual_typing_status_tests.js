/** @odoo-module **/

import {
    afterNextRender,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        this.createThreadTextualTypingStatusComponent = async (thread, target) => {
            await createRootMessagingComponent(thread.env, "ThreadTextualTypingStatus", {
                props: { threadLocalId: thread.localId },
                target,
            });
        };
    },
});

QUnit.test('receive other member typing status "is typing"', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: 'Demo' });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadTextualTypingStatusComponent(thread, widget.el);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
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
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadTextualTypingStatusComponent(thread, widget.el);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is no longer typing"
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: false,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
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
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { env, messaging, widget } = await start({
        hasTimeControl: true,
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadTextualTypingStatusComponent(thread, widget.el);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    await afterNextRender(() => env.testUtils.advanceTime(60 * 1000));
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
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
    });
    const { env, messaging, widget } = await start({
        hasTimeControl: true,
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadTextualTypingStatusComponent(thread, widget.el);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Demo",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is typing" again after 50s.
    await env.testUtils.advanceTime(50 * 1000);
    widget.call('bus_service', 'trigger', 'notification', [{
        type: 'mail.channel.partner/typing_status',
        payload: {
            channel_id: mailChannelId1,
            is_typing: true,
            partner_id: resPartnerId1,
            partner_name: "Demo",
        },
    }]);
    await env.testUtils.advanceTime(50 * 1000);
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should still display that demo user is typing after 100 seconds (refreshed is typing status at 50s => (100 - 50) = 50s < 60s after assuming no-longer typing)"
    );

    await afterNextRender(() => env.testUtils.advanceTime(11 * 1000));
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
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
            [0, 0, { partner_id: resPartnerId2 }],
            [0, 0, { partner_id: resPartnerId3 }],
        ],
    });
    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await this.createThreadTextualTypingStatusComponent(thread, widget.el);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from other10 (is typing)
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Other10",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10 is typing...",
        "Should display that 'Other10' member is typing"
    );

    // simulate receive typing notification from other11 (is typing)
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId2,
                partner_name: "Other11",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10 and Other11 are typing...",
        "Should display that members 'Other10' and 'Other11' are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other12 (is typing)
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId3,
                partner_name: "Other12",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10, Other11 and more are typing...",
        "Should display that members 'Other10', 'Other11' and more (at least 1 extra member) are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other10 (no longer is typing)
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: false,
                partner_id: resPartnerId1,
                partner_name: "Other10",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other11 and Other12 are typing...",
        "Should display that members 'Other11' and 'Other12' are typing ('Other10' stopped typing)"
    );

    // simulate receive typing notification from other10 (is typing again)
    await afterNextRender(() => {
        widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel.partner/typing_status',
            payload: {
                channel_id: mailChannelId1,
                is_typing: true,
                partner_id: resPartnerId1,
                partner_name: "Other10",
            },
        }]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other11, Other12 and more are typing...",
        "Should display that members 'Other11' and 'Other12' and more (at least 1 extra member) are typing (order by longer typer, 'Other10' just recently restarted typing)"
    );
});

});
});
