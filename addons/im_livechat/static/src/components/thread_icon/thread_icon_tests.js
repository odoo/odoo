/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        beforeEach.call(this);

        this.createThreadIcon = async thread => {
            await createRootMessagingComponent(this, "ThreadIcon", {
                props: { threadLocalId: thread.localId },
                target: this.webClient.el,
            });
        };
    },
});

QUnit.skip('livechat: public website visitor is typing', async function (assert) {
    // skip: livechat mockserver not done?
    assert.expect(4);

    this.serverData.models['mail.channel'].records.push({
        anonymous_name: "Visitor 20",
        channel_type: 'livechat',
        id: 20,
        livechat_operator_id: this.serverData.currentPartnerId,
        members: [this.serverData.currentPartnerId, this.serverData.publicPartnerId],
    });
    const { messaging } = await this.start();
    const thread = messaging.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.createThreadIcon(thread);
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon',
        "should have thread icon"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon .fa.fa-comments',
        "should have default livechat icon"
    );

    // simulate receive typing notification from livechat visitor "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            is_typing: true,
            partner_id: messaging.publicPartners[0].id,
            partner_name: messaging.publicPartners[0].name,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        owl.Component.env.services.bus_service.trigger('notification', [notification]);
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_typing',
        "should have thread icon with visitor currently typing"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_typing').title,
        "Visitor 20 is typing...",
        "title of icon should tell visitor is currently typing"
    );
});

});
});
});
