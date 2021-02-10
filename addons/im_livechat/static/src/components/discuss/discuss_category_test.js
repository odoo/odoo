odoo.define('im_livechat/static/src/components/discuss/discuss_category_test.js', function (require) {
'use strict';

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_category_test.js', {
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

        // prepare random category item data for livechat category
        this.data['mail.channel'].records.push({
            anonymous_name: "Visitor 11",
            channel_type: 'livechat',
            id: 11,
            livechat_operator_id: this.data.currentPartnerId,
            members: [this.data.currentPartnerId, this.data.publicPartnerId],
        });
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('category: open and close manually', async function (assert) {
    assert.expect(3);
    
    await this.start();
    assert.containsOnce(
        document.body,
        `.o_Category[data-category-local-id="${ this.env.messaging.discuss.categoryLivechat.localId }"]`,
        "Category livechat should exist"
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
});

QUnit.test('category: open and close from bus', async function (assert) {
    assert.expect(3);
    await this.start();

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

});
