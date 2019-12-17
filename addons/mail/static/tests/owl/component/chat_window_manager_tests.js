odoo.define('mail.component.ChatWindowManagerTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    inputFiles,
    pause,
    start: utilsStart,
} = require('mail.messagingTestUtils');

const { file: { createFile } } = require('web.test_utils');

QUnit.module('mail.messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('ChatWindowManager', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
                hasChatWindow: true,
                hasMessagingMenu: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    }
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
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_newMessageButton`).click();
    await afterNextRender();
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
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_newMessageButton`).click();
    await afterNextRender();
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
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_newMessageButton`).click();
    await afterNextRender();
    document.querySelector(`.o_ChatWindow_header .o_ChatWindowHeader_commandClose`).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        0,
        "chat window should be closed"
    );
});

QUnit.test('chat window new message: fold', async function (assert) {
    assert.expect(3);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_newMessageButton`).click();
    await afterNextRender();
    assert.notOk(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-folded'),
        "chat window should not be folded by default"
    );

    document.querySelector(`.o_ChatWindow_header`).click();
    await afterNextRender();
    assert.ok(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-folded'),
        "chat window should become folded"
    );

    document.querySelector(`.o_ChatWindow_header`).click();
    await afterNextRender();
    assert.notOk(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-folded'),
        "chat window should become unfolded"
    );
});

QUnit.test('chat window: basic rendering', async function (assert) {
    assert.expect(11);

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
                        res_id: 20,
                    },
                }];
            }
            return this._super(...arguments);
        },
    });
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_dropdownMenu .o_ThreadPreviewList_preview`).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    const chatWindow = document.querySelector(`.o_ChatWindow`);
    assert.strictEqual(
        chatWindow.dataset.threadLocalId,
        'mail.channel_20',
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
        chatWindow.querySelector(`:scope .o_ChatWindow_thread`).classList.contains('o_Thread'),
        "thread part should use component thread"
    );
});

QUnit.test('chat window: fold', async function (assert) {
    assert.expect(15);

    let foldCall = 0;
    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
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
                if (foldCall % 2 === 1) {
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
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_dropdownMenu .o_ThreadPreviewList_preview`).click();
    await afterNextRender();
    // Fold chat window
    document.querySelector(`.o_ChatWindow_header`).click();
    await afterNextRender();
    // Unfold chat window
    document.querySelector(`.o_ChatWindow_header`).click();
    await afterNextRender();
    assert.verifySteps(
        [
            'rpc:channel_fold/folded',
            'rpc:channel_fold/open'
        ],
        "RPC should be done in this order: , channel_fold (folded), channel_fold (open)"
    );
});

QUnit.test('chat window: open / close', async function (assert) {
    assert.expect(20);

    async function openThread() {
        document.querySelector(`.o_MessagingMenu_toggler`).click();
        await afterNextRender();
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_ThreadPreviewList_preview`).click();
        await afterNextRender();
    }

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
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
                assert.strictEqual(
                    args.kwargs.state,
                    'closed',
                    "channel_fold call state is 'closed'"
                );
                return [];
            } else if (args.method === 'channel_minimize') {
                assert.step('rpc:channel_minimize');
                assert.strictEqual(
                    args.args.length,
                    2,
                    "channel_minimize call have exactly 2 args"
                );
                assert.strictEqual(
                    Object.keys(args.kwargs).length,
                    0,
                    "channel_minimize call have no kwargs"
                );
                assert.strictEqual(
                    args.args[0],
                    'channel-20-uuid',
                    "channel_minimize call first param is the channel uuid"
                );
                assert.ok(
                    args.args[1],
                    "channel_minimize call second param is true"
                );
                return [];
            }
            return this._super(...arguments);
        },
    });
    await openThread();
    assert.verifySteps(['rpc:channel_minimize']);

    // Close chat window
    document.querySelector(`.o_ChatWindowHeader_commandClose`).click();
    await afterNextRender();
    assert.verifySteps(['rpc:channel_fold/closed']);

    // Reopen chat window
    await openThread();
    assert.verifySteps(['rpc:channel_minimize']);
});

QUnit.test('chat window: state conservation on toggle home menu', async function (assert) {
    assert.expect(9);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_channel: [{
                channel_type: 'channel',
                id: 20,
                is_minimized: false,
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
                return;
            } else if (args.method === 'message_fetch') {
                return [...Array(20).keys()].map(i => {
                    return {
                        author_id: [11, "Demo"],
                        body: "<p>body</p>",
                        channel_ids: [20],
                        date: "2019-04-20 10:00:00",
                        id: i + 10,
                        message_type: 'comment',
                        model: 'mail.channel',
                        record_name: 'General',
                        res_id: i + 1,
                    };
                });
            }
            return this._super(...arguments);
        },
    });
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`.o_MessagingMenu_dropdownMenu .o_ThreadPreviewList_preview`).click();
    await afterNextRender();
    // Set a scroll position to chat window
    document.querySelector(`.o_Thread_messageList`).scrollTop = 142;
    // Set html content of the composer of the chat window
    let composerTextInputEditable = document.querySelector(`.o_ComposerTextInput_editable`);
    composerTextInputEditable.focus();
    document.execCommand('insertText', false, 'XDU for the win !');
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
    inputFiles(
        document.querySelector('.o_FileUploader_input'),
        files
    );
    await afterNextRender();
    assert.strictEqual(
        document.querySelector(`.o_Thread_messageList`).scrollTop,
        142,
        "verify chat window initial scrollTop"
    );
    composerTextInputEditable = document.querySelector(`.o_ComposerTextInput_editable`);
    assert.strictEqual(
        composerTextInputEditable.textContent,
        "XDU for the win !",
        "verifif chat window composer initial html input"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        2,
        "verify chat window composer initial attachment count"
    );
    // Hide home menu
    await this.widget.call('chat_window', '_onWillHideHomeMenu');
    await this.widget.call('chat_window', '_onHideHomeMenu');
    assert.strictEqual(
        document.querySelector(`.o_Thread_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same (1)"
    );
    composerTextInputEditable = document.querySelector(`.o_ComposerTextInput_editable`);
    assert.strictEqual(
        composerTextInputEditable.textContent,
        "XDU for the win !",
        "Chat window composer should still have the same html input (1)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        2,
        "Chat window composer should have 2 attachments (1)"
    );

    // Show home menu
    await this.widget.call('chat_window', '_onWillShowHomeMenu');
    await this.widget.call('chat_window', '_onShowHomeMenu');
    assert.strictEqual(
        document.querySelector(`.o_Thread_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same (2)"
    );
    composerTextInputEditable = document.querySelector(`.o_ComposerTextInput_editable`);
    assert.strictEqual(
        composerTextInputEditable.textContent,
        "XDU for the win !",
        "chat window composer should still have the same html input (2)"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_Composer .o_Attachment`).length,
        2,
        "Chat window composer should have 2 attachments (2)"
    );
});

QUnit.test('open 2 different chat windows: enough screen width', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: @see `mail.component.test_utils:create()` method)
     * (others: @see store action `_computeChatWindows`)
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
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`
        .o_MessagingMenu_dropdownMenu
        .o_ThreadPreviewList_preview[data-thread-local-id="mail.channel_10"]`).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow[data-thread-local-id="mail.channel_10"]`).length,
        1,
        "chat window of chat should be open"
    );
    assert.ok(
        document.querySelector(`.o_ChatWindow[data-thread-local-id="mail.channel_10"]`)
            .classList.contains('o-focused'),
        "chat window of chat should have focus"
    );

    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`
        .o_MessagingMenu_dropdownMenu
        .o_ThreadPreviewList_preview[data-thread-local-id="mail.channel_20"]`
    ).click();
    await afterNextRender();
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        2,
        "should have open a new chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow[data-thread-local-id="mail.channel_20"]`).length,
        1,
        "chat window of channel should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow[data-thread-local-id="mail.channel_10"]`).length,
        1,
        "chat window of chat should still be open"
    );
    assert.ok(
        document.querySelector(`.o_ChatWindow[data-thread-local-id="mail.channel_20"]`)
            .classList.contains('o-focused'),
        "chat window of channel should have focus"
    );
    assert.notOk(
        document.querySelector(`.o_ChatWindow[data-thread-local-id="mail.channel_10"]`)
            .classList.contains('o-focused'),
        "chat window of chat should no longer have focus"
    );
});

QUnit.test('open 3 different chat windows: not enough screen width', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see store action `_computeChatWindows`)
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
                name: "channel1",
            }, {
                channel_type: "channel",
                id: 2,
                name: "channel2",
            }, {
                channel_type: "channel",
                id: 3,
                name: "channel3",
            }],
        },
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'channel_fetch_preview') {
                return [];
            }
            return this._super(...arguments);
        },
    });
    Object.assign(this.env.store.state, {
        globalWindow: {
            innerHeight: 900,
            innerWidth: 900,
        },
        isMobile: false,
    });

    // open, from systray menu, chat windows of channels with Id 1, 2, then 3
    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`
        .o_MessagingMenu_dropdownMenu
        .o_ThreadPreviewList_preview[data-thread-local-id="mail.channel_1"]`
    ).click();
    await afterNextRender();
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

    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`
        .o_MessagingMenu_dropdownMenu
        .o_ThreadPreviewList_preview[data-thread-local-id="mail.channel_2"]`
    ).click();
    await afterNextRender();
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

    document.querySelector(`.o_MessagingMenu_toggler`).click();
    await afterNextRender();
    document.querySelector(`
        .o_MessagingMenu_dropdownMenu
        .o_ThreadPreviewList_preview[data-thread-local-id="mail.channel_3"]`
    ).click();
    await afterNextRender();
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
        document.querySelectorAll(`.o_ChatWindow[data-thread-local-id="mail.channel_1"]`).length,
        1,
        "chat window of channel 1 should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow[data-thread-local-id="mail.channel_3"]`).length,
        1,
        "chat window of channel 3 should be open"
    );
    assert.ok(
        document.querySelector(`.o_ChatWindow[data-thread-local-id="mail.channel_3"]`)
            .classList.contains('o-focused'),
        "chat window of channel 3 should have focus"
    );
});

});
});
});
