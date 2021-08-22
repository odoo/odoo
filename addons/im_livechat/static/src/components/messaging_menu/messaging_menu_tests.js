/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('messaging_menu', {}, function () {
QUnit.module('messaging_menu_tests.js', { beforeEach });

QUnit.skip('livechats should be in "chat" filter', async function (assert) {
    // skip: livechat is broken?
    assert.expect(7);

    this.serverData.models['mail.channel'].records.push({
        anonymous_name: "Visitor 11",
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
    });
    const { messaging } = await this.start();
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
            messaging.models['mail.thread'].findFromIdentifyingData({
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
            messaging.models['mail.thread'].findFromIdentifyingData({
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
