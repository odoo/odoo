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
