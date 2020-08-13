odoo.define('im_livechat/static/src/components/discuss/discuss_tests.js', function (require) {
'use strict';

const { afterEach, beforeEach, start } = require('mail/static/src/utils/test_utils.js');

QUnit.module('im_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('livechat in the sidebar: basic rendering', async function (assert) {
    assert.expect(5);

    // channel that is expected to be found in the sidebar
    this.data['mail.channel'].records.push({
        channel_type: 'livechat', // channel is expected to be livechat
        id: 11, // random unique id, will be referenced in the test
        livechat_visitor: {
            name: "Visitor 11", // random name, will be asserted during the test
        },
    });
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
            this.env.models['mail.thread'].find(thread =>
                thread.id === 11 &&
                thread.model === 'mail.channel'
            ).localId
        }"]
    `);
    assert.ok(
        livechat,
        "should have a livechat in sidebar"
    );
    assert.strictEqual(
        livechat.textContent,
        "Visitor 11",
        "should have 'Visitor 11' as livechat name"
    );
});

});
});
});

});
