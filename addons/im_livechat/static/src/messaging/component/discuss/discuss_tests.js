odoo.define('im_livechat.messaging.component.DiscussTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    pause,
    start: utilsStart,
} = require('mail.messaging.testUtils');

QUnit.module('im_livechat', {}, function () {
QUnit.module('messaging', {}, function () {
QUnit.module('component', {}, function () {
QUnit.module('Discuss', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.widget) {
            this.widget.destroy();
        }
    },
});

QUnit.test('livechat in the sidebar', async function (assert) {
    assert.expect(5);

    this.data.initMessaging = {
        channel_slots: {
            channel_livechat: [{
                id: 1,
                channel_type: "livechat",
                correspondent_name: "Visitor",
            }],
        },
    };

    await this.start();

    assert.containsOnce(document.body, '.o_Discuss_sidebar',
        "should have a sidebar section"
    );
    const groupLivechat = document.querySelector('.o_DiscussSidebar_groupLivechat');
    assert.ok(groupLivechat,
        "should have a channel group livechat"
    );
    const grouptitle = groupLivechat.querySelector('.o_DiscussSidebar_groupTitle');
    assert.strictEqual(
        grouptitle.textContent.trim(),
        "Livechat",
        "should have a channel group named 'Livechat'"
    );
    const livechat = groupLivechat.querySelector(`
        .o_DiscussSidebarItem[data-thread-local-id="${
            this.env.entities.Thread.channelFromId(1).localId
        }"]
    `);
    assert.ok(
        livechat,
        "should have a livechat in sidebar"
    );
    assert.strictEqual(
        livechat.textContent,
        "Visitor",
        "should have 'Visitor' as livechat name"
    );
});

});
});
});

});
