odoo.define('im_livechat/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js', function (require) {
'use strict';

const components = {
    ThreadTextualTypingStatus: require('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadTextualTypingStatusComponent = async thread => {
            await createRootComponent(this, components.ThreadTextualTypingStatus, {
                props: { threadLocalId: thread.localId },
                target: this.widget.el,
            });
        };

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('receive visitor typing status "is typing"', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({
        anonymous_name: "Visitor 20",
        channel_type: 'livechat',
        id: 20,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start();
    const thread = this.env.models['mail.thread'].find(thread =>
        thread.id === 20 &&
        thread.model === 'mail.channel'
    );
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
            partner_id: this.env.messaging.publicPartner.id,
            partner_name: this.env.messaging.publicPartner.name,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
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

});
