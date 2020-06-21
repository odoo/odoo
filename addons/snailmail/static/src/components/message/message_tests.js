odoo.define('snailmail/static/src/components/message/message_tests.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
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
QUnit.module('message', {}, function () {
QUnit.module('message_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createMessageComponent = async message => {
            const MessageComponent = components.Message;
            MessageComponent.env = this.env;
            this.component = new MessageComponent(null, {
                messageLocalId: message.localId,
            });
            delete MessageComponent.env;
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
            // The component must be destroyed before the widget, because the
            // widget might destroy the models before destroying the component,
            // and the Message component is relying on messaging.
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
    },
});

QUnit.test('Sent', async function (assert) {
    assert.expect(8);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            id: 11,
            notification_status: 'sent',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopover_icon'),
        'fa-check',
        "popover should have the sent icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopover').textContent.trim(),
        "Sent",
        "popover should have the sent text"
    );
});

QUnit.test('Canceled', async function (assert) {
    assert.expect(8);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            id: 11,
            notification_status: 'canceled',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopover_icon'),
        'fa-trash-o',
        "popover should have the canceled icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopover').textContent.trim(),
        "Canceled",
        "popover should have the canceled text"
    );
});

QUnit.test('Pending', async function (assert) {
    assert.expect(8);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            id: 11,
            notification_status: 'ready',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover',
        "notification popover should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailNotificationPopover_icon',
        "popover should have one icon"
    );
    assert.hasClass(
        document.querySelector('.o_SnailmailNotificationPopover_icon'),
        'fa-clock-o',
        "popover should have the pending icon"
    );
    assert.strictEqual(
        document.querySelector('.o_SnailmailNotificationPopover').textContent.trim(),
        "Awaiting Dispatch",
        "popover should have the pending text"
    );
});

QUnit.test('No Price Available', async function (assert) {
    assert.expect(10);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'cancel_letter' && args.model === 'mail.message' && args.args[0][0] === 10) {
                assert.step(args.method);
                return;
            }
            return this._super(...arguments);
        },
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            failure_type: 'sn_price',
            id: 11,
            notification_status: 'exception',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_contentPrice',
        "error dialog should have the 'no price' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailErrorDialog_cancelLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailErrorDialog',
        "dialog should be closed after click on 'Cancel letter'"
    );
    assert.verifySteps(
        ['cancel_letter'],
        "should have made a RPC call to 'cancel_letter'"
    );
});

QUnit.test('Credit Error', async function (assert) {
    assert.expect(11);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'send_letter' && args.model === 'mail.message' && args.args[0][0] === 10) {
                assert.step(args.method);
                return;
            }
            if (args.method === 'get_credits_url') {
                return 'credits_url';
            }
            return this._super(...arguments);
        },
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            failure_type: 'sn_credit',
            id: 11,
            notification_status: 'exception',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_contentCredit',
        "error dialog should have the 'credit' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_resendLetterButton',
        "dialog should have a 'Re-send letter' button"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailErrorDialog_resendLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailErrorDialog',
        "dialog should be closed after click on 'Re-send letter'"
    );
    assert.verifySteps(
        ['send_letter'],
        "should have made a RPC call to 'send_letter'"
    );
});

QUnit.test('Trial Error', async function (assert) {
    assert.expect(11);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'send_letter' && args.model === 'mail.message' && args.args[0][0] === 10) {
                assert.step(args.method);
                return;
            }
            if (args.method === 'get_credits_url') {
                return 'credits_url_trial';
            }
            return this._super(...arguments);
        },
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            failure_type: 'sn_trial',
            id: 11,
            notification_status: 'exception',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog',
        "error dialog should be open"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_contentTrial',
        "error dialog should have the 'trial' content"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_resendLetterButton',
        "dialog should have a 'Re-send letter' button"
    );
    assert.containsOnce(
        document.body,
        '.o_SnailmailErrorDialog_cancelLetterButton',
        "dialog should have a 'Cancel letter' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_SnailmailErrorDialog_resendLetterButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_SnailmailErrorDialog',
        "dialog should be closed after click on 'Re-send letter'"
    );
    assert.verifySteps(
        ['send_letter'],
        "should have made a RPC call to 'send_letter'"
    );
});

QUnit.test('Format Error', async function (assert) {
    assert.expect(8);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'snailmail.snailmail_letter_format_error_action',
            "action should be the one for format error"
        );
        assert.strictEqual(
            payload.options.additional_context.message_id,
            10,
            "action should have correct message id"
        );
    });

    await this.start({ env: { bus } });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            failure_type: 'sn_format',
            id: 11,
            notification_status: 'exception',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.verifySteps(
        ['do_action'],
        "should do an action to display the format error dialog"
    );
});

QUnit.test('Missing Required Fields', async function (assert) {
    assert.expect(9);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action,
            'snailmail.snailmail_letter_missing_required_fields_action',
            "action should be the one for missing fields"
        );
        assert.strictEqual(
            payload.options.additional_context.letter_id,
            22, // should be the same as the id returned by search
            "action should have correct letter id"
        );
    });

    await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (args.model === 'snailmail.letter' && args.method === 'search') {
                assert.step('search');
                return [22]; // should be the same as the id given to the action
            }
            return this._super(...arguments);
        },
    });
    const message = this.env.models['mail.message'].create({
        id: 10,
        message_type: 'snailmail',
        notifications: [['insert', {
            failure_type: 'sn_fields',
            id: 11,
            notification_status: 'exception',
            notification_type: 'snail',
        }]],
    });
    await this.createMessageComponent(message);

    assert.containsOnce(
        document.body,
        '.o_Message',
        "should display a message component"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIconContainer',
        "should display the notification icon container"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_notificationIcon',
        "should display the notification icon"
    );
    assert.hasClass(
        document.querySelector('.o_Message_notificationIcon'),
        'fa-paper-plane',
        "icon should represent snailmail"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Message_notificationIconContainer').click();
    });
    assert.verifySteps(
        ['search', 'do_action'],
        "the id of the letter related to the message should be returned by a search and an action should be done to display the missing fields dialog"
    );
});

});
});
});

});
