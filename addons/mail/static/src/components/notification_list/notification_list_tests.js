odoo.define('mail/static/src/components/notification_list/notification_list_tests.js', function (require) {
'use strict';

const components = {
    NotificationList: require('mail/static/src/components/notification_list/notification_list.js'),
};

const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

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
            await createRootComponent(this, components.NotificationList, {
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
            channel_ids: [100],
            date: "2019-01-01 00:00:00",
            id: 42,
            model: 'mail.channel',
            res_id: 100,
        },
        {
            channel_ids: [200],
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
            channel_ids: [100],
            date: "2019-01-01 00:00:00",
            id: 42,
            model: 'mail.channel',
            res_id: 100,
        },
        {
            channel_ids: [200],
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

QUnit.test('last message of thread preview cannot be a transient one', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({
        id: 11,
        name: "Stranger",
    });
    this.data['mail.channel'].records.push({
        id: 11,
        is_pinned: true,
        message_unread_counter: 1,
    });
    this.data['mail.message'].records.push({
        author_id: 11,
        body: "this is the last message",
        channel_ids: [11],
        id: 100,
        model: 'mail.channel',
        res_id: 11,
    });
    await this.start({
        hasChatWindow: true,
    });
    await this.createNotificationListComponent({ filter: 'all' });
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview',
        "there should be one thread preview displayed for channel #11"
    );
    assert.containsOnce(
        document.body,
        '.o_ThreadPreview_inlineText',
        "last message of the thread should be displayed for channel #11"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_inlineText').textContent,
        "Stranger: this is the last message",
        "the last message displayed is the last message of channel #11"
    );

    await afterNextRender(() => document.querySelector('.o_ThreadPreview').click());
    assert.containsOnce(
        document.body,
        `.o_ChatWindow[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id:11,
                model: 'mail.channel',
            }).localId
        }"]`,
        "a chat window should have been opened on channel #11 after click on its thread preview"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "opened chat window should only contain the initial message of channel #11"
    );

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "/who"));
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "chat window should now contain two messages (initial one + the transient just received)"
    );
    assert.strictEqual(
        document.querySelector('.o_ThreadPreview_inlineText').textContent,
        "Stranger: this is the last message",
        "the last message displayed should remain unchanged as new message is transient should be ignored"
    );
});

QUnit.test('thread notifications are not re-ordered on receiving a new transient message', async function (assert) {
    assert.expect(7);

    this.data['mail.channel'].records.push(
        { id: 100, name: "Channel 2019" },
        { id: 200, name: "Channel 2020" }
    );
    this.data['mail.message'].records.push(
        {
            channel_ids: [100],
            date: "2019-01-01 00:00:00",
            id: 42,
            model: 'mail.channel',
            res_id: 100,
        },
        {
            channel_ids: [200],
            date: "2020-01-01 00:00:00",
            id: 43,
            model: 'mail.channel',
            res_id: 200,
        }
    );
    await this.start({
        hasChatWindow: true,
    });
    await this.createNotificationListComponent({ filter: 'all' });
    assert.containsN(
        document.body,
        '.o_ThreadPreview',
        2,
        "there should be two thread previews"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_ThreadPreview')[0].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2020',
        "First channel in the list should be 'Channel 2020'"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_ThreadPreview')[1].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2019',
        "Second channel in the list should be 'Channel 2019'"
    );

    await afterNextRender(() => document.querySelector(`.o_ThreadPreview[data-thread-local-id="${
        this.env.models['mail.thread'].findFromIdentifyingData({
            id: 100,
            model: 'mail.channel',
        }).localId
    }"]`).click());
    assert.containsOnce(
        document.body,
        `.o_ChatWindow[data-thread-local-id="${
            this.env.models['mail.thread'].findFromIdentifyingData({
                id:100,
                model: 'mail.channel',
            }).localId
        }"]`,
        "a chat window should have been opened on channel 2019 after click on its thread preview"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "opened chat window should only contain the initial message of channel 2019"
    );

    document.querySelector('.o_ComposerTextInput_textarea').focus();
    await afterNextRender(() => document.execCommand('insertText', false, "/who"));
    await afterNextRender(() => {
        const kevt = new window.KeyboardEvent('keydown', { key: "Enter" });
        document.querySelector('.o_ComposerTextInput_textarea').dispatchEvent(kevt);
    });
    assert.strictEqual(
        document.querySelectorAll('.o_ThreadPreview')[0].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2020',
        "First channel in the list should still be 'Channel 2020' after receiving a transient message"
    );
    assert.strictEqual(
        document.querySelectorAll('.o_ThreadPreview')[1].querySelector(':scope .o_ThreadPreview_name').textContent,
        'Channel 2019',
        "Second channel in the list should still be 'Channel 2019' after receiving a transient message"
    );
});

});
});
});

});
