/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('compoents', {}, function () {
QUnit.module('category_title', {}, function () {
QUnit.module('category_title_test.js', {
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

QUnit.test('basic: should not show in sidebar if no livechat threads exist', async function (assert) {
    assert.expect(1);

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat`).length,
        0,
        "should not show in sidebar if no livechat threads exist"
    );
});

QUnit.test('basic: should show in sidebar if any livechat threads exist', async function (assert) {
    assert.expect(1);

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat`).length,
        1,
        "render: should show in sidebar if any livechat threads exist"
    );
});

QUnit.test('title name: should have a correct title name', async function (assert) {
    assert.expect(1);

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });

    await this.start();
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).textContent.trim(),
        "Livechat",
        "should have a channel group named 'Livechat'"
    );
});

QUnit.test('counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });

    await this.start();
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with unread messages",
    )
});

QUnit.test('counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    // prepare 2 unread livechat threads
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
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with unread messages",
    )
});

QUnit.test('counter: should not have a counter if category is folded and without unread messages', async function (assert) {
    assert.expect(1);

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });

    await this.start();

    // fold the livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('counter: should have correct value of unread threads if category is folded and with unread messages', async function (assert) {
    assert.expect(1);

    // prepare 2 unread livechat threads
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

    // fold the livechat category
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_title`).click();
    });
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_groupLivechat .o_CategoryTitle_counter`).textContent,
        "2",
        "should have correct value of unread threads if category is folded and with unread messages"
    );
});

QUnit.test('category: open and close manually by clicking the title', async function (assert) {
    assert.expect(3);

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // fold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );

    // unfold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be open and the content should be visible"
    );
});

QUnit.test('category: open and close should call rpc', async function (assert) {
    assert.expect(6);

    // prepare a random livechat to show livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'set_category_states') {
                assert.step('set_category_states');
                assert.strictEqual(
                    args.kwargs.category,
                    "livechat",
                    "Correct category is sent to server to set state"
                );
            }
            return this._super(...arguments);
        }
    });

    // fold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.verifySteps(
        ['set_category_states'],
        "set_category_states should be called when folding the livechat category"
    );

    // unfold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.verifySteps(
        ['set_category_states'],
        "set_category_states should be called when unfolding the livechat category"
    );
});

QUnit.test('category: open and close from the bus', async function (assert) {
    assert.expect(3)

    // prepare a random livechat for livechat category
    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "category_states",
                is_category_livechat_open: false,
            }
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "category_states",
                is_category_livechat_open: true,
            }
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be open and the content should be visible"
    );

});

});
});
});
