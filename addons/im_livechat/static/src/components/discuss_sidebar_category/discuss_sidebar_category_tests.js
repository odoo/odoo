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
        document.querySelectorAll(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and without unread messages",
    );
});

QUnit.test('livechat - counter: should not have a counter if the category is unfolded and with unread messages', async function (assert) {
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
        document.querySelectorAll(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is unfolded and with unread messages",
    );
});

QUnit.test('livechat - counter: should not have a counter if category is folded and without unread messages', async function (assert) {
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
        document.querySelector(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`).length,
        0,
        "should not have a counter if the category is folded and without unread messages"
    );
});

QUnit.test('livechat - counter: should have correct value of unread threads if category is folded and with unread messages', async function (assert) {
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
        document.querySelector(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_title`).click();
    });
    assert.strictEqual(
        document.querySelector(`.o_DiscussSidebar_categoryLivechat .o_DiscussSidebarCategory_counter`).textContent,
        "2",
        "should have correct value of unread threads if category is folded and with unread messages"
    );
});

QUnit.test('livechat - states: open and close manually by clicking the title', async function (assert) {
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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // fold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be closed and the content should be invisible"
    );

    // unfold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be open and the content should be visible"
    );
});

QUnit.test('livechat - states: open and close should call rpc', async function (assert) {
    assert.expect(8);

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
            if (args.method === 'set_mail_user_settings') {
                const mailUserSettingsId = this._getRecords('mail.user.settings',
                    [['user_id', '=', this.currentUserId]],
                )[0].id;
                assert.step('set_mail_user_settings');
                assert.deepEqual(
                    args.args[0],
                    [mailUserSettingsId],
                    "correct mail user settings id should be sent to the server side"
                );
                assert.deepEqual(
                    args.kwargs.new_settings,
                    { is_discuss_sidebar_category_livechat_open: args.kwargs.new_settings.is_discuss_sidebar_category_livechat_open },
                    "Correct category states should be sent to the server side."
                );
            }
            return this._super(...arguments);
        },
    });

    // fold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when folding the livechat category"
    );

    // unfold the livechat category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );
    assert.verifySteps(
        ['set_mail_user_settings'],
        "set_mail_user_settings should be called when unfolding the livechat category"
    );
});

QUnit.test('livechat - states: open and close from the bus', async function (assert) {
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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
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
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_livechat_open: false,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
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
                type: "mail_user_settings",
                payload: {
                    is_discuss_sidebar_category_livechat_open: true,
                },
            },
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category livechat should be open and the content should be visible"
    );
});

QUnit.test('livechat - states: the active category item should be visble even if the category is closed', async function (assert) {
    assert.expect(4);

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
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`
    );

    // click the livechat thread to activate it
    const livechat = document.querySelector(`.o_DiscussSidebarCategoryItem[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 11,
            model: 'mail.channel',
        }).localId
    }"]`);
    await afterNextRender(() => {
        livechat.click();
    });
    assert.ok(livechat.classList.contains('o-active'));

    // close the category
    await afterNextRender(() =>
        document.querySelector(`.o_DiscussSidebarCategory[data-category-local-id="${
            this.env.messaging.discuss.categoryLivechat.localId}"]
            .o_DiscussSidebarCategory_title
        `).click()
    );

    assert.containsOnce(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        'the active livechat item should remain even if the category is folded'
    );

    // activate another item so the livechat thread is deactivated
    await afterNextRender(() => {
        document.querySelector(`.o_DiscussSidebarMailBox[data-thread-local-id="${
            this.env.messaging.inbox.localId
        }"]`).click();
    });

    assert.containsNone(
        document.body,
        `.o_DiscussSidebarCategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "inactive item should be invisible if the category is folded"
    );
});

});
});
});
