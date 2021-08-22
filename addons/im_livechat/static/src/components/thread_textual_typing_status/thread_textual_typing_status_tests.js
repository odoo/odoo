/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
} from '@mail/utils/test_utils';

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        beforeEach.call(this);

        this.createThreadTextualTypingStatusComponent = async thread => {
            await createRootMessagingComponent(this, "ThreadTextualTypingStatus", {
                props: { threadLocalId: thread.localId },
                target: this.webClient.el,
            });
        };
    },
});

QUnit.skip('receive visitor typing status "is typing"', async function (assert) {
    // skip: issue with visitor name
    assert.expect(2);

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
    await this.createThreadTextualTypingStatusComponent(thread);

    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "",
        "Should display no one is currently typing"
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
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Visitor 20 is typing...",
        "Should display that visitor is typing"
    );
});

});
});
});
