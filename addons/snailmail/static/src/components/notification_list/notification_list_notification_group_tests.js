odoo.define('snailmail/static/src/components/notification_list/notification_list_notification_group_tests.js', function (require) {
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

const Bus = require('web.Bus');

QUnit.module('snailmail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('notification_list', {}, function () {
QUnit.module('notification_list_notification_group_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        /**
         * @param {Object} param0
         * @param {string} [param0.filter='all']
         */
        this.createNotificationListComponent = async ({ filter = 'all' } = {}) => {
            const NotificationListComponent = components.NotificationList;
            NotificationListComponent.env = this.env;
            this.component = new NotificationListComponent(null, { filter });
            await afterNextRender(() => this.component.mount(this.widget.el));
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

QUnit.test('mark as read', async function (assert) {
    assert.expect(6);

    this.data.initMessaging.mail_failures = [{
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 11,
        message_type: 'snailmail',
        model: 'mail.channel',
        notifications: [{
            failure_type: 'sn_credit',
            id: 21,
            notification_status: 'exception',
            notification_type: 'snail',
            partner_id: [41, "Someone"],
        }],
        res_id: 31,
        res_model_name: "Channel",
    }];
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'snailmail.snailmail_letter_cancel_action',
            "action should be the one to cancel letter"
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
        "should do an action to display the cancel letter dialog"
    );
});

QUnit.test('notifications grouped by notification_type', async function (assert) {
    assert.expect(11);

    this.data.initMessaging.mail_failures = [{
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 11,
        message_type: 'email', // key element of this test: different type
        model: 'res.partner', // key element of this test: same model (and not `mail.channel``)
        notifications: [{
            failure_type: 'SMTP',
            id: 21,
            notification_status: 'exception',
            notification_type: 'email', // key element of this test: different type
            partner_id: [41, "Someone"],
        }],
        res_id: 31, // key element of this test: same res_id
        res_model_name: "Partner",
    }, {
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 12,
        message_type: 'snailmail', // key element of this test: different type
        model: 'res.partner', // key element of this test: same model (and not `mail.channel``)
        notifications: [{
            failure_type: 'sn_credit',
            id: 22,
            notification_status: 'exception',
            notification_type: 'snail', // key element of this test: different type
            partner_id: [42, "Someone else"],
        }],
        res_id: 31, // key element of this test: same res_id
        res_model_name: "Partner",
    }];

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
        "Partner",
        "should have model name as group name"
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
    assert.strictEqual(
        groups[0].querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending an email.",
        "should have the group text corresponding to email"
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
    assert.strictEqual(
        groups[1].querySelector('.o_NotificationGroup_inlineText').textContent.trim(),
        "An error occurred when sending a letter with Snailmail.",
        "should have the group text corresponding to snailmail"
    );
});

QUnit.test('grouped notifications by document model', async function (assert) {
    // If all failures linked to a document model refers to different documents,
    // a single notification should group all failures that are linked to this
    // document model.
    assert.expect(12);

    this.data.initMessaging.mail_failures = [{
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 11,
        message_type: 'snailmail',
        model: 'res.partner', // key element of this test: same model
        notifications: [{
            failure_type: 'sn_credit',
            id: 21,
            notification_status: 'exception',
            notification_type: 'snail',
            partner_id: [41, "Someone"],
        }],
        res_id: 31, // key element of this test: a different res_id
        res_model_name: "Partner",
    }, {
        date: moment.utc().format("YYYY-MM-DD HH:mm:ss"),
        id: 12,
        message_type: 'snailmail',
        model: 'res.partner', // key element of this test: same model
        notifications: [{
            failure_type: 'sn_credit',
            id: 22,
            notification_status: 'exception',
            notification_type: 'snail',
            partner_id: [42, "Someone else"],
        }],
        res_id: 32, // key element of this test: a different res_id
        res_model_name: "Partner",
    }];
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.name,
            "Snailmail Failures",
            "action should have 'Snailmail Failures' as name",
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
            JSON.stringify([['message_ids.snailmail_error', '=', true]]),
            "action should have 'message_has_sms_error' as domain"
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

});
});
});

});
