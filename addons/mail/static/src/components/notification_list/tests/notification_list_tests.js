/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list', {}, function () {
QUnit.module('notification_list_tests.js', {
    beforeEach() {
        beforeEach(this);

        /**
         * @param {Object} param0
         * @param {string} [param0.filter='all']
         */
        this.createNotificationListComponent = async ({ filter = 'all' }) => {
            await createRootMessagingComponent(this, "NotificationList", {
                props: { filter },
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

QUnit.test('marked as read thread notifications are ordered by last message date', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push(
        { id: 100, name: "Channel 2019" },
        { id: 200, name: "Channel 2020" }
    );
    this.data['mail.message'].records.push(
        {
            date: "2019-01-01 00:00:00",
            id: 42,
            model: 'mail.channel',
            res_id: 100,
        },
        {
            date: "2020-01-01 00:00:00",
            id: 43,
            model: 'mail.channel',
            res_id: 200,
        }
    );
    await this.start();
    await this.createNotificationListComponent({ filter: 'all' });
    assert.containsN(
        document.body,
        '.o_ThreadPreview',
        2,
        "there should be two thread previews"
    );
    const threadPreviewElList = document.querySelectorAll('.o_ThreadPreview');
    assert.strictEqual(
        threadPreviewElList[0].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2020',
        "First channel in the list should be the channel of 2020 (more recent last message)"
    );
    assert.strictEqual(
        threadPreviewElList[1].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2019',
        "Second channel in the list should be the channel of 2019 (least recent last message)"
    );
});

QUnit.test('thread notifications are re-ordered on receiving a new message', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push(
        { id: 100, name: "Channel 2019" },
        { id: 200, name: "Channel 2020" }
    );
    this.data['mail.message'].records.push(
        {
            date: "2019-01-01 00:00:00",
            id: 42,
            model: 'mail.channel',
            res_id: 100,
        },
        {
            date: "2020-01-01 00:00:00",
            id: 43,
            model: 'mail.channel',
            res_id: 200,
        }
    );
    await this.start();
    await this.createNotificationListComponent({ filter: 'all' });
    assert.containsN(
        document.body,
        '.o_ThreadPreview',
        2,
        "there should be two thread previews"
    );

    await afterNextRender(() => {
        this.widget.call('bus_service', 'trigger', 'notification', [{
            type: 'mail.channel/new_message',
            payload: {
                id: 100,
                message: {
                    author_id: [7, "Demo User"],
                    body: "<p>New message !</p>",
                    date: "2020-03-23 10:00:00",
                    id: 44,
                    message_type: 'comment',
                    model: 'mail.channel',
                    record_name: 'Channel 2019',
                    res_id: 100,
                },
            },
        }]);
    });
    assert.containsN(
        document.body,
        '.o_ThreadPreview',
        2,
        "there should still be two thread previews"
    );
    const threadPreviewElList = document.querySelectorAll('.o_ThreadPreview');
    assert.strictEqual(
        threadPreviewElList[0].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2019',
        "First channel in the list should now be 'Channel 2019'"
    );
    assert.strictEqual(
        threadPreviewElList[1].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2020',
        "Second channel in the list should now be 'Channel 2020'"
    );
});

});
});
});
