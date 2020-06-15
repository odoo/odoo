odoo.define('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js', function (require) {
'use strict';

const components = {
    ThreadTextualTypingStatus: require('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    nextAnimationFrame,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createThreadTextualTypingStatusComponent = async thread => {
            const ThreadTextualTypingStatusComponent = components.ThreadTextualTypingStatus;
            ThreadTextualTypingStatusComponent.env = this.env;
            this.component = new ThreadTextualTypingStatusComponent(null, {
                threadLocalId: thread.localId,
            });
            await afterNextRender(() => this.component.mount(this.widget.el));
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    async afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.ThreadTextualTypingStatus.env;
    },
});

QUnit.test('receive other member typing status "is typing"', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
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

    // simulate receive typing notification from demo
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 7,
            is_typing: true,
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

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
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
            partner_id: 7,
            is_typing: true,
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
            partner_id: 7,
            is_typing: false,
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

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
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
            partner_id: 7,
            is_typing: true,
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

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    name: 'Demo',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
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
            partner_id: 7,
            is_typing: true,
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
        partner_id: 7,
        is_typing: true,
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

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'other10@odoo.com',
                    id: 10,
                    name: 'Other10',
                }, {
                    email: 'other11@odoo.com',
                    id: 11,
                    name: 'Other11',
                }, {
                    email: 'other12@odoo.com',
                    id: 12,
                    name: 'Other12',
                }],
                name: "General",
            }],
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
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

    // simulate receive typing notification from other10 (is typing)
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 10,
            is_typing: true,
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
            partner_id: 11,
            is_typing: true,
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
            partner_id: 12,
            is_typing: true,
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
            partner_id: 10,
            is_typing: false,
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
            partner_id: 10,
            is_typing: true,
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
