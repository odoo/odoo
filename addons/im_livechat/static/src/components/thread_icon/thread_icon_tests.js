odoo.define('im_livechat/static/src/components/thread_icon/thread_icon_tests.js', function (require) {
'use strict';

const components = {
    ThreadIcon: require('mail/static/src/components/thread_icon/thread_icon.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('thread_icon', {}, function () {
QUnit.module('thread_icon_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createThreadIcon = async thread => {
            const ThreadIconComponent = components.ThreadIcon;
            ThreadIconComponent.env = this.env;
            this.component = new ThreadIconComponent(null, { threadLocalId: thread.localId });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };

    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.ThreadIcon.env;
    },
});

QUnit.test('livechat: public website visitor is typing', async function (assert) {
    assert.expect(4);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_livechat: [{
                channel_type: 'livechat',
                id: 20,
                is_pinned: true,
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

    // simulate receive typing notification from website visitor "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 7, // public partner_id
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
        "Visitor is typing...",
        "title of icon should tell visitor is currently typing"
    );
});

});
});
});

});
