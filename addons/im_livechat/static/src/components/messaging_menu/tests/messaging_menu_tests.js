/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu', {}, function () {
QUnit.module('messaging_menu_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const res = await start(Object.assign({}, params, {
                data: this.data,
            }));
            const { env, widget } = res;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('livechats should be in "chat" filter', async function (assert) {
    assert.expect(7);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    const { createMessagingMenuComponent } = await this.start();
    await createMessagingMenuComponent();
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu',
        "should have messaging menu"
    );

    await afterNextRender(() => document.querySelector('.o_MessagingMenu_toggler').click());
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu_tabButton[data-tab-id="all"]',
        "should have a tab/filter 'all' in messaging menu"
    );
    assert.containsOnce(
        document.body,
        '.o_MessagingMenu_tabButton[data-tab-id="chat"]',
        "should have a tab/filter 'chat' in messaging menu"
    );
    assert.hasClass(
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="all"]'),
        'o-active',
        "tab/filter 'all' of messaging menu should be active initially"
    );
    assert.containsOnce(
        document.body,
        `.o_ThreadPreview[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "livechat should be listed in 'all' tab/filter of messaging menu"
    );

    await afterNextRender(() =>
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="chat"]').click()
    );
    assert.hasClass(
        document.querySelector('.o_MessagingMenu_tabButton[data-tab-id="chat"]'),
        'o-active',
        "tab/filter 'chat' of messaging menu should become active after click"
    );
    assert.containsOnce(
        document.body,
        `.o_ThreadPreview[data-thread-local-id="${
            this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: 11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "livechat should be listed in 'chat' tab/filter of messaging menu"
    );
});

});
});
});
