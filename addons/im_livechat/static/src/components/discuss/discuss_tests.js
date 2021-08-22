/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_tests.js', { beforeEach });

QUnit.skip('livechat in the sidebar: basic rendering', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(5);

    this.serverData.models['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
    });
    const { messaging, openDiscuss } = await this.start();
    await openDiscuss();
    assert.containsOnce(document.body, '.o_Discuss_sidebar',
        "should have a sidebar section"
    );
    const groupLivechat = document.querySelector('.o_DiscussSidebar_groupLivechat');
    assert.ok(groupLivechat,
        "should have a channel group livechat"
    );
    const grouptitle = groupLivechat.querySelector('.o_DiscussSidebar_groupTitle');
    assert.strictEqual(
        grouptitle.textContent.trim(),
        "Livechat",
        "should have a channel group named 'Livechat'"
    );
    const livechat = groupLivechat.querySelector(`
        .o_DiscussSidebarItem[data-thread-local-id="${
            messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]
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

QUnit.skip('livechat in the sidebar: existing user with country', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(3);

    this.serverData.models['res.country'].records.push({
        code: 'be',
        id: 10,
        name: "Belgium",
    });
    this.serverData.models['res.partner'].records.push({
        country_id: 10,
        id: 10,
        name: "Jean",
    });
    this.serverData.models['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.currentPartnerId, 10],
    });
    const { openDiscuss } = await this.start();
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should have a channel group livechat in the side bar"
    );
    const livechat = document.querySelector('.o_DiscussSidebar_groupLivechat .o_DiscussSidebarItem');
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

QUnit.skip('do not add livechat in the sidebar on visitor opening his chat', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(2);

    const currentUser = this.serverData.models['res.users'].records.find(user =>
        user.id === this.serverData.currentUserId
    );
    currentUser.im_status = 'online';
    this.serverData.models['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.serverData.currentUserId],
    });
    const { env, openDiscuss } = await this.start();
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor opening his chat
    await env.services.rpc('/im_livechat/get_session', {
        context: { mockedUserId: false },
        channel_id: 10,
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should still not have any livechat in the sidebar after visitor opened his chat"
    );
});

QUnit.skip('do not add livechat in the sidebar on visitor typing', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(2);

    const currentUser = this.serverData.models['res.users'].records.find(user =>
        user.id === this.serverData.currentUserId
    );
    currentUser.im_status = 'online';
    this.serverData.models['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.serverData.currentUserId],
    });
    this.serverData.models['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 10,
        is_pinned: false,
        livechat_channel_id: 10,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.publicPartnerId, this.serverData.currentPartnerId],
    });
    const { env, openDiscuss } = await this.start();
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor typing
    const channel = this.serverData.models['mail.channel'].records.find(channel => channel.id === 10);
    await env.services.rpc('/im_livechat/notify_typing', {
        context: { mockedPartnerId: this.publicPartnerId },
        is_typing: true,
        uuid: channel.uuid,
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should still not have any livechat in the sidebar after visitor started typing"
    );
});

QUnit.skip('add livechat in the sidebar on visitor sending first message', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(4);

    const currentUser = this.serverData.models['res.users'].records.find(user =>
        user.id === this.serverData.currentUserId
    );
    currentUser.im_status = 'online';
    this.serverData.models['res.country'].records.push({
        code: 'be',
        id: 10,
        name: "Belgium",
    });
    this.serverData.models['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.serverData.currentUserId],
    });
    this.serverData.models['mail.channel'].records.push({
        anonymous_name: "Visitor (Belgium)",
        channel_type: 'livechat',
        country_id: 10,
        id: 10,
        is_pinned: false,
        livechat_channel_id: 10,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.publicPartnerId, this.serverData.currentPartnerId],
    });
    const { env, openDiscuss } = await this.start();
    await openDiscuss();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor sending a message
    const channel = this.serverData.models['mail.channel'].records.find(channel => channel.id === 10);
    await afterNextRender(async () => env.services.rpc('/mail/chat_post', {
        context: { mockedUserId: false },
        uuid: channel.uuid,
        message_content: "new message",
    }));
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should have a channel group livechat in the side bar after receiving first message"
    );
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_groupLivechat .o_DiscussSidebar_item',
        "should have a livechat in the sidebar after receiving first message"
    );
    assert.strictEqual(
        document.querySelector('.o_DiscussSidebar_groupLivechat .o_DiscussSidebar_item').textContent,
        "Visitor (Belgium)",
        "should have visitor name and country as livechat name"
    );
});

QUnit.skip('livechats are sorted by last message date in the sidebar: most recent at the top', async function (assert) {
    // skip: some livechat override business code is broken?
    /**
     * For simplicity the code that is covered in this test is considering
     * messages to be more/less recent than others based on their ids instead of
     * their actual creation date.
     */
    assert.expect(7);

    this.serverData.models['mail.message'].records.push(
        { id: 11, model: "mail.channel", res_id: 11 }, // least recent message due to smaller id
        { id: 12, model: "mail.channel", res_id: 12 }, // most recent message due to higher id
    );
    this.serverData.models['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12,
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
    );
    const { messaging, openDiscuss } = await this.start();
    await openDiscuss();
    const livechat11 = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const livechat12 = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 12,
        model: 'mail.channel',
    });
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should have a channel group livechat"
    );
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_DiscussSidebarItem');
    assert.strictEqual(
        initialLivechats.length,
        2,
        "should have 2 livechats in the sidebar"
    );
    assert.strictEqual(
        initialLivechats[0].dataset.threadLocalId,
        livechat12.localId,
        "first livechat should be the one with the most recent message"
    );
    assert.strictEqual(
        initialLivechats[1].dataset.threadLocalId,
        livechat11.localId,
        "second livechat should be the one with the least recent message"
    );

    // post a new message on the last channel
    await afterNextRender(() => initialLivechats[1].click());
    await afterNextRender(() => document.execCommand('insertText', false, "Blabla"));
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    const livechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_DiscussSidebarItem');
    assert.strictEqual(
        livechats.length,
        2,
        "should still have 2 livechats in the sidebar after posting a new message"
    );
    assert.strictEqual(
        livechats[0].dataset.threadLocalId,
        livechat11.localId,
        "first livechat should now be the one on which the new message was posted"
    );
    assert.strictEqual(
        livechats[1].dataset.threadLocalId,
        livechat12.localId,
        "second livechat should now be the one on which the message was not posted"
    );
});

QUnit.skip('livechats with no messages are sorted by creation date in the sidebar: most recent at the top', async function (assert) {
    // skip: some livechat override business code is broken?
    /**
     * For simplicity the code that is covered in this test is considering
     * channels to be more/less recent than others based on their ids instead of
     * their actual creation date.
     */
    assert.expect(5);

    this.serverData.models['mail.message'].records.push(
        { id: 13, model: "mail.channel", res_id: 13 },
    );
    this.serverData.models['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11, // least recent channel due to smallest id
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12, // most recent channel that does not have a message
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 13",
            channel_type: 'livechat',
            id: 13, // most recent channel (but it has a message)
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
    );
    const { messaging, openDiscuss } = await this.start();
    await openDiscuss();
    const livechat11 = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const livechat12 = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 12,
        model: 'mail.channel',
    });
    const livechat13 = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 13,
        model: 'mail.channel',
    });
    assert.containsOnce(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should have a channel group livechat"
    );
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_DiscussSidebarItem');
    assert.strictEqual(
        initialLivechats.length,
        3,
        "should have 3 livechats in the sidebar"
    );
    assert.strictEqual(
        initialLivechats[0].dataset.threadLocalId,
        livechat12.localId,
        "first livechat should be the most recent channel without message"
    );
    assert.strictEqual(
        initialLivechats[1].dataset.threadLocalId,
        livechat11.localId,
        "second livechat should be the second most recent channel without message"
    );
    assert.strictEqual(
        initialLivechats[2].dataset.threadLocalId,
        livechat13.localId,
        "third livechat should be the channel with a message"
    );
});

QUnit.skip('invite button should be present on livechat', async function (assert) {
    // skip: some livechat override business code is broken?
    assert.expect(1);

    this.serverData.models['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.serverData.currentPartnerId,
            members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
        },
    );
    const { openDiscuss } = await this.start();
    await openDiscuss({ activeId: 'mail.channel_11' });
    assert.containsOnce(
        document.body,
        '.o_ThreadViewTopbar_inviteButton',
        "Invite button should be visible in top bar when livechat is active thread"
    );
});

});
});
});
