/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

const { datetime_to_str } = require('web.time');

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

QUnit.test('livechat in the sidebar: title rendering', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
        message_unread_counter: 10,
    });
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 12",
        channel_type: 'livechat',
        id: 12,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
        message_unread_counter: 20,
    });
    await this.start();
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).textContent.trim(),
        "Livechat",
        "should have a channel group named 'Livechat'"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).length,
        0,
        "should not have a counter if the category is unfolded",
    )
    // Close livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).length,
        1,
        "should have a counter when different from 0 if the category is folded"
    );
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).textContent,
        "2",
        "should have a count value of the sum of the total unread threads"
    );
});

QUnit.test('livechat in the sidebar: basic rendering', async function (assert) {
    assert.expect(12);

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

    // Close livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryItem`).length,
        0,
        "should not have livechat if the category is folded"
    );

    // Open livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryItem`).length,
        1,
        "should have a livechat if the category is unfolded"
    );
    const livechat = groupLivechat.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
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
        livechat.querySelector(`:scope .o_CategoryItem_name`).textContent,
        "Visitor 11",
        "should have 'Visitor 11' as livechat name"
    );
    assert.strictEqual(
        livechat.querySelectorAll(`:scope .o_CategoryItem_commands`).length,
        1,
        "should have commands"
    );
    assert.strictEqual(
        livechat.querySelectorAll(`:scope .o_CategoryLivechatItem_command`).length,
        1,
        "should have 1 commands"
    );
    assert.strictEqual(
        livechat.querySelectorAll(`:scope .o_CategoryLivechatItem_commandUnpin`).length,
        1,
        "should have 'unpin' commands"
    );
    // activate the livechat thread
    await afterNextRender(() => livechat.click());
    assert.ok(
        livechat.classList.contains('o-item-active'),
        "should be active after clicking it"
    );
    // Close livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryItem`).length,
        1,
        "should have the active livechat even if the category is folded"
    );
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryItem`).dataset.threadLocalId,
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId,
        "should have the active livechat with id 11"
    );
});

QUnit.test('livechat in the sidebar: avatar rendering', async function (assert) {
    assert.expect(5);

    // Create 2 livechat thread, one with partner, another one is anonymous
    this.data['res.partner'].records.push({
        id: 10,
        name: "Jean",
    });
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.currentPartnerId],
    }, {
        channel_type: 'livechat',
        id: 21,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, 10],
    });
    await this.start();

    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryItem`).length,
        2,
        "should have a livechat"
    );
    const anonymous_livechat = document.querySelector(`
        .o_DiscussSidebar_groupLivechat .o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.ok(
        anonymous_livechat,
        "should have an anonymous livechat"
    );
    assert.strictEqual(
        anonymous_livechat.querySelector(`:scope .o_CategoryLivechatItem_image`).dataset.src,
        '/mail/static/src/img/smiley/avatar.jpg',
        "anonynamous livechat should have a smiley avatar",
    );
    const partner_livechat = document.querySelector(`
        .o_DiscussSidebar_groupLivechat .o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 21,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.ok(
        partner_livechat,
        "should have a livechat linked to a partner"
    );
    assert.strictEqual(
        partner_livechat.querySelector(`:scope .o_CategoryLivechatItem_image`).dataset.src,
        '/web/image/res.partner/10/image_128',
        "livechat linked with a partner should have a partner avatar",
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
    const livechat = document.querySelector('.o_DiscussSidebar_groupLivechat .o_CategoryItem');
    assert.ok(
        livechat,
        "should have a livechat in sidebar"
    );
    assert.strictEqual(
        livechat.querySelector(':scope .o_CategoryItem_name').textContent,
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
        '.o_DiscussSidebar_groupLivechat .o_CategoryItem',
        "should have a livechat in the sidebar after receiving first message"
    );
    assert.strictEqual(
        document.querySelector('.o_DiscussSidebar_groupLivechat .o_CategoryItem_name').textContent,
        "Visitor (Belgium)",
        "should have visitor name and country as livechat name"
    );
});

QUnit.test('livechats are sorted by last activity time in the sidebar: most recent at the top', async function (assert) {
    assert.expect(4);

    this.data['mail.message'].records.push(
        { id: 11, model: "mail.channel", res_id: 11 }, // least recent message due to smaller id
        { id: 12, model: "mail.channel", res_id: 12 }, // most recent message due to higher id
    );
    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_activity_time: datetime_to_str(new Date(2021, 0, 1)),
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_activity_time: datetime_to_str(new Date(2021, 0 ,2)),
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
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_CategoryItem');
    assert.strictEqual(
        initialLivechats.length,
        2,
        "should have 2 livechats in the sidebar"
    );
    assert.strictEqual(
        initialLivechats[0].dataset.threadLocalId,
        livechat12.localId,
        "first livechat should be the one with the most recent last activity time"
    );
    assert.strictEqual(
        initialLivechats[1].dataset.threadLocalId,
        livechat11.localId,
        "second livechat should be the one with the least recent message"
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
