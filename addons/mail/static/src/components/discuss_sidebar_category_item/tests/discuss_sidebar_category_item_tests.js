/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

import { datetime_to_str } from 'web.time';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_category_item', {}, function () {
QUnit.module('discuss_sidebar_category_item_tests.js', {
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

QUnit.test('channel - avatar: should have correct avatar', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        avatarCacheKey: '100111',
        id: 20,
    });

    await this.start();

    const channelItem = document.querySelector(`
        .o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.strictEqual(
        channelItem.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_image`).length,
        1,
        "channel should have an avatar"
    );

    assert.strictEqual(
        channelItem.querySelector(`:scope .o_DiscussSidebarCategoryItem_image`).dataset.src,
        '/web/image/mail.channel/20/avatar_128?unique=100111',
        'should link to the correct picture source'
    );

});

QUnit.test('channel - avatar: should update avatar url from bus', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        avatarCacheKey: '101010',
        id: 20,
     });

    await this.start();

    const channelItemAvatar = document.querySelector(`
        .o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"] .o_DiscussSidebarCategoryItem_image
    `);

    assert.strictEqual(
        channelItemAvatar.dataset.src,
        '/web/image/mail.channel/20/avatar_128?unique=101010',
    );

    await afterNextRender(() => {
        this.env.services.rpc({
            model: 'mail.channel',
            method: 'write',
            args: [[20], { image_128: 'This field does not matter' }],
        });
    });
    const result = await this.env.services.rpc({
        model: 'mail.channel',
        method: 'read',
        args: [[20], ['avatarCacheKey']],
    });
    const newCacheKey = result[0]['avatarCacheKey'];

    // FIXME: current test framework does not replace `src` with `data-src` during the re-rendering.
    assert.strictEqual(
        channelItemAvatar.getAttribute('src'),
        `/web/image/mail.channel/20/avatar_128?unique=${newCacheKey}`,
    );
});

QUnit.test('chat - avatar: should have correct avatar', async function (assert) {
    assert.expect(2);

    this.data['res.partner'].records.push({ id: 15, name: "Demo", im_status: 'offline' });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        members: [this.data.currentPartnerId, 15],
        public: 'private',
    });
    await this.start();

    const chatItem = document.querySelector(`
        .o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]
    `);
    assert.strictEqual(
        chatItem.querySelectorAll(`:scope .o_DiscussSidebarCategoryItem_image`).length,
        1,
        "chat should have an avatar"
    );

    assert.strictEqual(
        chatItem.querySelector(`:scope .o_DiscussSidebarCategoryItem_image`).dataset.src,
        '/web/image/res.partner/15/avatar_128',
        'should link to the partner avatar'
    );
});

QUnit.test('chat - sorting: should be sorted by last activity time', async function (assert) {
    assert.expect(6);

    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 10,
        public: 'private',
        last_interest_dt: datetime_to_str(new Date(2021, 0, 1)), // less recent one
    }, {
        channel_type: 'chat',
        id: 20,
        public: 'private',
        last_interest_dt: datetime_to_str(new Date(2021, 0, 2)), // more recent one
    });
    await this.start();

    const chat10 = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 10,
        model: 'mail.channel',
    });
    const chat20 = this.messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const initialChats = document.querySelectorAll('.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategoryItem');
    assert.strictEqual(
        initialChats.length,
        2,
        "should have 2 livechat items"
    );
    assert.strictEqual(
        initialChats[0].dataset.threadLocalId,
        chat20.localId,
        "first livechat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        initialChats[1].dataset.threadLocalId,
        chat10.localId,
        "second chat should be the one with the less recent last activity time"
    );

    // post a new message on the last channel
    await afterNextRender(() => initialChats[1].click());
    await afterNextRender(() => document.execCommand('insertText', false, "Blabla"));
    await afterNextRender(() => document.querySelector('.o_Composer_buttonSend').click());
    const newChats = document.querySelectorAll('.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategoryItem');
    assert.strictEqual(
        newChats.length,
        2,
        "should have 2 chat items"
    );
    assert.strictEqual(
        newChats[0].dataset.threadLocalId,
        chat10.localId,
        "first chat should be the one with the more recent last activity time"
    );
    assert.strictEqual(
        newChats[1].dataset.threadLocalId,
        chat20.localId,
        "second chat should be the one with the less recent last activity time"
    );
});

});
});
});
