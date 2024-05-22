odoo.define('im_livechat/static/src/components/discuss/discuss_tests.js', function (require) {
'use strict';

const {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('livechat in the sidebar: basic rendering', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();
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
            this.env.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('livechat in the sidebar: existing user with country', async function (assert) {
    assert.expect(3);

    this.data['res.country'].records.push({
        code: 'be',
        id: 10,
        name: "Belgium",
    });
    this.data['res.partner'].records.push({
        country_id: 10,
        id: 10,
        name: "Jean",
    });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, 10],
    });
    await this.start();
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

QUnit.test('do not add livechat in the sidebar on visitor opening his chat', async function (assert) {
    assert.expect(2);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    currentUser.im_status = 'online';
    this.data['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.data.currentUserId],
    });
    await this.start();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor opening his chat
    await this.env.services.rpc({
        route: '/im_livechat/get_session',
        params: {
            context: {
                mockedUserId: false,
            },
            channel_id: 10,
        },
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should still not have any livechat in the sidebar after visitor opened his chat"
    );
});

QUnit.test('do not add livechat in the sidebar on visitor typing', async function (assert) {
    assert.expect(2);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    currentUser.im_status = 'online';
    this.data['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.data.currentUserId],
    });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 10,
        is_pinned: false,
        livechat_channel_id: 10,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.publicPartnerId, this.data.currentPartnerId],
    });
    await this.start();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor typing
    const channel = this.data['mail.channel'].records.find(channel => channel.id === 10);
    await this.env.services.rpc({
        route: '/im_livechat/notify_typing',
        params: {
            context: {
                mockedPartnerId: this.publicPartnerId,
            },
            is_typing: true,
            uuid: channel.uuid,
        },
    });
    await nextAnimationFrame();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should still not have any livechat in the sidebar after visitor started typing"
    );
});

QUnit.test('add livechat in the sidebar on visitor sending first message', async function (assert) {
    assert.expect(4);

    const currentUser = this.data['res.users'].records.find(user =>
        user.id === this.data.currentUserId
    );
    currentUser.im_status = 'online';
    this.data['res.country'].records.push({
        code: 'be',
        id: 10,
        name: "Belgium",
    });
    this.data['im_livechat.channel'].records.push({
        id: 10,
        user_ids: [this.data.currentUserId],
    });
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor (Belgium)",
        channel_type: 'livechat',
        country_id: 10,
        id: 10,
        is_pinned: false,
        livechat_channel_id: 10,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.publicPartnerId, this.data.currentPartnerId],
    });
    await this.start();
    assert.containsNone(
        document.body,
        '.o_DiscussSidebar_groupLivechat',
        "should not have any livechat in the sidebar initially"
    );

    // simulate livechat visitor sending a message
    const channel = this.data['mail.channel'].records.find(channel => channel.id === 10);
    await afterNextRender(async () => this.env.services.rpc({
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

QUnit.test('livechats are sorted by last message date in the sidebar: most recent at the top', async function (assert) {
    /**
     * For simplicity the code that is covered in this test is considering
     * messages to be more/less recent than others based on their ids instead of
     * their actual creation date.
     */
    assert.expect(7);

    this.data['mail.message'].records.push(
        { id: 11, channel_ids: [11] }, // least recent message due to smaller id
        { id: 12, channel_ids: [12] }, // most recent message due to higher id
    );
    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
    );
    await this.start();
    const livechat11 = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const livechat12 = this.env.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('livechats with no messages are sorted by creation date in the sidebar: most recent at the top', async function (assert) {
    /**
     * For simplicity the code that is covered in this test is considering
     * channels to be more/less recent than others based on their ids instead of
     * their actual creation date.
     */
    assert.expect(5);

    this.data['mail.message'].records.push(
        { id: 13, channel_ids: [13] },
    );
    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11, // least recent channel due to smallest id
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12, // most recent channel that does not have a message
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
        {
            anonymous_name: "Visitor 13",
            channel_type: 'livechat',
            id: 13, // most recent channel (but it has a message)
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
    );
    await this.start();
    const livechat11 = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const livechat12 = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 12,
        model: 'mail.channel',
    });
    const livechat13 = this.env.models['mail.thread'].findFromIdentifyingData({
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

QUnit.test('invite button should be present on livechat', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        },
    );
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_11',
            },
        },
    });
    assert.containsOnce(
        document.body,
        '.o_widget_Discuss_controlPanelButtonInvite',
        "Invite button should be visible in control panel when livechat is active thread"
    );
});

});
});
});

});
