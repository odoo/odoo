/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

import { datetime_to_str } from 'web.time';

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
        .o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
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
        '.o_DiscussSidebar_categoryLivechat',
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
        '.o_DiscussSidebar_categoryLivechat',
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
        '.o_DiscussSidebar_categoryLivechat',
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
        '.o_DiscussSidebar_categoryLivechat',
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
        '.o_DiscussSidebar_categoryLivechat',
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

    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_interest_dt: datetime_to_str(new Date(2021, 0, 1)), // less recent one
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_interest_dt: datetime_to_str(new Date(2021, 0, 2)), // more recent one
        },
    );
    await this.start();
    const livechat11 = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 11,
        model: 'mail.channel',
    });
    const livechat12 = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 12,
        model: 'mail.channel',
    });
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategoryItem');
    assert.strictEqual(
        initialLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        initialLivechats[0].dataset.threadLocalId,
        livechat12.localId,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        initialLivechats[1].dataset.threadLocalId,
        livechat11.localId,
        "second livechat should be the one with the less recent last activity time"
    );

    // post a new message on the last channel
    await afterNextRender(() => initialLivechats[1].click());
    await afterNextRender(() => document.execCommand('insertText', false, "Blabla"));
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());

    const newLivechats = document.querySelectorAll('.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategoryItem');
    assert.strictEqual(
        newLivechats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        newLivechats[0].dataset.threadLocalId,
        livechat11.localId,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        newLivechats[1].dataset.threadLocalId,
        livechat12.localId,
        "second livechat should be the one with the less recent last activity time"
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
        '.o_ThreadViewTopbar_inviteButton',
        "Invite button should be visible in top bar when livechat is active thread"
    );
});

QUnit.test('call buttons should not be present on livechat', async function (assert) {
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
    assert.containsNone(
        document.body,
        '.o_ThreadViewTopbar_callButton',
        "Call buttons should not be visible in top bar when livechat is active thread"
    );
});

QUnit.test('reaction button should not be present on livechat', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 10,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_10',
            },
        },
    });
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    await afterNextRender(() => document.querySelector('.o_Message').click());
    assert.containsNone(
        document.body,
        '.o_MessageActionList_actionReaction',
        "should not have action to add a reaction"
    );
});

QUnit.test('reply button should not be present on livechat', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 10,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_10',
            },
        },
    });
    await afterNextRender(() => {
        document.querySelector(`.o_ComposerTextInput_textarea`).focus();
        document.execCommand('insertText', false, "Test");
    });
    await afterNextRender(() =>
        document.querySelector('.o_Composer_buttonSend').click()
    );
    await afterNextRender(() => document.querySelector('.o_Message').click());
    assert.containsNone(
        document.body,
        '.o_MessageActionList_actionReply',
        "should not have reply action"
    );
});

});
});
});
