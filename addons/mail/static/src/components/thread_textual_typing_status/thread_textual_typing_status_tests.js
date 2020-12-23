odoo.define('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js', function (require) {
'use strict';

const components = {
    ThreadTextualTypingStatus: require('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadTextualTypingStatusComponent = async thread => {
            await createRootComponent(this, components.ThreadTextualTypingStatus, {
                props: { threadLocalId: thread.localId },
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    async afterEach() {
        afterEach(this);
    },
});

QUnit.test('receive other member typing status "is typing"', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 17, name: 'Demo' });
    this.data['mail.channel'].records.push({
        id: 20,
        members: [this.data.currentPartnerId, 17],
    });
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
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
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is no longer typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: false,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
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
    await this.start({
        hasTimeControl: true,
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    await afterNextRender(() => this.env.testUtils.advanceTime(60 * 1000));
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
    await this.start({
        hasTimeControl: true,
    });
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 17,
            partner_name: "Demo",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should display that demo user is typing"
    );

    // simulate receive typing notification from demo "is typing" again after 50s.
    await this.env.testUtils.advanceTime(50 * 1000);
    const typingData = {
        info: 'typing_status',
        is_typing: true,
        partner_id: 17,
        partner_name: "Demo",
    };
    const notification = [[false, 'mail.channel', 20], typingData];
    this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    await this.env.testUtils.advanceTime(50 * 1000);
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Demo is typing...",
        "Should still display that demo user is typing after 100 seconds (refreshed is typing status at 50s => (100 - 50) = 50s < 60s after assuming no-longer typing)"
    );

    await afterNextRender(() => this.env.testUtils.advanceTime(11 * 1000));
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
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
    );

    // simulate receive typing notification from other10 (is typing)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 10,
            partner_name: "Other10",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10 is typing...",
        "Should display that 'Other10' member is typing"
    );

    // simulate receive typing notification from other11 (is typing)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 11,
            partner_name: "Other11",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10 and Other11 are typing...",
        "Should display that members 'Other10' and 'Other11' are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other12 (is typing)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 12,
            partner_name: "Other12",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other10, Other11 and more are typing...",
        "Should display that members 'Other10', 'Other11' and more (at least 1 extra member) are typing (order: longer typer named first)"
    );

    // simulate receive typing notification from other10 (no longer is typing)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: false,
            partner_id: 10,
            partner_name: "Other10",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other11 and Other12 are typing...",
        "Should display that members 'Other11' and 'Other12' are typing ('Other10' stopped typing)"
    );

    // simulate receive typing notification from other10 (is typing again)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: 10,
            partner_name: "Other10",
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Other11, Other12 and more are typing...",
        "Should display that members 'Other11' and 'Other12' and more (at least 1 extra member) are typing (order by longer typer, 'Other10' just recently restarted typing)"
    );
});

});
});
});

});
