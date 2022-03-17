/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    async beforeEach() {
        await beforeEach(this);

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

    this.data['res.partner'].records.push({ id: 17, name: 'Demo' });
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 17,
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

    this.data['res.partner'].records.push({ id: 17, name: 'Demo' });
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 17,
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
                channel_id: 20,
                is_typing: false,
                partner_id: 17,
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

    this.data['res.partner'].records.push({ id: 17, name: 'Demo' });
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    const { env, messaging, widget } = await start({ data: this.data, hasTimeControl: true });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 17,
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

    this.data['res.partner'].records.push({ id: 17, name: 'Demo' });
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    const { env, messaging, widget } = await start({
        data: this.data,
        hasTimeControl: true,
    });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 17,
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
            channel_id: 20,
            is_typing: true,
            partner_id: 17,
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

    this.data['res.partner'].records.push(
        { id: 10, name: 'Other10' },
        { id: 11, name: 'Other11' },
        { id: 12, name: 'Other12' }
    );
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 10, 11, 12],
    });
    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: 20,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 10,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 11,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 12,
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
                channel_id: 20,
                is_typing: false,
                partner_id: 10,
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
                channel_id: 20,
                is_typing: true,
                partner_id: 10,
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
