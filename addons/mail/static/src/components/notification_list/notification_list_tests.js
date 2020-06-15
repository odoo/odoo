odoo.define('mail/static/src/components/notification_list/notification_list_tests.js', function (require) {
'use strict';

const components = {
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
};

const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list', {}, function () {
QUnit.module('notification_list_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {Object} param0
         * @param {string} [param0.filter='all']
         */
        this.createNotificationListComponent = async ({ filter = 'all' }) => {
            const NotificationListComponent = components.NotificationList;
            NotificationListComponent.env = this.env;
            this.component = new NotificationListComponent(null, { filter });
            await afterNextRender(() => this.component.mount(this.widget.el));
        };

        this.start = async params => {
            Object.assign(this.data.initMessaging, {
                channel_slots: {
                    channel_channel: [{
                        channel_type: 'channel',
                        id: 100,
                        is_pinned: true,
                        name: "Channel 2019",
                        message_unread_counter: 0,
                    }, {
                        channel_type: 'channel',
                        id: 200,
                        is_pinned: true,
                        name: "Channel 2020",
                        message_unread_counter: 0,
                    }],
                },
            });
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
            this.component = undefined;
        }
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
        this.env = undefined;
        delete components.NotificationList.env;
    },
});

QUnit.test('marked as read thread notifications are ordered by last message date', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 100,
        message_unread_counter: 0,
        name: "Channel 2019",
    }, {
        channel_type: 'channel',
        id: 200,
        message_unread_counter: 0,
        name: "Channel 2020",
    }];
    this.data['mail.message'].records = [{
        author_id: [10, "Author A"],
        body: "<p>Message A</p>",
        channel_ids: [100],
        date: "2019-01-01 00:00:00",
        id: 42,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'Channel 2019',
        res_id: 100,
    }, {
        author_id: [20, "Author B"],
        body: "<p>Message B</p>",
        channel_ids: [200],
        date: "2020-01-01 00:00:00",
        id: 43,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'Channel 2020',
        res_id: 200,
    }];
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

    this.data['mail.channel'].records = [{
        channel_type: 'channel',
        id: 100,
        message_unread_counter: 0,
        name: "Channel 2019",
    }, {
        channel_type: 'channel',
        id: 200,
        message_unread_counter: 0,
        name: "Channel 2020",
    }];
    this.data['mail.message'].records = [{
        author_id: [10, "Author A"],
        body: "<p>Message A</p>",
        channel_ids: [100],
        date: "2019-01-01 00:00:00",
        id: 42,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'Channel 2019',
        res_id: 100,
    }, {
        author_id: [20, "Author B"],
        body: "<p>Message B</p>",
        channel_ids: [200],
        date: "2020-01-01 00:00:00",
        id: 43,
        message_type: 'comment',
        model: 'mail.channel',
        record_name: 'Channel 2020',
        res_id: 200,
    }];
    await this.start();
    await this.createNotificationListComponent({ filter: 'all' });
    assert.containsN(
        document.body,
        '.o_ThreadPreview',
        2,
        "there should be two thread previews"
    );

    await afterNextRender(() => {
        const messageData = {
            author_id: [7, "Demo User"],
            body: "<p>New message !</p>",
            channel_ids: [100],
            date: "2020-03-23 10:00:00",
            id: 44,
            message_type: 'comment',
            model: 'mail.channel',
            record_name: 'Channel 2019',
            res_id: 100,
        };
        this.widget.call('bus_service', 'trigger', 'notification', [
            [['my-db', 'mail.channel', 100], messageData]
        ]);
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

});
