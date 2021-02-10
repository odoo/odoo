odoo.define('mail/static/src/components/discuss/tests/discuss_category_tests.js', function (require) {
'use strict';

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_category_tests.js', {
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

        // prepare random category item data for channel and chat categories
        this.data['mail.channel'].records.push({ id:20, name:"General Channel" });
        this.data['res.partner'].records.push({ id: 17, name: "Demo", im_status: 'offline' });
        this.data['mail.channel'].records.push({
            channel_type: 'chat',
            id: 10, 
            members: [this.data.currentPartnerId, 17], 
            public: 'private',
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('category: open and close manually', async function (assert) {
    assert.expect(6);

    await this.start();
    // category channel 
    assert.containsOnce(
        document.body,
        `.o_Category[data-category-local-id="${ this.env.messaging.discuss.categoryChannel.localId }"]`,
        "Category channel should exist"
    );
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
    await afterNextRender(() => 
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryChannel.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
    // category chat
    assert.containsOnce(
        document.body,
        `.o_Category[data-category-local-id="${ this.env.messaging.discuss.categoryChat.localId }"]`,
        "Category chat should exist"
    );
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
    await afterNextRender(() => 
        document.querySelector(`.o_Category[data-category-local-id="${
            this.env.messaging.discuss.categoryChat.localId }"]
            .o_CategoryTitle_header
        `).click()
    );
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );

});

QUnit.test('category: open and close from bus', async function (assert) {
    assert.expect(6);
    await this.start();

    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "category_states",
                is_category_channel_open: false,
                is_category_chat_open: false,
            }
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be closed and the content should be invisible"
    );
    assert.containsNone(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be closed and the content should be invisible"
    );

    await afterNextRender(() => {
        const notif = [
            ["dbName", "res.partner", this.env.messaging.currentPartner.id],
            {
                type: "category_states",
                is_category_channel_open: true,
                is_category_chat_open: true,
            }
        ];
        this.env.services.bus_service.trigger('notification', [notif]);
    });
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 20,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category channel should be open and the content should be visible"
    );
    assert.containsOnce(
        document.body,
        `.o_CategoryItem[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id: 10,
                model: 'mail.channel',
            }).localId
        }"]`,
        "Category chat should be open and the content should be visible"
    );
});
});
});
});

});
