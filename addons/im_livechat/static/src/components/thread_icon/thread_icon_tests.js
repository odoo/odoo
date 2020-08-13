odoo.define('im_livechat/static/src/components/thread_icon/thread_icon_tests.js', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
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
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createThreadIcon = async thread => {
            await createRootComponent(this, components.ThreadIcon, {
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

QUnit.test('livechat: public website visitor is typing', async function (assert) {
    assert.expect(4);

    // channel that will be used for testing the typing feature
    this.data['mail.channel'].records.push({
        channel_type: 'livechat', // channel is expected to be livechat
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
            partner_id: this.env.messaging.publicPartner.id,
            is_typing: true,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
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

});
