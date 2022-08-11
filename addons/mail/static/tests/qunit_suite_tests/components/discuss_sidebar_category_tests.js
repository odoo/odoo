/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_category_tests.js');

QUnit.test('channel - counter: should not have a counter if the category is unfolded and without needaction messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});

    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and without unread messages"
    );
});

QUnit.test('channel - counter: should not have a counter if the category is unfolded and with needaction messagens', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'mailChannel1' }, { name: 'mailChannel2' }]);
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            body: "message 1",
            model: "mail.channel",
            res_id: mailChannelId1,
        },
        {
            body: "message_2",
            model: "mail.channel",
            res_id: mailChannelId2,
        },
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: mailMessageId2,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with needaction messages",
    );
});

QUnit.test('channel - counter: should not have a counter if category is folded and without needaction messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });

    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('channel - counter: should have correct value of needaction threads if category is folded and with needaction messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([{ name: 'mailChannel1' }, { name: 'mailChannel2' }]);
    const [mailMessageId1, mailMessageId2] = pyEnv['mail.message'].create([
        {
            body: "message 1",
            model: "mail.channel",
            res_id: mailChannelId1,
        },
        {
            body: "message_2",
            model: "mail.channel",
            res_id: mailChannelId2,
        },
    ]);
    pyEnv['mail.notification'].create([
        {
            mail_message_id: mailMessageId1,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
        {
            mail_message_id: mailMessageId2,
            notification_type: 'inbox',
            res_partner_id: pyEnv.currentPartnerId,
        },
    ]);
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of needaction threads if category is folded and with needaction messages"
    );
});

QUnit.test('channel - command: should have view command when category is unfolded', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandView`).length,
        1,
        "should have view command when channel category is open"
    );
});

QUnit.test('channel - command: should have view command when category is folded', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { click, openDiscuss } = await start();
    await openDiscuss();

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandView`).length,
        1,
        "should have view command when channel category is closed"
    );
});

QUnit.test('channel - command: should have add command when category is unfolded', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when channel category is open"
    );
});

QUnit.test('channel - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when channel category is closed"
    );
});

QUnit.test('channel - states: close manually by clicking the title', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
});

QUnit.test('channel - states: open manually by clicking the title', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: close should update the value on the server', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const currentUserId = pyEnv.currentUserId;
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    const initalSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_channel_open,
        true,
        "the vaule in server side should be true"
    );

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    const newSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_channel_open,
        false,
        "the vaule in server side should be false"
    );
});

QUnit.test('channel - states: open should update the value on the server', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const currentUserId = pyEnv.currentUserId;
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    const initalSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_channel_open,
        false,
        "the vaule in server side should be false"
    );

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    const newSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_channel_open,
        true,
        "the vaule in server side should be false"
    );
});

QUnit.test('channel - states: close from the bus', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resUsersSettingsId1 = pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: true,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'res.users.settings/insert', {
            id: resUsersSettingsId1,
            'is_discuss_sidebar_category_channel_open': false,
        });
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
});

QUnit.test('channel - states: open from the bus', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const resUsersSettingsId1 = pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_channel_open: false,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'res.users.settings/insert', {
            id: resUsersSettingsId1,
            'is_discuss_sidebar_category_channel_open': true,
        });
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
});

QUnit.test('channel - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    const channel = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        messaging.models['Thread'].findFromIdentifyingData({
            id: mailChannelId1,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        channel.click();
    });
    assert.ok(channel.classList.contains('o-active'));

    await click(`.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_title`);
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active channel item should remain even if the category is folded'
    );

    await click(`.o_DiscussSidebarMailbox[data-mailbox-local-id="${
        messaging.inbox.localId
    }"]`);
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

QUnit.test('chat - counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                message_unread_counter: 0,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
        channel_type: 'chat',
        public: 'private',
    });

    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and without unread messages",
    );
});

QUnit.test('chat - counter: should not have a counter if the category is unfolded and with unread messagens', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                message_unread_counter: 10,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
        channel_type: 'chat',
        public: 'private',
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with unread messages",
    );
});

QUnit.test('chat - counter: should not have a counter if category is folded and without unread messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                message_unread_counter: 0,
                partner_id: pyEnv.currentPartnerId,
            }],
        ],
        channel_type: 'chat',
        public: 'private',
    });
    const { click, openDiscuss } = await start();
    await openDiscuss();
    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('chat - counter: should have correct value of unread threads if category is folded and with unread messages', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create([
        {
            channel_member_ids: [
                [0, 0, {
                    message_unread_counter: 10,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            channel_type: 'chat',
            public: 'private',
        },
        {
            channel_member_ids: [
                [0, 0, {
                    message_unread_counter: 20,
                    partner_id: pyEnv.currentPartnerId,
                }],
            ],
            channel_type: 'chat',
            public: 'private',
        },
    ]);
    const { click, openDiscuss } = await start();
    await openDiscuss();
    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of unread threads if category is folded and with unread messages"
    );
});

QUnit.test('chat - command: should have add command when category is unfolded', async function (assert) {
    assert.expect(1);

    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        1,
        "should have add command when chat category is open"
    );
});

QUnit.test('chat - command: should not have add command when category is folded', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_header .o_DiscussSidebarCategory_commandAdd`).length,
        0,
        "should not have add command when chat category is closed"
    );
});

QUnit.test('chat - states: close manually by clicking the title', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        public: 'private',
    });
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: open manually by clicking the title', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        public: 'private',
    });
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: close should call update server data', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const currentUserId = pyEnv.currentUserId;
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    const initalSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_chat_open,
        true,
        "the value in server side should be true"
    );

    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    const newSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_chat_open,
        false,
        "the value in server side should be false"
    );
});

QUnit.test('chat - states: open should call update server data', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['mail.channel'].create({});
    pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    const initalSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[pyEnv.currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_chat_open,
        false,
        "the value in server side should be false"
    );

    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    const newSettings = await messaging.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[pyEnv.currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_chat_open,
        true,
        "the value in server side should be true"
    );
});

QUnit.test('chat - states: close from the bus', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        public: 'private',
    });
    const resUsersSettingsId1 = pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: true,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'res.users.settings/insert', {
            id: resUsersSettingsId1,
            'is_discuss_sidebar_category_chat_open': false,
        });
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
});

QUnit.test('chat - states: open from the bus', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        public: 'private',
    });
    const resUsersSettingsId1 = pyEnv['res.users.settings'].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_chat_open: false,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    await afterNextRender(() => {
        pyEnv['bus.bus']._sendone(pyEnv.currentPartner, 'res.users.settings/insert', {
            id: resUsersSettingsId1,
            'is_discuss_sidebar_category_chat_open': true,
        });
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );
});

QUnit.test('chat - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_type: 'chat',
        public: 'private',
    });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    const chat = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        messaging.models['Thread'].findFromIdentifyingData({
            id: mailChannelId1,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        chat.click();
    });
    assert.ok(chat.classList.contains('o-active'));

    await click(`.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_title`);
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active chat item should remain even if the category is folded'
    );

    await click(`.o_DiscussSidebarMailbox[data-mailbox-local-id="${
        messaging.inbox.localId
    }"]`);
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            messaging.models['Thread'].findFromIdentifyingData({
                id: mailChannelId1,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

});
});
