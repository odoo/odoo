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

    // channel that will be used for testing the typing feature
    this.data['mail.channel'].records.push({
        // channel is expected to be livechat, but channel_type set only for
        // consistency, not actually useful in the scope of this test
        channel_type: 'livechat',
        id: 20, // random unique id, will be referenced in the test
        livechat_visitor: {
            name: "Visitor 20", // random name, will be asserted during the test
        },
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
            partner_id: this.env.messaging.publicPartner.id,
            is_typing: true,
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
