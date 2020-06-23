odoo.define('mail/static/src/components/messaging_menu/messaging_menu_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const { makeTestPromise } = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu', {}, function () {
QUnit.module('messaging_menu_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { discussWidget, env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
                hasMessagingMenu: true,
            }));
            this.discussWidget = discussWidget;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    },
});

QUnit.test('messaging not initialized', async function (assert) {
    assert.expect(2);

    await this.start({
        async mockRPC(route) {
            if (route === '/mail/init_messaging') {
                // simulate messaging never initialized
                return new Promise(resolve => {});
            }
            return this._super(...arguments);
        },
        waitUntilMessagingInitialized: false,
    });
    assert.strictEqual(
        document.querySelectorAll('.o_MessagingMenu_loading').length,
        1,
        "should display loading icon on messaging menu when messaging not yet initialized"
    );

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_dropdownMenu').textContent,
        "Please wait...",
        "should prompt loading when opening messaging menu"
    );
});

QUnit.test('messaging becomes initialized', async function (assert) {
    assert.expect(2);

    const messagingInitializedProm = makeTestPromise();

    await this.start({
        async mockRPC(route) {
            const _super = this._super.bind(this, ...arguments); // limitation of class.js
            if (route === '/mail/init_messaging') {
                await messagingInitializedProm;
            }
            return _super();
        },
        waitUntilMessagingInitialized: false,
    });
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());

    // simulate messaging becomes initialized
    await afterNextRender(() => messagingInitializedProm.resolve());
    assert.strictEqual(
        document.querySelectorAll('.o_MessagingMenu_loading').length,
        0,
        "should no longer display loading icon on messaging menu when messaging becomes initialized"
    );
    assert.notOk(
        document.querySelector('.o_MessagingMenu_dropdownMenu').textContent.includes("Please wait..."),
        "should no longer prompt loading when opening messaging menu when messaging becomes initialized"
    );
});

QUnit.test('basic rendering', async function (assert) {
    assert.expect(21);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });
    assert.strictEqual(
        document.querySelectorAll('.o_MessagingMenu').length,
        1,
        "should have messaging menu"
    );
    assert.notOk(
        document.querySelector('.o_MessagingMenu').classList.contains('show'),
        "should not mark messaging menu item as shown by default"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_toggler`).length,
        1,
        "should have clickable element on messaging menu"
    );
    assert.notOk(
        document.querySelector(`.o_MessagingMenu_toggler`).classList.contains('show'),
        "should not mark messaging menu clickable item as shown by default"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_icon`).length,
        1,
        "should have icon on clickable element in messaging menu"
    );
    assert.ok(
        document.querySelector(`.o_MessagingMenu_icon`).classList.contains('fa-comments'),
        "should have 'comments' icon on clickable element in messaging menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu`).length,
        0,
        "should not display any messaging menu dropdown by default"
    );

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.hasClass(
        document.querySelector('.o_MessagingMenu'),
        "o-is-open",
        "should mark messaging menu as opened"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu`).length,
        1,
        "should display messaging menu dropdown after click"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenuHeader`).length,
        1,
        "should have dropdown menu header"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenuHeader
            .o_MessagingMenu_tabButton
        `).length,
        3,
        "should have 3 tab buttons to filter items in the header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="all"]`).length,
        1,
        "1 tab button should be 'All'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="chat"]`).length,
        1,
        "1 tab button should be 'Chat'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="channel"]`).length,
        1,
        "1 tab button should be 'Channels'"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should not be active"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        1,
        "should have button to make a new message"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList
        `).length,
        1,
        "should display thread preview list"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_noConversation
        `).length,
        1,
        "should display no conversation in thread preview list"
    );

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.doesNotHaveClass(
        document.querySelector('.o_MessagingMenu'),
        "o-is-open",
        "should mark messaging menu as closed"
    );
});

QUnit.test('counter is taking into account failure notification', async function (assert) {
    assert.expect(2);

    this.data.initMessaging.mail_failures = [{
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 11,
        message_type: 'email',
        model: 'mail.channel',
        notifications: [{
            failure_type: 'SMTP',
            id: 21,
            notification_status: 'exception',
            notification_type: 'email',
            partner_id: [41, "Someone"],
        }],
        res_id: 31,
        res_model_name: "Channel",
    }];
    await this.start();

    assert.containsOnce(
        document.body,
        '.o_MessagingMenu_counter',
        "should display a notification counter next to the messaging menu for one notification"
    );
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_counter').textContent,
        "1",
        "should display a counter of '1' next to the messaging menu"
    );
});

QUnit.test('switch tab', async function (assert) {
    assert.expect(15);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="all"]`).length,
        1,
        "1 tab button should be 'All'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="chat"]`).length,
        1,
        "1 tab button should be 'Chat'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_tabButton[data-tab-id="channel"]`).length,
        1,
        "1 tab button should be 'Channels'"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should not be active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_tabButton[data-tab-id="chat"]`).click()
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not become active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should stay inactive"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_tabButton[data-tab-id="channel"]`).click()
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should stay active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should become active"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_tabButton[data-tab-id="all"]`).click()
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should become active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should stay inactive"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenu_tabButton[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should become inactive"
    );
});

QUnit.test('new message', async function (assert) {
    assert.expect(3);

    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_newMessageButton`).click()
    );

    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    assert.ok(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-new-message'),
        "chat window should be for new message"
    );
    assert.ok(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-focused'),
        "chat window should be focused"
    );
});

QUnit.test('no new message when discuss is open', async function (assert) {
    assert.expect(3);

    await this.start({
        autoOpenDiscuss: true,
        hasDiscuss: true,
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        0,
        "should not have 'new message' when discuss is open"
    );

    // simulate closing discuss app
    await afterNextRender(() => this.discussWidget.on_detach_callback());
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        1,
        "should have 'new message' when discuss is closed"
    );

    // simulate opening discuss app
    await afterNextRender(() => this.discussWidget.on_attach_callback());
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        0,
        "should not have 'new message' when discuss is open again"
    );
});

QUnit.test('channel preview: basic rendering', async function (assert) {
    assert.expect(9);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [{
                    id: 20,
                    last_message: {
                        author_id: [7, "Demo"],
                        body: "<p>test</p>",
                        channel_ids: [20],
                        id: 100,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: "General",
                        res_id: 20,
                    },
                }];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu .o_ThreadPreview
        `).length,
        1,
        "should have one preview"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_sidebar
        `).length,
        1,
        "preview should have a sidebar"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_content
        `).length,
        1,
        "preview should have some content"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_header
        `).length,
        1,
        "preview should have header in content"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_header
            .o_ThreadPreview_name
        `).length,
        1,
        "preview should have name in header of content"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_name
        `).textContent,
        "General", "preview should have name of channel"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_content
            .o_ThreadPreview_core
        `).length,
        1,
        "preview should have core in content"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_core
            .o_ThreadPreview_inlineText
        `).length,
        1,
        "preview should have inline text in core of content"
    );
    assert.strictEqual(
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview_core
            .o_ThreadPreview_inlineText
        `).textContent.trim(),
        "Demo: test",
        "preview should have message content as inline text of core content"
    );
});

QUnit.test('filtered previews', async function (assert) {
    assert.expect(12);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo",
                }],
                id: 10,
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [{
                    id: 20,
                    last_message: {
                        author_id: [7, "Demo"],
                        body: "<p>test</p>",
                        channel_ids: [20],
                        id: 100,
                        message_type: 'comment',
                        model: 'mail.channel',
                        res_id: 20,
                    },
                }, {
                    id: 10,
                    last_message: {
                        author_id: [7, "Demo"],
                        body: "<p>test2</p>",
                        channel_ids: [10],
                        id: 101,
                        message_type: 'comment',
                        model: 'mail.channel',
                        res_id: 10,
                    },
                }];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        2,
        "should have 2 previews"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of channel"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="chat"]').click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        1,
        "should have one preview"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        0,
        "should not have preview of channel"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="channel"]').click()
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview
        `).length,
        1,
        "should have one preview"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        0,
        "should not have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of channel"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="all"]').click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        2,
        "should have 2 previews"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "should have preview of channel"
    );
});

QUnit.test('open chat window from preview', async function (assert) {
    assert.expect(1);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                name: "General",
            }],
        },
    });
    await this.start({
        hasChatWindow: true,
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
});

QUnit.test('no code injection in message body preview', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 1,
                name: "General",
            }],
        },
    });

    this.data['mail.channel'].records = [{
        id: 1,
        name: "general",
        channel_type: "channel",
        channel_message_ids: [1],
    }];
    this.data['mail.message'].records = [{
        id: 1,
        author_id: [1, 'Georges'],
        body: "<p><em>&shoulnotberaised</em><script>throw new Error('CodeInjectionError');</script></p>",
        channel_ids: [1],
    }];

    await this.start();

    await afterNextRender(() => {
        document.querySelector(`.o_MessagingMenu_toggler`).click();
    });
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu_dropdownMenu .o_ThreadPreview',
        "should display a preview",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_core',
        "preview should have core in content",
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_inlineText',
        "preview should have inline text in core of content",
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_inlineText')
            .textContent.replace(/\s/g, ""),
        "Georges:&shoulnotberaisedthrownewError('CodeInjectionError');",
        "should display correct uninjected last message inline content"
    );
    assert.containsNone(
        document.querySelector('.o_ThreadPreview_inlineText'),
        'script',
        "last message inline content should not have any code injection"
    );
});

});
});
});

});
