odoo.define('mail/static/src/components/chat_window_manager/chat_window_manager_tests.js', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    inputFiles,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const {
    file: { createFile },
    dom: { triggerEvent },
} = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({
                hasChatWindow: true,
                hasMessagingMenu: true,
            }, params, {
                data: this.data,
            }));
            this.debug = params && params.debug;
            this.env = env;
            this.widget = widget;
        };

        /**
         * Simulates the external behaviours & DOM changes implied by hiding home menu.
         * Needed to assert validity of tests at technical level (actual code of home menu could not
         * be used in these tests).
         */
        this.hideHomeMenu = async () => {
            await this.env.bus.trigger('will_hide_home_menu');
            await this.env.bus.trigger('hide_home_menu');
        };

        /**
         * Simulates the external behaviours & DOM changes implied by showing home menu.
         * Needed to assert validity of tests at technical level (actual code of home menu could not
         * be used in these tests).
         */
        this.showHomeMenu = async () => {
            await this.env.bus.trigger('will_show_home_menu');
            const $frag = document.createDocumentFragment();
            // in real condition, chat window will be removed and put in a fragment then
            // reinserted into DOM
            const selector = this.debug ? 'body' : '#qunit-fixture';
            $(selector).contents().appendTo($frag);
            await this.env.bus.trigger('show_home_menu');
            $(selector).append($frag);
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    },
});

QUnit.test('initial mount', async function (assert) {
    assert.expect(1);

    await this.start();
    assert.strictEqual(document.querySelectorAll('.o_ChatWindowManager').length,
        1,
        "should have chat window manager");
});

QUnit.test('chat window new message: basic rendering', async function (assert) {
    assert.expect(10);

    await this.start({
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
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_header`).length,
        1,
        "should have a header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_header .o_ChatWindowHeader_name`).length,
        1,
        "should have name part in header"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatWindow_header .o_ChatWindowHeader_name`).textContent,
        "New message",
        "should display 'new message' in the header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_header .o_ChatWindowHeader_command`).length,
        1,
        "should have 1 command in header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_header .o_ChatWindowHeader_commandClose`).length,
        1,
        "should have command to close chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_newMessageForm`).length,
        1,
        "should have a new message chat window container"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_newMessageFormLabel`).length,
        1,
        "should have a part in selection with label"
    );
    assert.strictEqual(
        document.querySelector(`.o_ChatWindow_newMessageFormLabel`).textContent.trim(),
        "To:",
        "should have label 'To:' in selection"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow_newMessageFormInput`).length,
        1,
        "should have an input in selection"
    );
});

QUnit.test('chat window new message: focused on open', async function (assert) {
    assert.expect(2);

    await this.start({
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
    assert.ok(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-focused'),
        "chat window should be focused"
    );
    assert.ok(
        document.activeElement,
        document.querySelector(`.o_ChatWindow_newMessageFormInput`),
        "chat window focused = selection input focused"
    );
});

QUnit.test('chat window new message: close', async function (assert) {
    assert.expect(1);

    await this.start({
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
    await afterNextRender(() =>
        document.querySelector(`.o_ChatWindow_header .o_ChatWindowHeader_commandClose`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        0,
        "chat window should be closed"
    );
});

QUnit.test('chat window new message: fold', async function (assert) {
    assert.expect(6);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_newMessageButton`).click()
    );
    assert.doesNotHaveClass(
        document.querySelector(`.o_ChatWindow`),
        'o-folded',
        "chat window should not be folded by default"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_newMessageForm',
        "chat window should have new message form"
    );

    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
    assert.hasClass(
        document.querySelector(`.o_ChatWindow`),
        'o-folded',
        "chat window should become folded"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow_newMessageForm',
        "chat window should not have new message form"
    );

    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
    assert.doesNotHaveClass(
        document.querySelector(`.o_ChatWindow`),
        'o-folded',
        "chat window should become unfolded"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_newMessageForm',
        "chat window should have new message form"
    );
});

QUnit.test('chat window: basic rendering', async function (assert) {
    assert.expect(11);

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
                }];
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`.o_NotificationList_preview`).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    const chatWindow = document.querySelector(`.o_ChatWindow`);
    assert.strictEqual(
        chatWindow.dataset.threadLocalId,
        this.env.models['mail.thread'].find(thread =>
            thread.id === 20 &&
            thread.model === 'mail.channel'
        ).localId,
        "should have open a chat window of channel"
    );
    assert.strictEqual(
        chatWindow.querySelectorAll(`:scope .o_ChatWindow_header`).length,
        1,
        "should have header part"
    );
    const chatWindowHeader = chatWindow.querySelector(`:scope .o_ChatWindow_header`);
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ThreadIcon`).length,
        1,
        "should have thread icon in header part"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_name`).length,
        1,
        "should have thread name in header part"
    );
    assert.strictEqual(
        chatWindowHeader.querySelector(`:scope .o_ChatWindowHeader_name`).textContent,
        "General",
        "should have correct thread name in header part"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_command`).length,
        2,
        "should have 2 commands in header part"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_commandExpand`).length,
        1,
        "should have command to expand thread in discuss"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_commandClose`).length,
        1,
        "should have command to close chat window"
    );
    assert.strictEqual(
        chatWindow.querySelectorAll(`:scope .o_ChatWindow_thread`).length,
        1,
        "should have part to display thread content inside chat window"
    );
    assert.ok(
        chatWindow.querySelector(`:scope .o_ChatWindow_thread`).classList.contains('o_ThreadViewer'),
        "thread viewer part should use component ThreadViewer"
    );
});

QUnit.test('chat window: fold', async function (assert) {
    assert.expect(27);

    let foldCall = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
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
                }];
            } else if (args.method === 'channel_fold') {
                assert.step(`rpc:${args.method}/${args.kwargs.state}`);
                foldCall++;
                const kwargsKeys = Object.keys(args.kwargs);
                assert.strictEqual(
                    args.args.length,
                    0,
                    "channel_fold call have no args"
                );
                assert.strictEqual(
                    kwargsKeys.length,
                    2,
                    "channel_fold call have exactly 2 kwargs"
                );
                assert.ok(
                    kwargsKeys.includes('state'),
                    "channel_fold call have 'state' kwargs"
                );
                assert.ok(
                    kwargsKeys.includes('uuid'),
                    "channel_fold call have 'uuid' kwargs"
                );
                assert.strictEqual(
                    args.kwargs.uuid,
                    'channel-20-uuid',
                    "channel_fold call uuid is from channel 20"
                );
                if (foldCall % 2 === 0) {
                    assert.strictEqual(
                        args.kwargs.state,
                        'folded',
                        "channel_fold call state is 'folded'"
                    );
                } else {
                    assert.strictEqual(
                        args.kwargs.state,
                        'open',
                        "channel_fold call state is 'open'"
                    );
                }
                return [];
            }
            return this._super(...arguments);
        },
    });
    // Open Thread
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should have a thread viewer"
    );
    assert.verifySteps(['rpc:channel_fold/open']);

    // Fold chat window
    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
    assert.verifySteps(['rpc:channel_fold/folded']);
    assert.containsNone(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should not have any thread viewer"
    );

    // Unfold chat window
    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
    assert.verifySteps(['rpc:channel_fold/open']);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should have a thread viewer"
    );
});

QUnit.test('chat window: open / close', async function (assert) {
    assert.expect(24);

    let foldCall = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
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
                }];
            } else if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
                foldCall++;
                const kwargsKeys = Object.keys(args.kwargs);
                assert.strictEqual(
                    args.args.length,
                    0,
                    "channel_fold call have no args"
                );
                assert.strictEqual(
                    kwargsKeys.length,
                    2,
                    "channel_fold call have exactly 2 kwargs"
                );
                assert.ok(
                    kwargsKeys.includes('state'),
                    "channel_fold call have 'state' kwargs"
                );
                assert.ok(
                    kwargsKeys.includes('uuid'),
                    "channel_fold call have 'uuid' kwargs"
                );
                assert.strictEqual(
                    args.kwargs.uuid,
                    'channel-20-uuid',
                    "channel_fold call uuid should be correct"
                );
                if (foldCall % 2 === 0) {
                    assert.strictEqual(
                        args.kwargs.state,
                        'closed',
                        "channel_fold call state is 'closed'"
                    );
                } else {
                    assert.strictEqual(
                        args.kwargs.state,
                        'open',
                        "channel_fold call state is 'open'"
                    );
                }
                return [];
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.verifySteps(['rpc:channel_fold/open']);

    // Close chat window
    await afterNextRender(() => document.querySelector(`.o_ChatWindowHeader_commandClose`).click());
    assert.verifySteps(['rpc:channel_fold/closed']);

    // Reopen chat window
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.verifySteps(['rpc:channel_fold/open']);
});

QUnit.test('chat window: close on ESCAPE', async function (assert) {
    assert.expect(12);

    this.data['res.partner'].records = [{
        email: "testpartnert@odoo.com",
        id: 11,
        name: "TestPartner",
    }];
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
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
                }];
            } else if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
                return [];
            }
            return this._super(...arguments);
        },
    });
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    assert.verifySteps(['rpc:channel_fold/open']);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should be opened after click on preview"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_Composer_buttonEmojis`).click()
    );
    assert.containsOnce(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be opened after click on emojis button"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_Composer_buttonEmojis`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_EmojisPopover',
        "emojis popover should be closed after pressing escape on emojis button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should still be opened after pressing escape on emojis button"
    );

    await afterNextRender(() => {
        document.execCommand('insertText', false, "@");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
    assert.containsOnce(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestion should be opened after typing @"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ComposerTextInput_mentionDropdownPropositionList',
        "mention suggestion should be closed after pressing escape on mention suggestion"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should still be opened after pressing escape on mention suggestion"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "chat window should be closed after pressing escape if there was no other priority escape handler"
    );
    assert.verifySteps(['rpc:channel_fold/closed']);
});

QUnit.test('focus next visible chat window when closing current chat window with ESCAPE', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: @see `mail/static/src/utils/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager/chat_window_manager.js:visual)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1920px
     *
     * Enough space for 2 visible chat windows:
     *  10 + 325 + 5 + 325 + 10 = 670 < 1920
     */
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [
                {
                    channel_type: 'channel',
                    id: 20,
                    is_minimized: true,
                    is_pinned: true,
                    name: "General",
                    state: 'open',
                    uuid: 'channel-20-uuid',
                },
                {
                    channel_type: 'channel',
                    id: 21,
                    is_minimized: true,
                    is_pinned: true,
                    name: "other chat",
                    state: 'open',
                    uuid: 'channel-21-uuid',
                },
            ],
        },
    });
    await this.start({
        env: {
            browser: {
                innerWidth: 1920,
            },
        },
    });
    assert.containsN(
        document.body,
        '.o_ChatWindow .o_ComposerTextInput_textarea',
        2,
        "initialy, 2 chat windows should be present"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow.o-folded',
        "both chat windows should be open"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: 'Escape' });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(ev);
    });
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "only one chat window should remain after pressing escape on first chat window"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow'),
        'o-focused',
        "next visible chat window should be focused after pressing escape on first chat window"
    );
});


QUnit.test('[technical] chat window: composer state conservation on toggle home menu', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(6);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
            }],
        },
    });
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    // Set content of the composer of the chat window
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, 'XDU for the win !');
    });
    // Set attachments of the composer
    const files = [
        await createFile({
            name: 'text state conservation on toggle home menu.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        }),
        await createFile({
            name: 'text2 state conservation on toggle home menu.txt',
            content: 'hello, xdu is da best man',
            contentType: 'text/plain',
        })
    ];
    await afterNextRender(() =>
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
            files
        )
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "chat window composer initial text input should contain 'XDU for the win !'"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "verify chat window composer initial attachment count"
    );

    await this.hideHomeMenu();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "Chat window composer should still have the same input after hiding home menu"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "Chat window composer should have 2 attachments after hiding home menu"
    );

    // Show home menu
    await this.showHomeMenu();
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "chat window composer should still have the same input showing home menu"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "Chat window composer should have 2 attachments showing home menu"
    );
});

QUnit.test('[technical] chat window: scroll conservation on toggle home menu', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
            }],
        },
    });
    this.data['mail.message'].records = [];
    for (const i of Array(20).keys()) {
        this.data['mail.message'].records.push({
            author_id: [7, "Demo"],
            body: "<p>body</p>",
            channel_ids: [20],
            date: "2019-04-20 10:00:00",
            id: i + 10,
            message_type: 'comment',
            model: 'mail.channel',
            record_name: "General",
            res_id: 20,
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    // Set a scroll position to chat window
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 142;
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window initial scrollTop should be 142px"
    );

    await afterNextRender(() => this.hideHomeMenu());
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is hidden"
    );

    await afterNextRender(() => this.showHomeMenu());
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is shown"
    );
});

QUnit.test('open 2 different chat windows: enough screen width [REQUIRE FOCUS]', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: @see `mail/static/src/utils/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager/chat_window_manager.js:visual)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1920px
     *
     * Enough space for 2 visible chat windows:
     *  10 + 325 + 5 + 325 + 10 = 670 < 1920
     */
    assert.expect(8);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 20,
                is_pinned: true,
                name: "General",
            }],
            channel_direct_message: [{
                channel_type: "chat",
                direct_partner: [{
                    id: 7,
                    name: "Demo",
                }],
                id: 10,
                is_pinned: true,
            }],
        },
    });
    await this.start({
        env: {
            browser: {
                innerHeight: 1080,
                innerWidth: 1920,
            },
        },
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
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "chat window of chat should be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should have focus"
    );

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        2,
        "should have open a new chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "chat window of channel should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "chat window of chat should still be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 20 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel should have focus"
    );
    assert.notOk(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 10 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should no longer have focus"
    );
});

QUnit.test('open 2 chat windows: check shift operations are available', async function (assert) {
    assert.expect(9);

    const channel = {
        channel_type: "channel",
        id: 20,
        is_pinned: true,
        name: "General",
    };
    const chat = {
        channel_type: "chat",
        direct_partner: [{
            id: 7,
            name: "Demo",
        }],
        id: 10,
        is_pinned: true,
    };
    this.data['mail.channel'].records = [channel, chat];
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [channel],
            channel_direct_message: [chat],
        },
    });
    await this.start();
    await afterNextRender(() => {
        document.querySelector('.o_MessagingMenu_toggler').click();
    });
    await afterNextRender(() => {
        document.querySelectorAll('.o_MessagingMenu_dropdownMenu .o_NotificationList_preview')[0].click();
    });
    await afterNextRender(() => {
        document.querySelector('.o_MessagingMenu_toggler').click();
    });
    await afterNextRender(() => {
        document.querySelectorAll('.o_MessagingMenu_dropdownMenu .o_NotificationList_preview')[1].click();
    });

    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "should have opened 2 chat windows"
    );
    assert.containsOnce(
        document.querySelectorAll('.o_ChatWindow')[0],
        '.o_ChatWindowHeader_commandShiftLeft',
        "first chat window should be allowed to shift left"
    );
    assert.containsNone(
        document.querySelectorAll('.o_ChatWindow')[0],
        '.o_ChatWindowHeader_commandShiftRight',
        "first chat window should not be allowed to shift right"
    );
    assert.containsNone(
        document.querySelectorAll('.o_ChatWindow')[1],
        '.o_ChatWindowHeader_commandShiftLeft',
        "second chat window should not be allowed to shift left"
    );
    assert.containsOnce(
        document.querySelectorAll('.o_ChatWindow')[1],
        '.o_ChatWindowHeader_commandShiftRight',
        "second chat window should be allowed to shift right"
    );

    const initialFirstChatWindowThreadLocalId =
        document.querySelectorAll('.o_ChatWindow')[0].dataset.threadLocalId;
    const initialSecondChatWindowThreadLocalId =
        document.querySelectorAll('.o_ChatWindow')[1].dataset.threadLocalId;
    await afterNextRender(() => {
        document.querySelectorAll('.o_ChatWindow')[0]
            .querySelector(':scope .o_ChatWindowHeader_commandShiftLeft')
            .click();
    });
    assert.strictEqual(
        document.querySelectorAll('.o_ChatWindow')[0].dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "First chat window should be second after it has been shift left"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_ChatWindow')[1].dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "Second chat window should be first after the first has been shifted left"
    );

    await afterNextRender(() => {
        document.querySelectorAll('.o_ChatWindow')[1]
            .querySelector(':scope .o_ChatWindowHeader_commandShiftRight')
            .click();
    });
    assert.strictEqual(
        document.querySelectorAll('.o_ChatWindow')[0].dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "First chat window should be back at first place after being shifted left then right"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_ChatWindow')[1].dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "Second chat window should be back at second place after first one has been shifted left then right"
    );
});

QUnit.test('open 3 different chat windows: not enough screen width', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see `mail/static/src/models/chat_window_manager/chat_window_manager.js:visual`)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1080px
     *
     * Enough space for 2 visible chat windows, and one hidden chat window:
     * 3 visible chat windows:
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 900
     * 2 visible chat windows + hidden menu:
     *  10 + 325 + 5 + 325 + 10 + 200 + 5 = 875 < 900
     */
    assert.expect(12);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 1,
                is_pinned: true,
                name: "channel1",
            }, {
                channel_type: "channel",
                id: 2,
                is_pinned: true,
                name: "channel2",
            }, {
                channel_type: "channel",
                id: 3,
                is_pinned: true,
                name: "channel3",
            }],
        },
    });
    await this.start({
        env: {
            browser: {
                innerHeight: 900,
                innerWidth: 900,
            },
        },
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });

    // open, from systray menu, chat windows of channels with Id 1, 2, then 3
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 1 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open 1 visible chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindowManager_hiddenMenu`).length,
        0,
        "should not have hidden menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu`).length,
        0,
        "messaging menu should be hidden"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 2 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        2,
        "should have open 2 visible chat windows"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindowManager_hiddenMenu`).length,
        0,
        "should not have hidden menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu`).length,
        0,
        "messaging menu should be hidden"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 3 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).click()
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        2,
        "should have open 2 visible chat windows"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindowManager_hiddenMenu`).length,
        1,
        "should have hidden menu"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu`).length,
        0,
        "messaging menu should be hidden"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 1 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "chat window of channel 1 should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 3 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).length,
        1,
        "chat window of channel 3 should be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 3 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel 3 should have focus"
    );
});

QUnit.test('chat window: switch on TAB', async function (assert) {
    assert.expect(10);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: "channel",
                id: 1,
                is_pinned: true,
                name: "channel1",
            }, {
                channel_type: "channel",
                id: 2,
                is_pinned: true,
                name: "channel2",
            }],
        },
    });
    await this.start();

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 1 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]`
        ).click()
    );

    assert.containsOnce(document.body, '.o_ChatWindow', "Only 1 chatWindow must be opened");
    const chatWindow = document.querySelector('.o_ChatWindow');
    assert.strictEqual(
        chatWindow.querySelector('.o_ChatWindowHeader_name').textContent,
        'channel1',
        "The name of the only chatWindow should be 'channel1' (channel with ID 1)"
    );
    assert.strictEqual(
        chatWindow.querySelector('.o_ComposerTextInput_textarea'),
        document.activeElement,
        "The chatWindow composer must have focus"
    );

    await afterNextRender(() =>
        triggerEvent(
            chatWindow.querySelector('.o_ChatWindow .o_ComposerTextInput_textarea'),
            'keydown',
            { key: 'Tab' },
        )
    );
    assert.strictEqual(
        chatWindow.querySelector('.o_ChatWindow .o_ComposerTextInput_textarea'),
        document.activeElement,
        "The chatWindow composer still has focus"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].find(thread =>
                    thread.id === 2 &&
                    thread.model === 'mail.channel'
                ).localId
            }"]`
        ).click()
    );

    assert.containsN(document.body, '.o_ChatWindow', 2, "2 chatWindows must be opened");
    const chatWindows = document.querySelectorAll('.o_ChatWindow');
    assert.strictEqual(
        chatWindows[0].querySelector('.o_ChatWindowHeader_name').textContent,
        'channel1',
        "The name of the 1st chatWindow should be 'channel1' (channel with ID 1)"
    );
    assert.strictEqual(
        chatWindows[1].querySelector('.o_ChatWindowHeader_name').textContent,
        'channel2',
        "The name of the 2nd chatWindow should be 'channel2' (channel with ID 2)"
    );
    assert.strictEqual(
        chatWindows[1].querySelector('.o_ComposerTextInput_textarea'),
        document.activeElement,
        "The 2nd chatWindow composer must have focus (channel with ID 2)"
    );

    await afterNextRender(() =>
        triggerEvent(
            chatWindows[1].querySelector('.o_ComposerTextInput_textarea'),
            'keydown',
            { key: 'Tab' },
        )
    );
    assert.containsN(document.body, '.o_ChatWindow', 2, "2 chatWindows should still be opened");
    assert.strictEqual(
        chatWindows[0].querySelector('.o_ComposerTextInput_textarea'),
        document.activeElement,
        "The 1st chatWindow composer must have focus (channel with ID 1)"
    );
});

QUnit.test('chat window with a thread: keep scroll position in message list on folded', async function (assert) {
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
            }],
        },
    });
    this.data['mail.message'].records = [];
    for(const i of Array(20).keys()) {
        this.data['mail.message'].records.push({
            author_id: [7, "Demo"],
            body: "<p>body</p>",
            channel_ids: [20],
            date: "2019-04-20 10:00:00",
            id: i,
            message_type: 'comment',
            model: 'mail.channel',
            record_name: "General",
            res_id: 20,
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_NotificationList_preview`).click()
    );
    // Set a scroll position to chat window
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 142;
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "verify chat window initial scrollTop"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.containsNone(
        document.body,
        ".o_ThreadViewer",
        "chat window should be folded so no thread viewer should be present"
    );

    // unfold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same when chat window is unfolded"
    );
});

QUnit.test('[technical] chat window: composer state conservation on toggle home menu when folded', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(6);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
            }],
        },
    });
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    // Set content of the composer of the chat window
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, 'XDU for the win !');
    });
    // Set attachments of the composer
    const files = [
        await createFile({
            name: 'text state conservation on toggle home menu.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        }),
        await createFile({
            name: 'text2 state conservation on toggle home menu.txt',
            content: 'hello, xdu is da best man',
            contentType: 'text/plain',
        })
    ];
    await afterNextRender(() =>
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
            files
        )
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "verify chat window composer initial html input"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "verify chat window composer initial attachment count"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    await this.hideHomeMenu();
    // unfold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "Chat window composer should still have the same input after hiding home menu"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "Chat window composer should have 2 attachments after hiding home menu"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    await this.showHomeMenu();
    // unfold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "chat window composer should still have the same input after showing home menu"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_Attachment',
        2,
        "Chat window composer should have 2 attachments after showing home menu"
    );
});

QUnit.test('[technical] chat window with a thread: keep scroll position in message list on toggle home menu when folded', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(3);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
                is_pinned: true,
                name: "General",
                state: 'open',
                uuid: 'channel-20-uuid',
            }],
        },
    });
    this.data['mail.message'].records = [];
    for (const i of Array(20).keys()) {
        this.data['mail.message'].records.push({
            author_id: [7, "Demo"],
            body: "<p>body</p>",
            channel_ids: [20],
            date: "2019-04-20 10:00:00",
            id: i + 10,
            message_type: 'comment',
            model: 'mail.channel',
            record_name: "General",
            res_id: 20,
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
    // Set a scroll position to chat window
    document.querySelector(`.o_ThreadViewer_messageList`).scrollTop = 142;
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "should have scrolled to 142px"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    await this.hideHomeMenu();
    // unfold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is hidden"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    // Show home menu
    await this.showHomeMenu();
    // unfold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.strictEqual(
        document.querySelector(`.o_ThreadViewer_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is shown"
    );
});

});
});
});

});
