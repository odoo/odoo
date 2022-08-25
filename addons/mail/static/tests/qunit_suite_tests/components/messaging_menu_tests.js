/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { browser } from '@web/core/browser/browser';
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

import { makeTestPromise } from 'web.test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu_tests.js');

QUnit.test('[technical] messaging not created then becomes created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(2);

    const messagingBeforeCreationDeferred = makeTestPromise();
    await start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });
    assert.containsOnce(
        document.body,
        '.o_MessagingMenuContainer_spinner',
        "messaging menu container should have spinner when messaging is not yet created"
    );

    // simulate messaging becoming created
    await afterNextRender(() => messagingBeforeCreationDeferred.resolve());
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu',
        "messaging menu container should contain messaging menu after messaging has been created"
    );
});

QUnit.test('messaging not initialized', async function (assert) {
    assert.expect(2);

    const { click } = await start({
        async mockRPC(route) {
            if (route === '/mail/init_messaging') {
                // simulate messaging never initialized
                return new Promise(resolve => {});
            }
        },
        waitUntilMessagingCondition: 'created',
    });
    assert.strictEqual(
        document.querySelectorAll('.o_MessagingMenu_loading').length,
        1,
        "should display loading icon on messaging menu when messaging not yet initialized"
    );

    await click(`.o_MessagingMenu_toggler`);
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_dropdownMenu').textContent,
        "Please wait...",
        "should prompt loading when opening messaging menu"
    );
});

QUnit.test('messaging becomes initialized', async function (assert) {
    assert.expect(2);

    const messagingInitializedProm = makeTestPromise();

    const { click } = await start({
        async mockRPC(route) {
            if (route === '/mail/init_messaging') {
                await messagingInitializedProm;
            }
        },
        waitUntilMessagingCondition: 'created',
    });
    await click(`.o_MessagingMenu_toggler`);

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

    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: 'denied',
        },
    });
    const { click } = await start();
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

    await click(`.o_MessagingMenu_toggler`);
    assert.hasClass(
        document.querySelector('.o_MessagingMenu'),
        "show",
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
            .o_MessagingMenuTab
        `).length,
        3,
        "should have 3 tab buttons to filter items in the header"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="all"]`).length,
        1,
        "1 tab button should be 'All'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="chat"]`).length,
        1,
        "1 tab button should be 'Chat'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="channel"]`).length,
        1,
        "1 tab button should be 'Channels'"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="channel"]
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

    await click(`.o_MessagingMenu_toggler`);
    assert.doesNotHaveClass(
        document.querySelector('.o_MessagingMenu'),
        "show",
        "should mark messaging menu as closed"
    );
});

QUnit.test('counter is taking into account failure notification', async function (assert) {
    assert.expect(2);

    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: 'denied',
        },
    });
    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        model: 'mail.channel',
        res_id: mailChannelId1,
    });
    const [mailChannelMemberId] = pyEnv['mail.channel.member'].search([['channel_id', '=', mailChannelId1], ['partner_id', '=', pyEnv.currentPartnerId]]);
    pyEnv['mail.channel.member'].write([mailChannelMemberId], { seen_message_id: mailMessageId1 });
    // failure that is expected to be used in the test
    pyEnv['mail.notification'].create({
        mail_message_id: mailMessageId1, // id of the related message
        notification_status: 'exception', // necessary value to have a failure
        notification_type: 'email',
    });
    await start();

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

    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="all"]`).length,
        1,
        "1 tab button should be 'All'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="chat"]`).length,
        1,
        "1 tab button should be 'Chat'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenuTab[data-tab-id="channel"]`).length,
        1,
        "1 tab button should be 'Channels'"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not be active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should not be active"
    );

    await click(`.o_MessagingMenuTab[data-tab-id="chat"]`);
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should not become active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should stay inactive"
    );

    await click(`.o_MessagingMenuTab[data-tab-id="channel"]`);
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should stay active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should become inactive"
    );
    assert.ok(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should become active"
    );

    await click(`.o_MessagingMenuTab[data-tab-id="all"]`);
    assert.ok(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="all"]
        `).classList.contains('o-active'),
        "'all' tab button should become active"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="chat"]
        `).classList.contains('o-active'),
        "'chat' tab button should stay inactive"
    );
    assert.notOk(
        document.querySelector(`
            .o_MessagingMenuTab[data-tab-id="channel"]
        `).classList.contains('o-active'),
        "'channel' tab button should become inactive"
    );
});

QUnit.test('new message', async function (assert) {
    assert.expect(3);

    const { click } = await start();
    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_newMessageButton`);

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

    const { click, openDiscuss, openView } = await start();
    await openDiscuss({ waitUntilMessagesLoaded: false });

    await click(`.o_MessagingMenu_toggler`);
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        0,
        "should not have 'new message' when discuss is open"
    );

    await openView({
        res_model: 'res.partner',
        views: [[false, 'form']],
    });

    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        1,
        "should have 'new message' when discuss is closed"
    );

    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_newMessageButton`).length,
        0,
        "should not have 'new message' when discuss is open again"
    );
});

QUnit.test('channel preview: basic rendering', async function (assert) {
    assert.expect(9);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ name: "Demo" });
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    pyEnv['mail.message'].create({
        author_id: resPartnerId1, // not current partner, will be asserted in the test
        body: "<p>test</p>", // random body, will be asserted in the test
        model: 'mail.channel', // necessary to link message to channel
        res_id: mailChannelId1, // id of related channel
    });
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
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

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        { channel_type: "chat" },
        { name: "mailChannel1" },
    ]);
    pyEnv['mail.message'].create([
        {
            model: 'mail.channel', // to link message to channel
            res_id: mailChannelId1, // id of related channel
        },
        {
            model: 'mail.channel', // to link message to channel
            res_id: mailChannelId2, // id of related channel
        },
    ]);
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        2,
        "should have 2 previews"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId2}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of channel"
    );

    await click('.o_MessagingMenuTab[data-tab-id="chat"]');
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        1,
        "should have one preview"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId2}"][data-thread-model="mail.channel"]
        `).length,
        0,
        "should not have preview of channel"
    );

    await click('.o_MessagingMenuTab[data-tab-id="channel"]');
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
            .o_ThreadPreview[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `).length,
        0,
        "should not have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId2}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of channel"
    );

    await click('.o_MessagingMenuTab[data-tab-id="all"]');
    assert.strictEqual(
        document.querySelectorAll(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`).length,
        2,
        "should have 2 previews"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of chat"
    );
    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId2}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have preview of channel"
    );
});

QUnit.test('open chat window from preview', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
    await click(`.o_MessagingMenu_dropdownMenu .o_ThreadPreview`);
    assert.strictEqual(
        document.querySelectorAll(`.o_ChatWindow`).length,
        1,
        "should have open a chat window"
    );
});

QUnit.test('no code injection in message body preview', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        body: "<p><em>&shoulnotberaised</em><script>throw new Error('CodeInjectionError');</script></p>",
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
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
        "You:&shoulnotberaisedthrownewError('CodeInjectionError');",
        "should display correct uninjected last message inline content"
    );
    assert.containsNone(
        document.querySelector('.o_ThreadPreview_inlineText'),
        'script',
        "last message inline content should not have any code injection"
    );
});

QUnit.test('no code injection in message body preview from sanitized message', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        body: "<p>&lt;em&gt;&shoulnotberaised&lt;/em&gt;&lt;script&gt;throw new Error('CodeInjectionError');&lt;/script&gt;</p>",
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
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
        "You:<em>&shoulnotberaised</em><script>thrownewError('CodeInjectionError');</script>",
        "should display correct uninjected last message inline content"
    );
    assert.containsNone(
        document.querySelector('.o_ThreadPreview_inlineText'),
        'script',
        "last message inline content should not have any code injection"
    );
});

QUnit.test('<br/> tags in message body preview are transformed in spaces', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        body: "<p>a<br/>b<br>c<br   />d<br     ></p>",
        model: "mail.channel",
        res_id: mailChannelId1,
    });
    const { click } = await start();

    await click(`.o_MessagingMenu_toggler`);
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
        document.querySelector('.o_ThreadPreview_inlineText').textContent,
        "You: a b c d",
        "should display correct last message inline content with brs replaced by spaces"
    );
});

QUnit.test('rendering with OdooBot has a request (default)', async function (assert) {
    assert.expect(4);

    patchWithCleanup(browser, {
        Notification: {
            ...browser.Notification,
            permission: 'default',
        },
    });
    const { click } = await start();

    assert.ok(
        document.querySelector('.o_MessagingMenu_counter'),
        "should display a notification counter next to the messaging menu for OdooBot request"
    );
    assert.strictEqual(
        document.querySelector('.o_MessagingMenu_counter').textContent,
        "1",
        "should display a counter of '1' next to the messaging menu"
    );

    await click('.o_MessagingMenu_toggler');
    assert.containsOnce(
        document.body,
        '.o_NotificationRequest',
        "should display a notification in the messaging menu"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationRequest_name').textContent.trim(),
        'OdooBot has a request',
        "notification should display that OdooBot has a request"
    );
});

QUnit.test('rendering without OdooBot has a request (denied)', async function (assert) {
    assert.expect(2);

    patchWithCleanup(browser, {
        Notification: {
            permission: 'denied',
        },
    });
    const { click } = await start();

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await click('.o_MessagingMenu_toggler');
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('rendering without OdooBot has a request (accepted)', async function (assert) {
    assert.expect(2);

    patchWithCleanup(browser, {
        Notification: {
            permission: 'granted',
        },
    });
    const { click } = await start();

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await click('.o_MessagingMenu_toggler');
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('respond to notification prompt (denied)', async function (assert) {
    assert.expect(4);

    patchWithCleanup(browser, {
        Notification: {
            permission: 'default',
            async requestPermission() {
                this.permission = 'denied';
                return this.permission;
            },
        },
    });
    const { click } = await start({
        services: {
            notification: makeFakeNotificationService(() => {
                assert.step(
                    "should display a toast notification with the deny confirmation"
                );
            }),
        },
    });

    await click('.o_MessagingMenu_toggler');
    await click('.o_NotificationRequest');
    assert.verifySteps([
        "should display a toast notification with the deny confirmation",
    ]);

    assert.containsNone(
        document.body,
        '.o_MessagingMenu_counter',
        "should not display a notification counter next to the messaging menu"
    );

    await click('.o_MessagingMenu_toggler');
    assert.containsNone(
        document.body,
        '.o_NotificationRequest',
        "should display no notification in the messaging menu"
    );
});

QUnit.test('Group chat should be displayed inside the chat section of the messaging menu', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'group',
    });
    const { click } = await start();

    await click('.o_MessagingMenu_toggler');
    await click(`.o_MessagingMenuTab[data-tab-id="chat"]`);

    assert.strictEqual(
        document.querySelectorAll(`
            .o_MessagingMenu_dropdownMenu
            .o_ThreadPreview[data-thread-id="${mailChannelId1}"][data-thread-model="mail.channel"]
        `).length,
        1,
        "should have one preview of group"
    );
});

});
});
