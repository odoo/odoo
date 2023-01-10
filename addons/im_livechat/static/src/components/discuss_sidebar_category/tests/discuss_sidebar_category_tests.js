/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_sidebar_category', {}, function () {
QUnit.module('discuss_sidebar_category_tests.js', {
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

QUnit.test('livechat - counter: should not have a counter if the category is unfolded and without unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();
    assert.containsNone(
        document.body,
        `.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`,
        "should not have a counter if the category is unfolded and without unread messages",
    );
});

QUnit.test('livechat - counter: should not have a counter if the category is unfolded and with unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
        message_unread_counter: 10,
    });
    await this.start();
    assert.containsNone(
        document.body,
        `.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`,
        "should not have a counter if the category is unfolded and with unread messages",
    );
});

QUnit.test('livechat - counter: should not have a counter if category is folded and without unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    await this.start();

    assert.containsNone(
        document.body,
        `.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('livechat - counter: should have correct value of unread threads if category is folded and with unread messages', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
        message_unread_counter: 10,
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    await this.start();

    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`).textContent,
        "1",
        "should have correct value of unread threads if category is folded and with unread messages"
    );
});

QUnit.test('livechat - states: close manually by clicking the title', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: true,
    });
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // fold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );
});

QUnit.test('livechat - states: open manually by clicking the title', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    await this.start();

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // open the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );
});

QUnit.test('livechat - states: close should update the value on the server', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: true,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_livechat_open,
        true,
        "the value in server side should be true"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_livechat_open,
        false,
        "the value in server side should be false"
    );
});

QUnit.test('livechat - states: open should update the value on the server', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    const currentUserId = this.data.currentUserId;
    await this.start();

    const initalSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        initalSettings.is_discuss_sidebar_category_livechat_open,
        false,
        "the value in server side should be false"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    const newSettings = await this.env.services.rpc({
        model: 'res.users.settings',
        method: '_find_or_create_for_user',
        args: [[currentUserId]],
    });
    assert.strictEqual(
        newSettings.is_discuss_sidebar_category_livechat_open,
        true,
        "the value in server side should be true"
    );
});

QUnit.test('livechat - states: close from the bus', async function (assert) {
    assert.expect(2);

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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_livechat_open: false,
            },
        }]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );
});

QUnit.test('livechat - states: open from the bus', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    this.data['res.users.settings'].records.push({
        user_id: this.data.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    await this.start();

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() => {
        this.env.services.bus_service.trigger('notification', [{
            type: "res.users.settings/changed",
            payload: {
                is_discuss_sidebar_category_livechat_open: true,
            },
        }]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );
});


QUnit.test('livechat - states: category item should be invisible if the catgory is closed', async function (assert) {
    assert.expect(2);

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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

QUnit.test('livechat - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(3);

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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    const livechat = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.messaging.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        livechat.click();
    });
    assert.ok(livechat.classList.contains('o-active'));

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active livechat item should remain even if the category is folded'
    );
});

});
});
});
