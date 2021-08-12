/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list', {}, function () {
QUnit.module('notification_list_notification_group_tests.js', {
    beforeEach() {
        beforeEach(this);

        /**
         * @param {Object} param0
         * @param {string} [param0.filter='all']
         */
        this.createNotificationListComponent = async ({ filter = 'all' } = {}) => {
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

QUnit.test('notification group basic layout', async function (assert) {
    assert.expect(10);

    // message that is expected to have a failure
    this.data['mail.message'].records.push({
        id: 11, // random unique id, will be used to link failure to message
        message_type: 'email', // message must be email (goal of the test)
        model: 'mail.channel', // expected value to link message to channel
        res_id: 31, // id of a random channel
        res_model_name: "Channel", // random res model name, will be asserted in the test
    });
    // failure that is expected to be used in the test
    this.data['mail.notification'].records.push({
        mail_message_id: 11, // id of the related message
        notification_status: 'exception', // necessary value to have a failure
        notification_type: 'email', // expected failure type for email message
    });
    await this.start();
    await this.createNotificationListComponent();
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_name',
        "should have 1 group name"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_name').textContent,
        "Channel",
        "should have model name as group name"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(1)",
        "should have only 1 notification in the group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_date',
        "should have 1 group date"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_date').textContent,
        "a few seconds ago",
        "should have the group date corresponding to now"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_inlineText',
        "should have 1 group text"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending an email.",
        "should have the group text corresponding to email"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_markAsRead',
        "should have 1 mark as read button"
    );
});

QUnit.test('mark as read', async function (assert) {
    assert.expect(6);

    // message that is expected to have a failure
    this.data['mail.message'].records.push({
        id: 11, // random unique id, will be used to link failure to message
        message_type: 'email', // message must be email (goal of the test)
        model: 'mail.channel', // expected value to link message to channel
        res_id: 31, // id of a random channel
        res_model_name: "Channel", // random res model name, will be asserted in the test
    });
    // failure that is expected to be used in the test
    this.data['mail.notification'].records.push({
        mail_message_id: 11, // id of the related message
        notification_status: 'exception', // necessary value to have a failure
        notification_type: 'email', // expected failure type for email message
    });
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'mail.mail_resend_cancel_action',
            "action should be the one to cancel email"
        );
        assert.strictEqual(
            payload.options.additional_context.default_model,
            'mail.channel',
            "action should have the group model as default_model"
        );
        assert.strictEqual(
            payload.options.additional_context.unread_counter,
            1,
            "action should have the group notification length as unread_counter"
        );
    });
    await this.start({ env: { bus } });
    await this.createNotificationListComponent();
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_markAsRead',
        "should have 1 mark as read button"
    );

    document.querySelector('.o_NotificationGroup_markAsRead').click();
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the cancel email dialog"
    );
});

QUnit.test('grouped notifications by document', async function (assert) {
    // If some failures linked to a document refers to a same document, a single
    // notification should group all those failures.
    assert.expect(5);

    this.data['mail.message'].records.push(
        // first message that is expected to have a failure
        {
            id: 11, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: 31, // same res_id as second message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            id: 12, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: 31, // same res_id as first message
            res_model_name: "Partner", // same related model name for consistency
        }
    );
    this.data['mail.notification'].records.push(
        // first failure that is expected to be used in the test
        {
            mail_message_id: 11, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: 12, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        }
    );
    await this.start({ hasChatWindow: true });
    await this.createNotificationListComponent();

    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in the group"
    );
    assert.containsNone(
        document.body,
        '.o_ChatWindow',
        "should have no chat window initially"
    );

    await afterNextRender(() =>
        document.querySelector('.o_NotificationGroup').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the thread in a chat window after clicking on it"
    );
});

QUnit.test('grouped notifications by document model', async function (assert) {
    // If all failures linked to a document model refers to different documents,
    // a single notification should group all failures that are linked to this
    // document model.
    assert.expect(12);

    this.data['mail.message'].records.push(
        // first message that is expected to have a failure
        {
            id: 11, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as second message (and not `mail.channel`)
            res_id: 31, // different res_id from second message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            id: 12, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // same model as first message (and not `mail.channel`)
            res_id: 32, // different res_id from first message
            res_model_name: "Partner", // same related model name for consistency
        }
    );
    this.data['mail.notification'].records.push(
        // first failure that is expected to be used in the test
        {
            mail_message_id: 11, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: 12, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        }
    );
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.name,
            "Mail Failures",
            "action should have 'Mail Failures' as name",
        );
        assert.strictEqual(
            payload.action.type,
            'ir.actions.act_window',
            "action should have the type act_window"
        );
        assert.strictEqual(
            payload.action.view_mode,
            'kanban,list,form',
            "action should have 'kanban,list,form' as view_mode"
        );
        assert.strictEqual(
            JSON.stringify(payload.action.views),
            JSON.stringify([[false, 'kanban'], [false, 'list'], [false, 'form']]),
            "action should have correct views"
        );
        assert.strictEqual(
            payload.action.target,
            'current',
            "action should have 'current' as target"
        );
        assert.strictEqual(
            payload.action.res_model,
            'res.partner',
            "action should have the group model as res_model"
        );
        assert.strictEqual(
            JSON.stringify(payload.action.domain),
            JSON.stringify([['message_has_error', '=', true]]),
            "action should have 'message_has_error' as domain"
        );
    });

    await this.start({ env: { bus } });
    await this.createNotificationListComponent();

    assert.containsOnce(
        document.body,
        '.o_NotificationGroup',
        "should have 1 notification group"
    );
    assert.containsOnce(
        document.body,
        '.o_NotificationGroup_counter',
        "should have 1 group counter"
    );
    assert.strictEqual(
        document.querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(2)",
        "should have 2 notifications in the group"
    );

    document.querySelector('.o_NotificationGroup').click();
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the related records"
    );
});

QUnit.test('different mail.channel are not grouped', async function (assert) {
    // `mail.channel` is a special case where notifications are not grouped when
    // they are linked to different channels, even though the model is the same.
    assert.expect(6);

    this.data['mail.channel'].records.push({ id: 31 }, { id: 32 });
    this.data['mail.message'].records.push(
        // first message that is expected to have a failure
        {
            id: 11, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'mail.channel', // testing a channel is the goal of the test
            res_id: 31, // different res_id from second message
            res_model_name: "Channel", // random related model name
        },
        // second message that is expected to have a failure
        {
            id: 12, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'mail.channel', // testing a channel is the goal of the test
            res_id: 32, // different res_id from first message
            res_model_name: "Channel", // same related model name for consistency
        }
    );
    this.data['mail.notification'].records.push(
        // first failure that is expected to be used in the test
        {
            mail_message_id: 11, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: 12, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        }
    );
    await this.start({
        hasChatWindow: true, // needed to assert thread.open
    });
    await this.createNotificationListComponent();
    assert.containsN(
        document.body,
        '.o_NotificationGroup',
        2,
        "should have 2 notifications group"
    );
    const groups = document.querySelectorAll('.o_NotificationGroup');
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(1)",
        "should have 1 notification in first group"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(1)",
        "should have 1 notification in second group"
    );

    await afterNextRender(() => groups[0].click());
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have opened the channel related to the first group in a chat window"
    );
});

QUnit.test('multiple grouped notifications by document model, sorted by the most recent message of each group', async function (assert) {
    assert.expect(9);

    this.data['mail.message'].records.push(
        // first message that is expected to have a failure
        {
            id: 11, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // different model from second message
            res_id: 31, // random unique id, useful to link failure to message
            res_model_name: "Partner", // random related model name
        },
        // second message that is expected to have a failure
        {
            id: 12, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.company', // different model from first message
            res_id: 32, // random unique id, useful to link failure to message
            res_model_name: "Company", // random related model name
        }
    );
    this.data['mail.notification'].records.push(
        // first failure that is expected to be used in the test
        {
            mail_message_id: 11, // id of the related first message
            notification_status: 'exception', // one possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        },
        // second failure that is expected to be used in the test
        {
            mail_message_id: 12, // id of the related second message
            notification_status: 'bounce', // other possible value to have a failure
            notification_type: 'email', // expected failure type for email message
        }
    );
    await this.start();
    await this.createNotificationListComponent();
    assert.containsN(
        document.body,
        '.o_NotificationGroup',
        2,
        "should have 2 notifications group"
    );
    const groups = document.querySelectorAll('.o_NotificationGroup');
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_name',
        "should have 1 group name in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_name').textContent,
        "Company",
        "should have first model name as group name"
    );
    assert.containsOnce(
        groups[0],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in first group"
    );
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(1)",
        "should have 1 notification in first group"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_name',
        "should have 1 group name in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_name').textContent,
        "Partner",
        "should have second model name as group name"
    );
    assert.containsOnce(
        groups[1],
        '.o_NotificationGroup_counter',
        "should have 1 group counter in second group"
    );
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_counter').textContent.trim(),
        "(1)",
        "should have 1 notification in second group"
    );
});

QUnit.test('non-failure notifications are ignored', async function (assert) {
    assert.expect(1);

    this.data['mail.message'].records.push(
        // message that is expected to have a notification
        {
            id: 11, // random unique id, will be used to link failure to message
            message_type: 'email', // message must be email (goal of the test)
            model: 'res.partner', // random model
            res_id: 31, // random unique id, useful to link failure to message
        }
    );
    this.data['mail.notification'].records.push(
        // notification that is expected to be used in the test
        {
            mail_message_id: 11, // id of the related first message
            notification_status: 'ready', // non-failure status
            notification_type: 'email', // expected notification type for email message
        },
    );
    await this.start();
    await this.createNotificationListComponent();
    assert.containsNone(
        document.body,
        '.o_NotificationGroup',
        "should have 0 notification group"
    );
});

});
});
});
