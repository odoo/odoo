/** @odoo-module **/

import {
    afterNextRender,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { datetime_to_str } from 'web.time';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_tests.js');

QUnit.test('livechat in the sidebar: basic rendering', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(document.body, '.o_Discuss_sidebar',
        "should have a sidebar section"
    );
    const groupLivechat = document.querySelector('.o_DiscussSidebar_categoryLivechat');
    assert.ok(groupLivechat,
        "should have a channel group livechat"
    );
    const titleText = groupLivechat.querySelector('.o_DiscussSidebarCategory_titleText');
    assert.strictEqual(
        titleText.textContent.trim(),
        "Livechat",
        "should have a channel group named 'Livechat'"
    );
    const livechat = groupLivechat.querySelector(`
        .o_DiscussSidebarCategoryItem[data-channel-id="${mailChannelId1}"]
    `);
    assert.ok(
        livechat,
        "should have a livechat in sidebar"
    );
    assert.strictEqual(
        livechat.textContent,
        "Visitor 11",
        "should have 'Visitor 11' as livechat name"
    );
});

QUnit.test('livechat in the sidebar: existing user with country', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resCountryId1 = pyEnv['res.country'].create({
        code: 'be',
        name: "Belgium",
    });
    const resPartnerId1 = pyEnv['res.partner'].create({
        country_id: resCountryId1,
        name: "Jean",
    });
    pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();

    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should have a channel group livechat in the side bar"
    );
    const livechat = document.querySelector('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategoryItem');
    assert.ok(
        livechat,
        "should have a livechat in sidebar"
    );
    assert.strictEqual(
        livechat.textContent,
        "Jean (Belgium)",
        "should have user name and country as livechat name"
    );
});

QUnit.test('do not add livechat in the sidebar on visitor opening his chat', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['res.users'].write([pyEnv.currentUserId], { im_status: 'online' });
    const imLivechatChannelId1 = pyEnv['im_livechat.channel'].create({
        user_ids: [pyEnv.currentUserId],
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor opening his chat
    await messaging.rpc({
        route: '/im_livechat/get_session',
        params: {
            context: {
                mockedUserId: false,
            },
            channel_id: imLivechatChannelId1,
        },
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should still not have any livechat in the sidebar after visitor opened his chat"
    );
});

QUnit.test('do not add livechat in the sidebar on visitor typing', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv['res.users'].write([pyEnv.currentUserId], { im_status: 'online' });
    const imLivechatChannelId1 = pyEnv['im_livechat.channel'].create({
        user_ids: [pyEnv.currentUserId],
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, {
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_channel_id: imLivechatChannelId1,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();

    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor typing
    const channel = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    await messaging.rpc({
        route: '/im_livechat/notify_typing',
        params: {
            context: {
                mockedPartnerId: pyEnv.publicPartnerId,
            },
            is_typing: true,
            uuid: channel.uuid,
        },
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should still not have any livechat in the sidebar after visitor started typing"
    );
});

QUnit.test('add livechat in the sidebar on visitor sending first message', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    pyEnv['res.users'].write([pyEnv.currentUserId], { im_status: 'online' });
    const resCountryId1 = pyEnv['res.country'].create({
        code: 'be',
        name: "Belgium",
    });
    const imLivechatChannelId1 = pyEnv['im_livechat.channel'].create({
        user_ids: [pyEnv.currentUserId],
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor (Belgium)",
        channel_member_ids: [
            [0, 0, {
                is_pinned: false,
                partner_id: pyEnv.currentPartnerId,
            }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        country_id: resCountryId1,
        livechat_channel_id: imLivechatChannelId1,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor sending a message
    const channel = pyEnv['mail.channel'].searchRead([['id', '=', mailChannelId1]])[0];
    await afterNextRender(async () => messaging.rpc({
        route: '/mail/chat_post',
        params: {
            context: {
                mockedUserId: false,
            },
            uuid: channel.uuid,
            message_content: "new message",
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_categoryLivechat',
        "should have a channel group livechat in the side bar after receiving first message"
    );
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategoryItem',
        "should have a livechat in the sidebar after receiving first message"
    );
    assert.strictEqual(
        document.querySelector('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategoryItem .o_DiscussSidebarCategoryItem_name').textContent,
        "Visitor (Belgium)",
        "should have visitor name and country as livechat name"
    );
});

QUnit.test('livechats are sorted by last activity time in the sidebar: most recent at the top', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [mailChannelId1, mailChannelId2] = pyEnv['mail.channel'].create([
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, {
                    last_interest_dt: datetime_to_str(new Date(2021, 0, 1)),
                    partner_id: pyEnv.currentPartnerId,
                }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
        {
            anonymous_name: "Visitor 12",
            channel_member_ids: [
                [0, 0, {
                    last_interest_dt: datetime_to_str(new Date(2021, 0, 2)),
                    partner_id: pyEnv.currentPartnerId,
                }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss();
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_item');
    assert.strictEqual(
        initialLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        Number(initialLivechats[0].dataset.channelId),
        mailChannelId2,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        Number(initialLivechats[1].dataset.channelId),
        mailChannelId1,
        "second livechat should be the one with the less recent last activity time"
    );

    // post a new message on the last channel
    await afterNextRender(() => initialLivechats[1].click());
    await afterNextRender(() => document.execCommand('insertText', false, "Blabla"));
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());

    const newLivechats = document.querySelectorAll('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_item');
    assert.strictEqual(
        newLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        Number(newLivechats[0].dataset.channelId),
        mailChannelId1,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        Number(newLivechats[1].dataset.channelId),
        mailChannelId2,
        "second livechat should be the one with the less recent last activity time"
    );
});

QUnit.test('invite button should be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create(
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    );
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_ThreadViewTopbar_inviteButton',
        "Invite button should be visible in top bar when livechat is active thread"
    );
});

QUnit.test('call buttons should not be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create(
        {
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: 'livechat',
            livechat_operator_id: pyEnv.currentPartnerId,
        },
    );
    const { openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_ThreadViewTopbar_callButton',
        "Call buttons should not be visible in top bar when livechat is active thread"
    );
});

QUnit.test('reaction button should not be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        channel_partner_ids: [pyEnv.currentPartnerId, pyEnv.publicPartnerId],
    });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    await click('.o_Message');
    assert.containsNone(
        document.body,
        '.o_MessageActionView_actionReaction',
        "should not have action to add a reaction"
    );
});

QUnit.test('reply button should not be present on livechat', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        channel_partner_ids: [pyEnv.currentPartnerId, pyEnv.publicPartnerId],
    });
    const { click, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    await click('.o_Message');
    assert.containsNone(
        document.body,
        '.o_MessageActionView_actionReplyTo',
        "should not have reply action"
    );
});

});
});
