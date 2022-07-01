/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    isScrolledToBottom,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { file, dom } from 'web.test_utils';
const { createFile, inputFiles } = file;
const { triggerEvent } = dom;

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager_tests.js');

QUnit.skipWOWL('[technical] messaging not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(1);

    const messagingBeforeCreationDeferred = makeDeferred();
    const { afterNextRender } = await start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });

    // simulate messaging being created
    await afterNextRender(() => messagingBeforeCreationDeferred.resolve());

    assert.containsOnce(
        document.body,
        '.o_ChatWindowManager',
        "should contain chat window manager after messaging has been created"
    );
});

QUnit.skipWOWL('initial mount', async function (assert) {
    assert.expect(1);

    await start();
    assert.containsOnce(
        document.body,
        '.o_ChatWindowManager',
        "should have chat window manager"
    );
});

QUnit.skipWOWL('chat window new message: basic rendering', async function (assert) {
    assert.expect(10);

    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);
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

QUnit.skipWOWL('chat window new message: focused on open [REQUIRE FOCUS]', async function (assert) {
    assert.expect(2);

    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);
    assert.ok(
        document.querySelector(`.o_ChatWindow`).classList.contains('o-focused'),
        "chat window should be focused"
    );
    assert.strictEqual(
        document.activeElement,
        document.querySelector(`.o_ChatWindow_newMessageFormInput`),
        "chat window focused = selection input focused"
    );
});

QUnit.skipWOWL('chat window new message: close', async function (assert) {
    assert.expect(1);

    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);
    await click(`.o_ChatWindow_header .o_ChatWindowHeader_commandClose`);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        0,
        "chat window should be closed"
    );
});

QUnit.skipWOWL('chat window new message: fold', async function (assert) {
    assert.expect(6);

    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);
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

    await click(`.o_ChatWindow_header`);
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

    await click(`.o_ChatWindow_header`);
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

QUnit.skipWOWL('open chat from "new message" chat window should open chat in place of this "new message" chat window', async function (assert) {
    /**
     * InnerWith computation uses following info:
     * ([mocked] global window width: @see `mail/static/tests/helpers/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager.js:visual)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1920px
     *
     * Enough space for 3 visible chat windows:
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 1920
     */
    assert.expect(12);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Partner 131" });
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const [, mailChannelId2] = pyEnv['mail.channel'].create([
        {
            name: 'channel-1',
            channel_last_seen_partner_ids: [
                [0, 0, {
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
        {
            name: 'channel-2',
            channel_last_seen_partner_ids: [
                [0, 0, {
                    is_minimized: false,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
    ]);
    const imSearchDef = makeDeferred();
    patchUiSize({ width: 1920 });
    const { click, insertText, messaging } = await start({
        mockRPC(route, args) {
            if (args.method === 'im_search') {
                imSearchDef.resolve();
            }
        }
    });
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        1,
        "should have 1 chat window initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow.o-new-message',
        "should not have any 'new message' chat window initially"
    );

    // open "new message" chat window
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow.o-new-message',
        "should have 'new message' chat window after clicking 'new message' in messaging menu"
    );
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "should have 2 chat windows after opening 'new message' chat window",
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_newMessageFormInput',
        "'new message' chat window should have new message form input"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]'),
        'o-new-message',
        "'new message' chat window should be the last chat window initially",
    );

    // open channel-2
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_NotificationListItem[data-thread-local-id="${
        messaging.models['Thread'].findFromIdentifyingData({
            id: mailChannelId2,
            model: 'mail.channel',
        }).localId
    }"]`);
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        3,
        "should have 3 chat windows after opening chat window of 'channel-2'",
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]'),
        'o-new-message',
        "'new message' chat window should be in the middle after opening chat window of 'channel-2'",
    );

    // search for a user in "new message" autocomplete
    await insertText('.o_ChatWindow_newMessageFormInput', "131");
    // Wait for search RPC to be resolved. The following await lines are
    // necessary because autocomplete is an external lib therefore it is not
    // possible to use `afterNextRender`.
    await imSearchDef;
    await nextAnimationFrame();
    const link = document.querySelector('.ui-autocomplete .ui-menu-item a');
    assert.ok(
        link,
        "should have autocomplete suggestion after typing on 'new message' input"
    );
    assert.strictEqual(
        link.textContent,
        "Partner 131",
        "autocomplete suggestion should target the partner matching search term"
    );

    await afterNextRender(() => link.click());
    assert.containsNone(
        document.body,
        '.o_ChatWindow.o-new-message',
        "should have removed the 'new message' chat window after selecting a partner"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="1"] .o_ChatWindowHeader_name').textContent,
        "Partner 131",
        "chat window with selected partner should be opened in position where 'new message' chat window was, which is in the middle"
    );
});

QUnit.skipWOWL('new message chat window should close on selecting the user if chat with the user is already open', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Partner 131" });
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                fold_state: 'open',
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
        name: "Partner 131",
        public: 'private',
    });
    const { afterEvent, click } = await start();

    // open "new message" chat window
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);

    // search for a user in "new message" autocomplete
    await afterEvent({
        eventName: 'o-AutocompleteInput-source',
        func: () => {
            document.execCommand('insertText', false, "131");
            document.querySelector(`.o_ChatWindow_newMessageFormInput`)
                .dispatchEvent(new window.KeyboardEvent('keydown'));
            document.querySelector(`.o_ChatWindow_newMessageFormInput`)
                .dispatchEvent(new window.KeyboardEvent('keyup'));
        },
        message: "should wait until autocomplete ui sourced its data",
        predicate: () => true,
    });
    const link = document.querySelector('.ui-autocomplete .ui-menu-item a');

    await afterNextRender(() => link.click());
    assert.containsNone(
        document.body,
        '.o_ChatWindow_newMessageFormInput',
        "'new message' chat window should not be there"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have only one chat window after selecting user whose chat is already open",
    );
});

QUnit.skipWOWL('new message autocomplete should automatically select first result', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Partner 131" });
    pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    const imSearchDef = makeDeferred();
    const { click } = await start({
        mockRPC(route, args) {
            if (args.method === 'im_search') {
                imSearchDef.resolve();
            }
        },
    });

    // open "new message" chat window
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);

    // search for a user in "new message" autocomplete
    document.execCommand('insertText', false, "131");
    document.querySelector(`.o_ChatWindow_newMessageFormInput`)
        .dispatchEvent(new window.KeyboardEvent('keydown'));
    document.querySelector(`.o_ChatWindow_newMessageFormInput`)
        .dispatchEvent(new window.KeyboardEvent('keyup'));
    // Wait for search RPC to be resolved. The following await lines are
    // necessary because autocomplete is an external lib therefore it is not
    // possible to use `afterNextRender`.
    await imSearchDef;
    await nextAnimationFrame();
    assert.hasClass(
        document.querySelector('.ui-autocomplete .ui-menu-item a'),
        'ui-state-active',
        "first autocomplete result should be automatically selected",
    );
});

QUnit.skipWOWL('chat window: basic rendering', async function (assert) {
    assert.expect(14);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { click, messaging } = await start();

    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_NotificationList_preview`);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    const chatWindow = document.querySelector(`.o_ChatWindow`);
    assert.strictEqual(
        chatWindow.dataset.threadLocalId,
        messaging.models['Thread'].findFromIdentifyingData({
            id: mailChannelId1,
            model: 'mail.channel',
        }).localId,
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
        5,
        "should have 5 commands in header part"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_commandPhone`).length,
        1,
        "should have command to start an RTC call in audio mode"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_commandCamera`).length,
        1,
        "should have command to start an RTC call in video mode"
    );
    assert.strictEqual(
        chatWindowHeader.querySelectorAll(`:scope .o_ChatWindowHeader_commandShowMemberList`).length,
        1,
        "should have command to show the member list"
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
        chatWindow.querySelector(`:scope .o_ChatWindow_thread`).classList.contains('o_ThreadView'),
        "thread part should use component ThreadView"
    );
});

QUnit.skipWOWL('chat window: fold', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    const { click } = await start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:${args.method}/${args.kwargs.state}`);
            }
        },
    });
    // Open Thread
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should have a thread"
    );
    assert.verifySteps(
        ['rpc:channel_fold/open'],
        "should sync fold state 'open' with server after opening chat window"
    );

    // Fold chat window
    await click(`.o_ChatWindow_header`);
    assert.verifySteps(
        ['rpc:channel_fold/folded'],
        "should sync fold state 'folded' with server after folding chat window"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should not have any thread"
    );

    // Unfold chat window
    await click(`.o_ChatWindow_header`);
    assert.verifySteps(
        ['rpc:channel_fold/open'],
        "should sync fold state 'open' with server after unfolding chat window"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_thread',
        "chat window should have a thread"
    );
});

QUnit.skipWOWL('chat window: open / close', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    const { click } = await start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
        },
    });
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have a chat window initially"
    );
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have a chat window after clicking on thread preview"
    );
    assert.verifySteps(
        ['rpc:channel_fold/open'],
        "should sync fold state 'open' with server after opening chat window"
    );

    // Close chat window
    await click(`.o_ChatWindowHeader_commandClose`);
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have a chat window after closing it"
    );
    assert.verifySteps(
        ['rpc:channel_fold/closed'],
        "should sync fold state 'closed' with server after closing chat window"
    );

    // Reopen chat window
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have a chat window again after clicking on thread preview again"
    );
    assert.verifySteps(
        ['rpc:channel_fold/open'],
        "should sync fold state 'open' with server after opening chat window again"
    );
});

QUnit.skipWOWL('Mobile: opening a chat window should not update channel state on the server', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                fold_state: 'closed',
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    patchUiSize({ size: SIZES.SM });
    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_NotificationList_preview`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have a chat window after clicking on thread preview"
    );
    const [member] = pyEnv['mail.channel.partner'].searchRead([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    assert.strictEqual(
        member.fold_state,
        'closed',
        'opening a chat window in mobile should not update channel state on the server',
    );
});

QUnit.skipWOWL('Mobile: closing a chat window should not update channel state on the server', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                fold_state: 'open',
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    patchUiSize({ size: SIZES.SM });
    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_NotificationList_preview`);
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have a chat window after clicking on thread preview"
    );
    // Close chat window
    await click(`.o_ChatWindowHeader_commandClose`);
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have a chat window after closing it"
    );
    const [member] = pyEnv['mail.channel.partner'].searchRead([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    assert.strictEqual(
        member.fold_state,
        'open',
        'closing the chat window should not update channel state on the server',
    );
});

QUnit.skipWOWL("Mobile: chat window shouldn't open automatically after receiving a new message", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const resUsersId1 = pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    pyEnv['mail.channel'].records = [
        {
            channel_last_seen_partner_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: resPartnerId1 }],
            ],
            channel_type: "chat",
            id: resPartnerId1,
            uuid: 'channel-10-uuid',
        },
    ];
    patchUiSize({ size: SIZES.SM });
    const { messaging } = await start();

    // simulate receiving a message
    messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "hu",
            uuid: 'channel-10-uuid',
        },
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "On mobile, the chat window shouldn't open automatically after receiving a new message"
    );
});

QUnit.skipWOWL('chat window: close on ESCAPE', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    pyEnv['res.partner'].create({ name: "TestPartner" });
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    const { click, insertText } = await start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
        },
    });
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should be opened initially"
    );

    await click(`.o_Composer_buttonEmojis`);
    assert.containsOnce(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be opened after click on emojis button"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_Composer_buttonEmojis`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_EmojiPickerView',
        "emoji list should be closed after pressing escape on emojis button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should still be opened after pressing escape on emojis button"
    );

    await insertText('.o_ComposerTextInput_textarea', "@");
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionList_list'),
        'show',
        "should display mention suggestions on typing '@'"
    );

    await afterNextRender(() => {
        const ev = new window.KeyboardEvent('keydown', { bubbles: true, key: "Escape" });
        document.querySelector(`.o_ComposerTextInput_textarea`).dispatchEvent(ev);
    });
    assert.containsNone(
        document.body,
        '.o_ComposerSuggestionList_list',
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

QUnit.skipWOWL('focus next visible chat window when closing current chat window with ESCAPE [REQUIRE FOCUS]', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: @see `mail/static/tests/helpers/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager.js:visual)
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

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create([
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
    await start();
    assert.containsN(
        document.body,
        '.o_ChatWindow .o_ComposerTextInput_textarea',
        2,
        "2 chat windows should be present initially"
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

QUnit.skipWOWL('chat window: composer state conservation on toggle discuss', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, insertText, messaging, openDiscuss, openView } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`);
    // Set content of the composer of the chat window
    await insertText('.o_ComposerTextInput_textarea', 'XDU for the win !');
    assert.containsNone(
        document.body,
        '.o_Composer .o_AttachmentCard',
        "composer should have no attachment initially"
    );
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
            messaging.chatWindowManager.chatWindows[0].threadView.composerView.fileUploader.fileInput,
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
        '.o_Composer .o_AttachmentCard',
        2,
        "composer should have 2 total attachments after adding 2 attachments"
    );

    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.containsNone(document.body, '.o_ChatWindow', "should not have any chat window after opening discuss");

    await openView({
        res_id: mailChannelId,
        res_model: 'mail.channel',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelector(`.o_ComposerTextInput_textarea`).value,
        "XDU for the win !",
        "chat window composer should still have the same input after closing discuss"
    );
    assert.containsN(
        document.body,
        '.o_Composer .o_AttachmentCard',
        2,
        "Chat window composer should have 2 attachments after closing discuss"
    );
});

QUnit.skipWOWL('chat window: scroll conservation on toggle discuss', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    for (let i = 0; i < 10; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
        });
    }
    const { afterEvent, click, openDiscuss, openView } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    // Set a scroll position to chat window
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142;
        },
        message: "should wait until channel scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    });

    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.containsNone(document.body, '.o_ChatWindow', "should not have any chat window after opening discuss");

    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => openView({
            res_id: mailChannelId1,
            res_model: 'mail.channel',
            views: [[false, 'list']],
        }),
        message: "should wait until channel restored its scroll to 142 after closing discuss",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after closing discuss"
    );
});

QUnit.skipWOWL('open 2 different chat windows: enough screen width [REQUIRE FOCUS]', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: @see `mail/static/tests/helpers/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager.js:visual)
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

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'mailChannel1' }, { name: 'mailChannel2' }]);
    patchUiSize({ width: 1920 }); // enough to fit at least 2 chat windows
    const { click, messaging } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: 'mail.channel',
                }).localId
            }"]
        `).length,
        1,
        "chat window of chat should be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should have focus"
    );

    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId2,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        2,
        "should have open a new chat window"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId2,
                    model: 'mail.channel',
                }).localId
            }"]
        `).length,
        1,
        "chat window of channel should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: 'mail.channel',
                }).localId
            }"]
        `).length,
        1,
        "chat window of chat should still be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId2,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel should have focus"
    );
    assert.notOk(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should no longer have focus"
    );
});

QUnit.skipWOWL('open 3 different chat windows: not enough screen width', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see `mail/static/src/models/chat_window_manager.js:visual`)
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

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2, mailChannelId3] = pyEnv['mail.channel'].create([
        { name: 'mailChannel1' },
        { name: 'mailChannel2' },
        { name: 'mailChannel3' },
    ]);
    patchUiSize({ width: 900 }); // enough to fit 2 chat windows but not 3
    const { click, messaging } = await start();

    // open, from systray menu, chat windows of channels with Id 1, 2, then 3
    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]
    `);
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

    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId2,
                model: 'mail.channel',
            }).localId
        }"]
    `);
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

    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId3,
                model: 'mail.channel',
            }).localId
        }"]
    `);
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
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId1,
                    model: 'mail.channel',
                }).localId
            }"]
        `).length,
        1,
        "chat window of channel 1 should be open"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId3,
                    model: 'mail.channel',
                }).localId
            }"]
        `).length,
        1,
        "chat window of channel 3 should be open"
    );
    assert.ok(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                messaging.models['Thread'].findFromIdentifyingData({
                    id: mailChannelId3,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel 3 should have focus"
    );
});

QUnit.skipWOWL('chat window: switch on TAB', async function (assert) {
    assert.expect(10);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'channel1' }, { name: 'channel2' }]);
    const { click, messaging } = await start();

    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`
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

    await click(`.o_MessagingMenu_toggler`);
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId2,
                model: 'mail.channel',
            }).localId
        }"]`
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

QUnit.skipWOWL('chat window: TAB cycle with 3 open chat windows [REQUIRE FOCUS]', async function (assert) {
    /**
     * InnerWith computation uses following info:
     * ([mocked] global window width: @see `mail/static/tests/helpers/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager.js:visual)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1920px
     *
     * Enough space for 3 visible chat windows:
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 1920
     */
    assert.expect(6);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create([
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
        },
    ]);
    patchUiSize({ width: 1920 });
    await start();
    assert.containsN(
        document.body,
        '.o_ChatWindow .o_ComposerTextInput_textarea',
        3,
        "initialy, 3 chat windows should be present"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow.o-folded',
        "all 3 chat windows should be open"
    );

    await afterNextRender(() => {
        document.querySelector(".o_ChatWindow[data-visible-index='2'] .o_ComposerTextInput_textarea").focus();
    });
    assert.strictEqual(
        document.querySelector(".o_ChatWindow[data-visible-index='2'] .o_ComposerTextInput_textarea"),
        document.activeElement,
        "The chatWindow with visible-index 2 should have the focus"
    );

    await afterNextRender(() =>
        triggerEvent(
            document.querySelector(".o_ChatWindow[data-visible-index='2'] .o_ComposerTextInput_textarea"),
            'keydown',
            { key: 'Tab' },
        )
    );
    assert.strictEqual(
        document.querySelector(".o_ChatWindow[data-visible-index='1'] .o_ComposerTextInput_textarea"),
        document.activeElement,
        "after pressing tab on the chatWindow with visible-index 2, the chatWindow with visible-index 1 should have focus"
    );

    await afterNextRender(() =>
        triggerEvent(
            document.querySelector(".o_ChatWindow[data-visible-index='1'] .o_ComposerTextInput_textarea"),
            'keydown',
            { key: 'Tab' },
        )
    );
    assert.strictEqual(
        document.querySelector(".o_ChatWindow[data-visible-index='0'] .o_ComposerTextInput_textarea"),
        document.activeElement,
        "after pressing tab on the chat window with visible-index 1, the chatWindow with visible-index 0 should have focus"
    );

    await afterNextRender(() =>
        triggerEvent(
            document.querySelector(".o_ChatWindow[data-visible-index='0'] .o_ComposerTextInput_textarea"),
            'keydown',
            { key: 'Tab' },
        )
    );
    assert.strictEqual(
        document.querySelector(".o_ChatWindow[data-visible-index='2'] .o_ComposerTextInput_textarea"),
        document.activeElement,
        "the chatWindow with visible-index 2 should have the focus after pressing tab on the chatWindow with visible-index 0"
    );
});

QUnit.skipWOWL('chat window with a thread: keep scroll position in message list on folded', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    for (let i = 0; i < 10; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
        });
    }
    const { afterEvent, click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    // Set a scroll position to chat window
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142;
        },
        message: "should wait until channel scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "verify chat window initial scrollTop"
    );

    // fold chat window
    await click('.o_ChatWindow_header');
    assert.containsNone(
        document.body,
        ".o_ThreadView",
        "chat window should be folded so no ThreadView should be present"
    );

    // unfold chat window
    await afterNextRender(() => afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_ChatWindow_header').click(),
        message: "should wait until channel restored its scroll position to 142",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    }));
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same when chat window is unfolded"
    );
});

QUnit.skipWOWL('chat window should scroll to the newly posted message just after posting it', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                fold_state: 'open',
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    for (let i = 0; i < 10; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
        });
    }
    const { insertText } = await start();

    // Set content of the composer of the chat window
    await insertText('.o_ComposerTextInput_textarea', 'WOLOLO');
    // Send a new message in the chatwindow to trigger the scroll
    await afterNextRender(() =>
        triggerEvent(
            document.querySelector('.o_ChatWindow .o_ComposerTextInput_textarea'),
            'keydown',
            { key: 'Enter' },
        )
    );
    const messageList = document.querySelector('.o_MessageList');
    assert.ok(
        isScrolledToBottom(messageList),
        "chat window should scroll to the newly posted message just after posting it"
    );
});

QUnit.skipWOWL('chat window: post message on non-mailing channel with "CTRL-Enter" keyboard shortcut for small screen size', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                is_minimized: true,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
    });
    patchUiSize({ size: SIZES.SM });
    const { click, insertText } = await start();

    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`);
    // insert some HTML in editable
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { ctrlKey: true, key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have single message in channel after posting message from pressing 'CTRL-Enter' in text input of composer for small screen"
    );
});

QUnit.skipWOWL('chat window with a thread: keep scroll position in message list on toggle discuss when folded', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    for (let i = 0; i < 10; i++) {
        pyEnv['mail.message'].create({
            body: "not empty",
            model: "mail.channel",
            res_id: mailChannelId1,
        });
    }
    const { afterEvent, click, openDiscuss, openView } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                isScrolledToBottom(messageList)
            );
        },
    });
    // Set a scroll position to chat window
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142,
        message: "should wait until channel scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    });
    // fold chat window
    await click('.o_ChatWindow_header');
    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.containsNone(document.body, '.o_ChatWindow', "should not have any chat window after opening discuss");

    await openView({
        res_id: mailChannelId1,
        res_model: 'mail.channel',
        views: [[false, 'list']],
    });
    // unfold chat window
    await afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_ChatWindow_header').click(),
        message: "should wait until channel restored its scroll position to the last saved value (142)",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === mailChannelId1 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after closing discuss"
    );
});

QUnit.skipWOWL('chat window does not fetch messages if hidden', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see `mail/static/src/models/chat_window_manager.js:visual`)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1080px
     *
     * Enough space for 2 visible chat windows, and one hidden chat window:
     * 3 visible chat windows:
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 > 900
     * 2 visible chat windows + hidden menu:
     *  10 + 325 + 5 + 325 + 10 + 200 + 5 = 875 < 900
     */
    assert.expect(11);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2, mailChannelId3] = pyEnv['mail.channel'].create([
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }]
            ],
            name: "Channel #10",
        },
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            name: "Channel #11",
        },
        {
            channel_last_seen_partner_ids: [
                [0, 0, {
                    fold_state: 'open',
                    is_minimized: true,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            name: "Channel #12",
        },
    ]);
    patchUiSize({ width: 900 });
    const { click, messaging } = await start({
        mockRPC(route, args) {
            if (route === '/mail/channel/messages') {
                const { channel_id } = args;
                assert.step(`rpc:/mail/channel/messages:${channel_id}`);
            }
        },
    });

    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "2 chat windows should be visible"
    );
    assert.containsNone(
        document.body,
        `.o_ChatWindow[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId3,
                model: 'mail.channel',
            }).localId
        }"]`,
        "chat window for Channel #12 should be hidden"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHiddenMenu',
        "chat window hidden menu should be displayed"
    );
    assert.verifySteps(
        [`rpc:/mail/channel/messages:${mailChannelId1}`, `rpc:/mail/channel/messages:${mailChannelId2}`],
        "messages should be fetched for the two visible chat windows"
    );

    await click('.o_ChatWindowHiddenMenu_dropdownToggle');
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHiddenMenuItem',
        "1 hidden chat window should be listed in hidden menu"
    );

    await click('.o_ChatWindowHiddenMenuItem_chatWindowHeader');
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "2 chat windows should still be visible"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatWindow[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId3,
                model: 'mail.channel',
            }).localId
        }"]`,
        "chat window for Channel #12 should now be visible"
    );
    assert.verifySteps(
        [`rpc:/mail/channel/messages:${mailChannelId3}`],
        "messages should now be fetched for Channel #12"
    );
});

QUnit.skipWOWL('new message separator is shown in a chat window of a chat on receiving new message if there is a history of conversation', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const resUsersId1 = pyEnv['res.users'].create({ name: "Foreigner user", partner_id: resPartnerId1 });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                is_minimized: true,
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
        uuid: 'channel-10-uuid',
    });
    pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { messaging } = await start();

    // simulate receiving a message
    await afterNextRender(async () => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "hu",
            uuid: 'channel-10-uuid',
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "a chat window should be visible after receiving a new message from a chat"
    );
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "chat window should have 2 messages"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should display 'new messages' separator in the conversation, from reception of new messages"
    );
});

QUnit.skipWOWL('new message separator is not shown in a chat window of a chat on receiving new message if there is no history of conversation', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const resUsersId1 = pyEnv['res.users'].create({ name: "Foreigner user", partner_id: resPartnerId1 });
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
        uuid: 'channel-10-uuid',
    });
    const { messaging } = await start();

    // simulate receiving a message
    await afterNextRender(async () => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "hu",
            uuid: 'channel-10-uuid',
        },
    }));
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should not display 'new messages' separator in the conversation of a chat on receiving new message if there is no history of conversation"
    );
});

QUnit.skipWOWL('focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const resUsersId1 = pyEnv['res.users'].create({ name: "Foreigner user", partner_id: resPartnerId1 });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                is_minimized: true,
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "chat",
        uuid: 'channel-10-uuid',
    });
    pyEnv['mail.message'].create({
        body: "not empty",
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const { afterEvent, messaging } = await start();

    // simulate receiving a message
    await afterNextRender(() => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "hu",
            uuid: 'channel-10-uuid',
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should display 'new messages' separator in the conversation, from reception of new messages"
    );

    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => document.querySelector('.o_ComposerTextInput_textarea').focus(),
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.id === mailChannelId1 &&
                thread.model === 'mail.channel'
            );
        },
    }));
    assert.containsNone(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "new message separator should no longer be shown, after focus on composer text input of chat window"
    );
});

QUnit.skipWOWL('chat window should open when receiving a new DM', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const resUsersId1 = pyEnv['res.users'].create({ partner_id: resPartnerId1 });
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'chat',
        uuid: 'channel11uuid',
    });
    const { messaging } = await start();

    // simulate receiving the first message on channel 11
    await afterNextRender(() => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "new message",
            uuid: 'channel11uuid',
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "a chat window should be open now that current user received a new message"
    );
});

QUnit.skipWOWL('chat window should remain folded when new message is received', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const resUsersId1 = pyEnv['res.users'].create({ name: "Foreigner user", partner_id: resPartnerId1 });
    pyEnv['mail.channel'].create({
        channel_last_seen_partner_ids: [
            [0, 0, {
                fold_state: 'folded',
                is_minimized: true,
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, {
                partner_id: resPartnerId1,
            }],
        ],
        channel_type: "chat",
        uuid: 'channel-10-uuid',
    });

    const { messaging } = await start();
    // simulate receiving a new message
    await afterNextRender(async () => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: resUsersId1,
            },
            message_content: "New Message 2",
            uuid: 'channel-10-uuid',
        },
    }));
    assert.hasClass(
        document.querySelector(`.o_ChatWindow`),
        'o-folded',
        "chat window should remain folded"
    );
});

QUnit.skipWOWL('should not have chat window hidden menu in mobile (transition from 2 chat windows in desktop to mobile)', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see `mail/static/src/models/chat_window_manager.js:visual`)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1080px
     *
     * Not enough space for 2 visible chat windows:
     *  10 + 325 + 5 + 325 + 10 = 675 > 600
     * Enough space for 1 visible chat window + hidden menu:
     *  10 + 325 + 5 + 200 + 10 = 550 < 600
     */
    assert.expect(1);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'mailChannel1' }, { name: 'mailChannel1' }]);
    patchUiSize({ width: 600 }); // enough to fit 1 chat window + hidden menu
    const { click, messaging } = await start();
    // open, from systray menu, chat windows of channels with id 1, 2
    await click('.o_MessagingMenu_toggler');
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    await click('.o_ChatWindowHeader_commandBack');
    await click(`
        .o_MessagingMenu_dropdownMenu
        .o_NotificationList_preview[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId2,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    // simulate resize to go into mobile
    await afterNextRender(
        () => messaging.device.update({
            globalWindowInnerWidth: 300,
            isMobileDevice: true,
            isSmall: true,
            sizeClass: 0, // XS
        }),
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindowManager_hiddenMenu',
        "should not have any chat window hidden menu in mobile (transition from desktop having 2 visible chat windows)",
    );
});

});
});
