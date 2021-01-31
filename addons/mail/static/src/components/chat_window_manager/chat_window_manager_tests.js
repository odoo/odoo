odoo.define('mail/static/src/components/chat_window_manager/chat_window_manager_tests.js', function (require) {
'use strict';

const { makeDeferred } = require('mail/static/src/utils/deferred/deferred.js');
const {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

const {
    file: { createFile, inputFiles },
    dom: { triggerEvent },
} = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chat_window_manager', {}, function () {
QUnit.module('chat_window_manager_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign(
                { hasChatWindow: true, hasMessagingMenu: true },
                params,
                { data: this.data }
            ));
            this.debug = params && params.debug;
            this.afterEvent = afterEvent;
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
        afterEach(this);
    },
});

QUnit.test('[technical] messaging not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(2);

    const messagingBeforeCreationDeferred = makeDeferred();
    await this.start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });
    assert.containsOnce(
        document.body,
        '.o_ChatWindowManager',
        "should have chat window manager even when messaging is not yet created"
    );

    // simulate messaging being created
    messagingBeforeCreationDeferred.resolve();
    await nextAnimationFrame();

    assert.containsOnce(
        document.body,
        '.o_ChatWindowManager',
        "should still contain chat window manager after messaging has been created"
    );
});

QUnit.test('initial mount', async function (assert) {
    assert.expect(1);

    await this.start();
    assert.containsOnce(
        document.body,
        '.o_ChatWindowManager',
        "should have chat window manager"
    );
});

QUnit.test('chat window new message: basic rendering', async function (assert) {
    assert.expect(10);

    await this.start();
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

    await this.start();
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

    await this.start();
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

    await this.start();
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

QUnit.test('open chat from "new message" chat window should open chat in place of this "new message" chat window', async function (assert) {
    /**
     * InnerWith computation uses following info:
     * ([mocked] global window width: @see `mail/static/src/utils/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager/chat_window_manager.js:visual)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - hidden menu width: 200px
     * - global width: 1920px
     *
     * Enough space for 3 visible chat windows:
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 < 1920
     */
    assert.expect(11);

    this.data['res.partner'].records.push({ id: 131, name: "Partner 131" });
    this.data['res.users'].records.push({ partner_id: 131 });
    this.data['mail.channel'].records.push(
        { is_minimized: true },
        { is_minimized: true },
    );
    const imSearchDef = makeDeferred();
    await this.start({
        env: {
            browser: {
                innerWidth: 1920,
            },
        },
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'im_search') {
                imSearchDef.resolve();
            }
            return res;
        }
    });
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "should have 2 chat windows initially"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow.o-new-message',
        "should not have any 'new message' chat window initially"
    );

    // open "new message" chat window
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_newMessageButton`).click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow.o-new-message',
        "should have 'new message' chat window after clicking 'new message' in messaging menu"
    );
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        3,
        "should have 3 chat window after opening 'new message' chat window",
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow_newMessageFormInput',
        "'new message' chat window should have new message form input"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="2"]'),
        'o-new-message',
        "'new message' chat window should be the last chat window initially",
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindow[data-visible-index="2"] .o_ChatWindowHeader_commandShiftRight').click()
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]'),
        'o-new-message',
        "'new message' chat window should have moved to the middle after clicking shift previous",
    );

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

QUnit.test('new message autocomplete should automatically select first result', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({ id: 131, name: "Partner 131" });
    this.data['res.users'].records.push({ partner_id: 131 });
    const imSearchDef = makeDeferred();
    await this.start({
        async mockRPC(route, args) {
            const res = await this._super(...arguments);
            if (args.method === 'im_search') {
                imSearchDef.resolve();
            }
            return res;
        },
    });

    // open "new message" chat window
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_newMessageButton`).click()
    );

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

QUnit.test('chat window: basic rendering', async function (assert) {
    assert.expect(11);

    // channel that is expected to be found in the messaging menu
    // with random unique id and name that will be asserted during the test
    this.data['mail.channel'].records.push({ id: 20, name: "General" });
    await this.start();

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
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 20,
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
        chatWindow.querySelector(`:scope .o_ChatWindow_thread`).classList.contains('o_ThreadView'),
        "thread part should use component ThreadView"
    );
});

QUnit.test('chat window: fold', async function (assert) {
    assert.expect(9);

    // channel that is expected to be found in the messaging menu
    // with random UUID, will be asserted during the test
    this.data['mail.channel'].records.push({ uuid: 'channel-uuid' });
    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:${args.method}/${args.kwargs.state}`);
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
        "chat window should have a thread"
    );
    assert.verifySteps(
        ['rpc:channel_fold/open'],
        "should sync fold state 'open' with server after opening chat window"
    );

    // Fold chat window
    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
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
    await afterNextRender(() => document.querySelector(`.o_ChatWindow_header`).click());
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

QUnit.test('chat window: open / close', async function (assert) {
    assert.expect(10);

    // channel that is expected to be found in the messaging menu
    // with random UUID, will be asserted during the test
    this.data['mail.channel'].records.push({ uuid: 'channel-uuid' });
    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
            return this._super(...arguments);
        },
    });
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should not have a chat window initially"
    );
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
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
    await afterNextRender(() => document.querySelector(`.o_ChatWindowHeader_commandClose`).click());
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
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_dropdownMenu .o_NotificationList_preview`).click()
    );
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

QUnit.test('chat window: close on ESCAPE', async function (assert) {
    assert.expect(10);

    // expected partner to be found by mention during the test
    this.data['res.partner'].records.push({ name: "TestPartner" });
    // a chat window with thread is expected to be initially open for this test
    this.data['mail.channel'].records.push({ is_minimized: true });
    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                assert.step(`rpc:channel_fold/${args.kwargs.state}`);
            }
            return this._super(...arguments);
        },
    });
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "chat window should be opened initially"
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
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "@");
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keydown'));
        document.querySelector(`.o_ComposerTextInput_textarea`)
            .dispatchEvent(new window.KeyboardEvent('keyup'));
    });
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

    // 2 chat windows with thread are expected to be initially open for this test
    this.data['mail.channel'].records.push(
        { is_minimized: true, state: 'open' },
        { is_minimized: true, state: 'open' }
    );
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

QUnit.test('[technical] chat window: composer state conservation on toggle home menu', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(7);

    // channel that is expected to be found in the messaging menu
    // with random unique id that is needed to link messages
    this.data['mail.channel'].records.push({ id: 20 });
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
    assert.containsNone(
        document.body,
        '.o_Composer .o_Attachment',
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
        "composer should have 2 total attachments after adding 2 attachments"
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
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i < 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel 20 scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    // Set a scroll position to chat window
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142;
        },
        message: "should wait until channel 20 scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === 142
            );
        },
    });
    await afterNextRender(() => this.hideHomeMenu());
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is hidden"
    );

    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => this.showHomeMenu(),
        message: "should wait until channel 20 restored its scroll to 142 after showing the home menu",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
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

    // 2 channels are expected to be found in the messaging menu, each with a
    // random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 10 }, { id: 20 });
    await this.start({
        env: {
            browser: {
                innerWidth: 1920, // enough to fit at least 2 chat windows
            },
        },
    });
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should have focus"
    );

    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 20,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 20,
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 20,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel should have focus"
    );
    assert.notOk(
        document.querySelector(`
            .o_ChatWindow[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 10,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of chat should no longer have focus"
    );
});

QUnit.test('open 2 chat windows: check shift operations are available', async function (assert) {
    assert.expect(9);

    // 2 channels are expected to be found in the messaging menu
    // only their existence matters, data are irrelevant
    this.data['mail.channel'].records.push({}, {});
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

QUnit.test('open 2 folded chat windows: check shift operations are available', async function (assert) {
    /**
     * computation uses following info:
     * ([mocked] global window width: 900px)
     * (others: @see `mail/static/src/models/chat_window_manager/chat_window_manager.js:visual`)
     *
     * - chat window width: 325px
     * - start/end/between gap width: 10px/10px/5px
     * - global width: 900px
     *
     * 2 visible chat windows + hidden menu:
     *  10 + 325 + 5 + 325 + 10 = 675 < 900
     */
    assert.expect(13);

    this.data['res.partner'].records.push({ id: 7, name: "Demo" });
    const channel = {
        channel_type: "channel",
        is_minimized: true,
        is_pinned: true,
        state: 'folded',
    };
    const chat = {
        channel_type: "chat",
        is_minimized: true,
        is_pinned: true,
        members: [this.data.currentPartnerId, 7],
        state: 'folded',
    };
    this.data['mail.channel'].records.push(channel, chat);
    await this.start({
        env: {
            browser: {
                innerWidth: 900,
            },
        },
    });

    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "should have opened 2 chat windows initially"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="0"]'),
        'o-folded',
        "first chat window should be folded"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]'),
        'o-folded',
        "second chat window should be folded"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow .o_ChatWindowHeader_commandShiftLeft',
        "there should be only one chat window allowed to shift left even if folded"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow .o_ChatWindowHeader_commandShiftRight',
        "there should be only one chat window allowed to shift right even if folded"
    );

    const initialFirstChatWindowThreadLocalId =
        document.querySelector('.o_ChatWindow[data-visible-index="0"]').dataset.threadLocalId;
    const initialSecondChatWindowThreadLocalId =
        document.querySelector('.o_ChatWindow[data-visible-index="1"]').dataset.threadLocalId;
    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandShiftLeft').click()
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="0"]').dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "First chat window should be second after it has been shift left"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]').dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "Second chat window should be first after the first has been shifted left"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandShiftLeft').click()
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="0"]').dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "First chat window should be back at first place"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]').dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "Second chat window should be back at second place"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandShiftRight').click()
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="0"]').dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "First chat window should be second after it has been shift right"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]').dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "Second chat window should be first after the first has been shifted right"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHeader_commandShiftRight').click()
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="0"]').dataset.threadLocalId,
        initialFirstChatWindowThreadLocalId,
        "First chat window should be back at first place"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindow[data-visible-index="1"]').dataset.threadLocalId,
        initialSecondChatWindowThreadLocalId,
        "Second chat window should be back at second place"
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

    // 3 channels are expected to be found in the messaging menu, each with a
    // random unique id that will be referenced in the test
    this.data['mail.channel'].records.push({ id: 1 }, { id: 2 }, { id: 3 });
    await this.start({
        env: {
            browser: {
                innerWidth: 900, // enough to fit 2 chat windows but not 3
            },
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 1,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 2,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 3,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 1,
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 3,
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 3,
                    model: 'mail.channel',
                }).localId
            }"]
        `).classList.contains('o-focused'),
        "chat window of channel 3 should have focus"
    );
});

QUnit.test('chat window: switch on TAB', async function (assert) {
    assert.expect(10);

    // 2 channels are expected to be found in the messaging menu
    // with random unique id and name that will be asserted during the test
    this.data['mail.channel'].records.push(
        { id: 1, name: "channel1" },
        { id: 2, name: "channel2" }
    );
    await this.start();

    await afterNextRender(() =>
        document.querySelector(`.o_MessagingMenu_toggler`).click()
    );
    await afterNextRender(() =>
        document.querySelector(`
            .o_MessagingMenu_dropdownMenu
            .o_NotificationList_preview[data-thread-local-id="${
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 1,
                    model: 'mail.channel',
                }).localId
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
                this.env.models['mail.thread'].findFromIdentifyingData({
                    id: 2,
                    model: 'mail.channel',
                }).localId
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

QUnit.test('chat window: TAB cycle with 3 open chat windows [REQUIRE FOCUS]', async function (assert) {
    /**
     * InnerWith computation uses following info:
     * ([mocked] global window width: @see `mail/static/src/utils/test_utils.js:start()` method)
     * (others: @see mail/static/src/models/chat_window_manager/chat_window_manager.js:visual)
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

    this.data['mail.channel'].records.push(
        {
            is_minimized: true,
            is_pinned: true,
            state: 'open',
        },
        {
            is_minimized: true,
            is_pinned: true,
            state: 'open',
        },
        {
            is_minimized: true,
            is_pinned: true,
            state: 'open',
        }
    );
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

QUnit.test('chat window with a thread: keep scroll position in message list on folded', async function (assert) {
    assert.expect(3);

    // channel that is expected to be found in the messaging menu
    // with a random unique id, needed to link messages
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i < 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel 20 scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    // Set a scroll position to chat window
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => {
            document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142;
        },
        message: "should wait until channel 20 scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
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
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    assert.containsNone(
        document.body,
        ".o_ThreadView",
        "chat window should be folded so no ThreadView should be present"
    );

    // unfold chat window
    await afterNextRender(() => this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_ChatWindow_header').click(),
        message: "should wait until channel 20 restored its scroll position to 142",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
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

QUnit.test('chat window should scroll to the newly posted message just after posting it', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        id: 20,
        is_minimized: true,
        state: 'open',
    });
    for (let i = 0; i < 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();

    // Set content of the composer of the chat window
    await afterNextRender(() => {
        document.querySelector('.o_ComposerTextInput_textarea').focus();
        document.execCommand('insertText', false, 'WOLOLO');
    });
    // Send a new message in the chatwindow to trigger the scroll
    await afterNextRender(() =>
        triggerEvent(
            document.querySelector('.o_ChatWindow .o_ComposerTextInput_textarea'),
            'keydown',
            { key: 'Enter' },
        )
    );
    const messageList = document.querySelector('.o_MessageList');
    assert.strictEqual(
        messageList.scrollHeight - messageList.scrollTop,
        messageList.clientHeight,
        "chat window should scroll to the newly posted message just after posting it"
    );
});

QUnit.test('[technical] chat window: composer state conservation on toggle home menu when folded', async function (assert) {
    // technical as show/hide home menu simulation are involved and home menu implementation
    // have side-effects on DOM that may make chat window components not work
    assert.expect(6);

    // channel that is expected to be found in the messaging menu
    // only its existence matters, data are irrelevant
    this.data['mail.channel'].records.push({});
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
    assert.expect(2);

    // channel that is expected to be found in the messaging menu
    // with random unique id, needed to link messages
    this.data['mail.channel'].records.push({ id: 20 });
    for (let i = 0; i < 10; i++) {
        this.data['mail.message'].records.push({
            body: "not empty",
            channel_ids: [20],
        });
    }
    await this.start();
    await afterNextRender(() => document.querySelector(`.o_MessagingMenu_toggler`).click());
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_NotificationList_preview').click(),
        message: "should wait until channel 20 scrolled to its last message after opening it from the messaging menu",
        predicate: ({ scrollTop, thread }) => {
            const messageList = document.querySelector('.o_ThreadView_messageList');
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === messageList.scrollHeight - messageList.clientHeight
            );
        },
    });
    // Set a scroll position to chat window
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector(`.o_ThreadView_messageList`).scrollTop = 142,
        message: "should wait until channel 20 scrolled to 142 after setting this value manually",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === 142
            );
        },
    });
    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    await this.hideHomeMenu();
    // unfold chat window
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_ChatWindow_header').click(),
        message: "should wait until channel 20 restored its scroll to 142 after unfolding it",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is hidden"
    );

    // fold chat window
    await afterNextRender(() => document.querySelector('.o_ChatWindow_header').click());
    // Show home menu
    await this.showHomeMenu();
    // unfold chat window
    await this.afterEvent({
        eventName: 'o-component-message-list-scrolled',
        func: () => document.querySelector('.o_ChatWindow_header').click(),
        message: "should wait until channel 20 restored its scroll position to the last saved value (142)",
        predicate: ({ scrollTop, thread }) => {
            return (
                thread &&
                thread.model === 'mail.channel' &&
                thread.id === 20 &&
                scrollTop === 142
            );
        },
    });
    assert.strictEqual(
        document.querySelector(`.o_ThreadView_messageList`).scrollTop,
        142,
        "chat window scrollTop should still be the same after home menu is shown"
    );
});

QUnit.test('chat window does not fetch messages if hidden', async function (assert) {
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
     *  10 + 325 + 5 + 325 + 5 + 325 + 10 = 1000 > 900
     * 2 visible chat windows + hidden menu:
     *  10 + 325 + 5 + 325 + 10 + 200 + 5 = 875 < 900
     */
    assert.expect(14);

    // 3 channels are expected to be found in the messaging menu, each with a
    // random unique id that will be referenced in the test
    this.data['mail.channel'].records = [
        {
            id: 10,
            is_minimized: true,
            name: "Channel #10",
            state: 'open',
        },
        {
            id: 11,
            is_minimized: true,
            name: "Channel #11",
            state: 'open',
        },
        {
            id: 12,
            is_minimized: true,
            name: "Channel #12",
            state: 'open',
        },
    ];
    await this.start({
        env: {
            browser: {
                innerWidth: 900,
            },
        },
        mockRPC(route, args) {
            if (args.method === 'message_fetch') {
                // domain should be like [['channel_id', 'in', [X]]] with X the channel id
                const channel_ids = args.kwargs.domain[0][2];
                assert.strictEqual(channel_ids.length, 1, "messages should be fetched channel per channel");
                assert.step(`rpc:message_fetch:${channel_ids[0]}`);
            }
            return this._super(...arguments);
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
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 12,
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
        ['rpc:message_fetch:10', 'rpc:message_fetch:11'],
        "messages should be fetched for the two visible chat windows"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHiddenMenu_dropdownToggle').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindowHiddenMenu_chatWindowHeader',
        "1 hidden chat window should be listed in hidden menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_ChatWindowHiddenMenu_chatWindowHeader').click()
    );
    assert.containsN(
        document.body,
        '.o_ChatWindow',
        2,
        "2 chat windows should still be visible"
    );
    assert.containsOnce(
        document.body,
        `.o_ChatWindow[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 12,
                model: 'mail.channel',
            }).localId
        }"]`,
        "chat window for Channel #12 should now be visible"
    );
    assert.verifySteps(
        ['rpc:message_fetch:12'],
        "messages should now be fetched for Channel #12"
    );
});

QUnit.test('new message separator is shown in a chat window of a chat on receiving new message', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ id: 10, name: "Demo" });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 10,
    });
    this.data['mail.channel'].records = [
        {
            channel_type: "chat",
            id: 10,
            is_minimized: true,
            is_pinned: false,
            members: [this.data.currentPartnerId, 10],
            uuid: 'channel-10-uuid',
        },
    ];
    await this.start({
        mockRPC(route, args) {
            if (args.method === 'channel_fold') {
                const channel_uuid = args.kwargs.uuid;
                assert.strictEqual(channel_uuid, 'channel-10-uuid', "chat window fold state should have been sent to server");
                assert.step(`rpc:channel_fold:${channel_uuid}`);
            }
            return this._super(...arguments);
        },
    });

    // simulate receiving a message
    await afterNextRender(async () => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
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
    assert.containsOnce(
        document.body,
        '.o_Message',
        "chat window should have a single message (the newly received one)"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageList_separatorNewMessages',
        "should display 'new messages' separator in the conversation, from reception of new messages"
    );
    assert.verifySteps(
        ['rpc:channel_fold:channel-10-uuid'],
        "fold state of chat window of chat should have been updated to server"
    );
});

QUnit.test('focusing a chat window of a chat should make new message separator disappear [REQUIRE FOCUS]', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 10, name: "Demo" });
    this.data['res.users'].records.push({
        id: 42,
        name: "Foreigner user",
        partner_id: 10,
    });
    this.data['mail.channel'].records.push(
        {
            channel_type: "chat",
            id: 10,
            is_minimized: true,
            is_pinned: false,
            members: [this.data.currentPartnerId, 10],
            message_unread_counter: 0,
            uuid: 'channel-10-uuid',
        },
    );
    await this.start();

    // simulate receiving a message
    await afterNextRender(() => this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: 42,
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

    await afterNextRender(() => this.afterEvent({
        eventName: 'o-thread-last-seen-by-current-partner-message-id-changed',
        func: () => document.querySelector('.o_ComposerTextInput_textarea').focus(),
        message: "should wait until last seen by current partner message id changed",
        predicate: ({ thread }) => {
            return (
                thread.id === 10 &&
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

});
});
});

});
