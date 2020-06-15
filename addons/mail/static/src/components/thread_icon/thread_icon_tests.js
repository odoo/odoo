odoo.define('mail/static/src/components/thread_icon/thread_icon_tests.js', function (require) {
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

QUnit.module('mail', {}, function () {
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

QUnit.test('chat: correspondent is typing', async function (assert) {
    assert.expect(5);

    Object.assign(this.data.initMessaging, {
        channel_slots: {
            channel_direct_message: [{
                channel_type: 'chat',
                direct_partner: [{
                    email: 'demo@odoo.com',
                    id: 7,
                    im_status: 'online',
                    name: "Demo",
                }],
                id: 20,
                is_pinned: true,
                members: [{
                    email: 'admin@odoo.com',
                    id: 3,
                    name: 'Admin',
                }, {
                    email: 'demo@odoo.com',
                    id: 7,
                    im_status: 'online',
                    name: 'Demo',
                }],
            }],
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
        '.o_ThreadIcon_online',
        "should have thread icon with partner im status icon 'online'"
    );

    // simulate receive typing notification from demo "is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 7,
            is_typing: true,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_typing',
        "should have thread icon with partner currently typing"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadIcon_typing').title,
        "Demo is typing...",
        "title of icon should tell demo is currently typing"
    );

    // simulate receive typing notification from demo "no longer is typing"
    await afterNextRender(() => {
        const typingData = {
            info: 'typing_status',
            partner_id: 7,
            is_typing: false,
        };
        const notification = [[false, 'mail.channel', 20], typingData];
        this.widget.call('bus_service', 'trigger', 'notification', [notification]);
    });
    assert.containsOnce(
        document.body,
        '.o_ThreadIcon_online',
        "should have thread icon with partner im status icon 'online' (no longer typing)"
    );
});

});
});
});

});
