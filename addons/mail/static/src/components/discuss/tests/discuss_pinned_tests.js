odoo.define('mail/static/src/components/discuss/tests/discuss_pinned_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_pinned_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        if (this.widget) {
            this.widget.destroy();
        }
        utilsAfterEach(this);
    },
});

QUnit.test('sidebar: pinned channel 1: init with one pinned channel', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
    });
    await this.start();
    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${this.env.messaging.inbox.localId}"]`,
        "The Inbox is opened in discuss"
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarItem[data-thread-local-id="${
            this.env.models['mail.thread'].find(thread =>
                thread.id === 20 && thread.model === 'mail.channel'
            ).localId
        }"]`,
        "1 channel is present in discuss sidebar and it is 'general'"
    );
});

QUnit.test('sidebar: pinned channel 2: open pinned channel', async function (assert) {
    assert.expect(1);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
    });
    await this.start();

    const threadGeneral = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 && thread.model === 'mail.channel'
    );
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-local-id="${
            threadGeneral.localId
        }"]`).click()
    );
    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${threadGeneral.localId}"]`,
        "The channel #General is displayed in discuss"
    );
});

QUnit.test('sidebar: pinned channel 3: open pinned channel and unpin it', async function (assert) {
    assert.expect(8);

    const channel = {
        channel_type: "channel",
        id: 20,
        is_minimized: false,
        is_pinned: true,
        name: "General",
        uuid: 'general',
        state: 'closed',
    };

    this.data['mail.channel'].records = [channel];
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [channel],
        },
    });

    const self = this;
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'execute_command') {
                assert.step('execute_command');
                assert.deepEqual(args.args[0], [20],
                    "The right id is sent to the server to remove"
                );
                assert.strictEqual(args.args[1], 'leave',
                    "The right command is sent to the server"
                );
            }
            if (args.method === 'channel_fold') {
                assert.step('channel_fold');
            }
            return this._super(...arguments);
        },
    });

    const threadGeneral = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 && thread.model === 'mail.channel'
    );
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-local-id="${
            threadGeneral.localId
        }"]`).click()
    );
    assert.verifySteps([], "neither channel_fold nor execute_command are called yet");
    await afterNextRender(() =>
        document.querySelector('.o_DiscussSidebarItem_commandLeave').click()
    );
    assert.verifySteps(
        [
            'channel_fold',
            'execute_command'
        ],
        "both channel_fold and execute_command have been called when unpinning a channel"
    );
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarItem[data-thread-local-id="${threadGeneral.localId}"]`,
        "The channel must have been removed from discuss sidebar"
    );
    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${this.env.messaging.inbox.localId}"]`,
        "The Inbox is opened in discuss"
    );
});

QUnit.test('sidebar: unpin channel from bus', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                is_pinned: true,
                name: "General",
            }],
        },
    });

    await this.start();
    const threadGeneral = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 && thread.model === 'mail.channel'
    );

    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${this.env.messaging.inbox.localId}"]`,
        "The Inbox is opened in discuss"
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarItem[data-thread-local-id="${threadGeneral.localId}"]`,
        "1 channel is present in discuss sidebar and it is 'general'"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarItem[data-thread-local-id="${
            threadGeneral.localId
        }"]`).click()
    );
    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${threadGeneral.localId}"]`,
        "The channel #General is opened in discuss"
    );

    // Simulate receiving a leave channel notification
    // (e.g. from user interaction from another device or browser tab)
    await afterNextRender(() => {
        const notif = [
            ["dbName", 'res.partner', this.env.messaging.currentPartner.id],
            {
                channel_type: 'channel',
                id: 20,
                info: 'unsubscribe',
                name: "General",
                public: 'public',
                state: 'open',
            }
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_Discuss_thread[data-thread-local-id="${this.env.messaging.inbox.localId}"]`,
        "The Inbox is opened in discuss"
    );
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarItem[data-thread-local-id="${threadGeneral.localId}"]`,
        "The channel must have been removed from discuss sidebar"
    );
});

QUnit.test('sidebar: channel group_based_subscription: mandatorily pinned', async function (assert) {
    assert.expect(2);

    // FIXME: The following is admittedly odd.
    // Fixing it should entail a deeper reflexion on the group_based_subscription
    // and is_pinned functionalities, especially in python.
    // task-2284357

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                group_based_subscription: true,
                id: 20,
                is_pinned: false,
                name: "General",
            }],
        },
    });
    await this.start();
    const threadGeneral = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 && thread.model === 'mail.channel'
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarItem[data-thread-local-id="${threadGeneral.localId}"]`,
        "The channel #General is in discuss sidebar"
    );
    assert.containsNone(
        document.body,
        'o_DiscussSidebarItem_commandLeave',
        "The group_based_subscription channel is not unpinnable"
    );
});

});
});
});

});
