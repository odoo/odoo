odoo.define('mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection_tests.js', function (require) {
'use strict';

const {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign(
                {
                    autoOpenDiscuss: true,
                    data: this.data,
                    env: {
                        browser: {
                            innerHeight: 640,
                            innerWidth: 360,
                        },
                        device: {
                            isMobile: true,
                        },
                    },
                    hasDiscuss: true,
                },
                params,
            ));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('select another mailbox', async function (assert) {
    assert.expect(7);

    await this.start();
    assert.containsOnce(
        document.body,
        '.o_Discuss',
        "should display discuss initially"
    );
    assert.hasClass(
        document.querySelector('.o_Discuss'),
        'o-mobile',
        "discuss should be opened in mobile mode"
    );
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should display a thread initially"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        this.env.messaging.inbox.localId,
        "inbox mailbox should be opened initially"
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussMobileMailboxSelection_button[
            data-mailbox-local-id="${this.env.messaging.starred.localId}"
        ]`,
        "should have a button to open starred mailbox"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussMobileMailboxSelection_button[
            data-mailbox-local-id="${this.env.messaging.starred.localId}"]
        `).click()
    );
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should still have a thread after clicking on starred mailbox"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        this.env.messaging.starred.localId,
        "starred mailbox should be opened after clicking on it"
    );
});

});
});
});

});
