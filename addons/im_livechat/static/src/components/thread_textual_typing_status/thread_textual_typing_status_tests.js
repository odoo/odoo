odoo.define('im_livechat/static/src/components/thread_textual_typing_status/thread_textual_typing_status_tests.js', function (require) {
'use strict';

const components = {
    ThreadTextualTypingStatus: require('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_textual_typing_status', {}, function () {
QUnit.module('thread_textual_typing_status_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createThreadTextualTypingStatusComponent = async thread => {
            const ThreadTextualTypingStatusComponent = components.ThreadTextualTypingStatus;
            ThreadTextualTypingStatusComponent.env = this.env;
            this.component = new ThreadTextualTypingStatusComponent(null, {
                threadLocalId: thread.localId,
            });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    async afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.ThreadTextualTypingStatus.env;
    },
});

QUnit.test('receive visitor typing status "is typing"', async function (assert) {
    assert.expect(2);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_livechat: [{
                channel_type: 'livechat',
                id: 20,
                livechat_visitor: {
                    country: false,
                    id: false,
                    name: "Visitor",
                },
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }],
            }],
        },
        public_partner: {
            active: false,
            display_name: "Public Partner",
            id: 7,
        },
    });
    await this.start({
        env: {
            session: {
                name: 'Admin',
                partner_display_name: 'Your Company, Admin',
                partner_id: 3,
                uid: 2,
            },
        },
    });
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

    // simulate receive typing notification from visitor "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 7, // public partner_id
            is_typing: true,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.strictEqual(
        document.querySelector('.o_ThreadTextualTypingStatus').textContent,
        "Visitor is typing...",
        "Should display that visitor is typing"
    );
});

});
});
});

});
