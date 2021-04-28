/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

const { datetime_to_str, str_to_datetime } = require('web.time');

QUnit.module('im_livechat', {}, function () {
QUnit.module('compoents', {}, function () {
QUnit.module('category_livechat_item', {}, function () {
QUnit.module('category_livechat_item_tests.js', {
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

QUnit.test('basic: should render livechat item', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });

    await this.start();

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.ok(
        livechatItem,
        "should have correct livechat item rendered"
    );

});

QUnit.test('item name: should have correct name (without country)', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_CategoryItem_name`).textContent,
        "Visitor 11",
        "should have correct name as livechat item name"
    );
});

QUnit.test('item name: should have correct name (with country)', async function (assert) {
    assert.expect(1);

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

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_CategoryItem_name`).textContent,
        "Jean (Belgium)",
        "should have correct name and country as livechat item name"
    );
});

QUnit.test('avatar: should have a smily face avatar for an anonymous livechat item', async function (assert) {
    assert.expect(2);

    // create a livechat thread linked with an anonymous user
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.currentPartnerId],
    });
    await this.start();

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.strictEqual(
        livechatItem.querySelectorAll(`:scope .o_CategoryLivechatItem_image`).length,
        1,
        "should have an avatar"
    );
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_CategoryLivechatItem_image`).dataset.src,
        '/mail/static/src/img/smiley/avatar.jpg',
        'should have the smiley face as the avatar for anonymous users'
    );
});

QUnit.test('avatar: should have a parnter profile picture for a livechat item linked with a partner', async function (assert) {
    assert.expect(2);

    // create a livechat thread linked with a partner
    this.data['res.partner'].records.push({
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

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.strictEqual(
        livechatItem.querySelectorAll(`:scope .o_CategoryLivechatItem_image`).length,
        1,
        "should have an avatar"
    );
    assert.strictEqual(
        livechatItem.querySelector(`:scope .o_CategoryLivechatItem_image`).dataset.src,
        '/web/image/res.partner/10/image_128',
        'should have the partner profile picture as the avatar for partners'
    );
});

QUnit.test('commands: should have correct commands for livechat items', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.currentPartnerId],
    });
    await this.start();

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.strictEqual(
        livechatItem.querySelectorAll(`:scope .o_CategoryItem_commands`).length,
        1,
        "should have a commands placeholder in a livechat item"
    );
    assert.strictEqual(
        livechatItem.querySelectorAll(`:scope .o_CategoryItem_commands .o_CategoryLivechatItem_command`).length,
        1,
        "should have 1 command in a livechat item"
    );
    assert.strictEqual(
        livechatItem.querySelectorAll(`:scope .o_CategoryItem_commands .o_CategoryLivechatItem_commandUnpin`).length,
        1,
        "should have the 'unpin' command in a livechat item"
    )

});

QUnit.test('activation: should be active after clicking on a livechat item', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.currentPartnerId],
    }, {
        anonymous_name: "Visitor 21",
        channel_type: 'livechat',
        id: 21,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.currentPartnerId],
    });
    await this.start();

    const livechatItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    assert.notOk(
        livechatItem.classList.contains('o-item-active'),
        "should not be active by default"
    );

    // click the item, the item should be activiated
    await afterNextRender(() => livechatItem.click());
    assert.ok(
        livechatItem.classList.contains('o-item-active'),
        "should be active after clciking it"
    );

    // click another itme, the original one should be deactivated
    const anotherItem = document.querySelector(`
    .o_CategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 21,
            model: 'mail.channel',
        }).localId
        }"]
    `);
    await afterNextRender(() => anotherItem.click());
    assert.notOk(
        livechatItem.classList.contains('o-item-active'),
        "should not be active after another item is activated"
    );
});

QUnit.test('sort: should be sorted by last activity time', async function (assert) {
    assert.expect(6);

    this.data['mail.channel'].records.push(
        {
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_activity_time: datetime_to_str(new Date(2021, 0, 1)),  // less recent one
        },
        {
            anonymous_name: "Visitor 12",
            channel_type: 'livechat',
            id: 12,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
            last_activity_time: datetime_to_str(new Date(2021, 0 ,2)),  // more recent one
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
    const initialLivechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_CategoryItem');
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

    // update livechat 11 with a more recent last activity time
    await afterNextRender(() => {
        livechat11.update({
            lastActivityTime: new Date(2021, 0 ,3),
        });
    });
    const newLivechats = document.querySelectorAll('.o_DiscussSidebar_groupLivechat .o_CategoryItem');
    assert.strictEqual(
        initialLivechats.length,
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

});
});
});
