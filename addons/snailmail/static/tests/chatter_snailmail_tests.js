odoo.define('snailmail.chatter_snailmail_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');
var ThreadWidget = require('mail.widget.Thread');

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

var getArch = function () {
    return '<form string="Invoice">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                '</div>' +
            '</form>';
};

QUnit.module('snailmail', {}, function () {
QUnit.module('Chatter', {
    before: function () {
        this.services = mailTestUtils.getMailServices();
        this.data = {
            'account.move': {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    message_ids: {
                        string: "messages",
                        type: "one2many",
                        relation: 'mail.message',
                        relation_field: "res_id",
                    },
                    message_attachment_count: {
                        string: 'Attachment count',
                        type: 'integer',
                    },
                },
                records: [{
                    id: 1,
                    display_name: "Invoice 1",
                    foo: "HELLO",
                    message_ids: [11],
                    message_attachment_count: 0,
                }]
            },
            'mail.message': {
                fields: {
                    author_id: {
                        string: "Author",
                        relation: 'res.partner',
                    },
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    date: {
                        string: "Date",
                        type: 'datetime',
                    },
                    model: {
                        string: "Related Document Model",
                        type: 'char',
                    },
                    res_id: {
                        string: "Related Document ID",
                        type: 'integer',
                    },
                    message_type: {
                        string: "Type",
                        type: 'selection',
                    },
                    notifications: {
                        string: "Notifications",
                        type: 'array',
                    }
                },
                records: [{
                    id: 11,
                    author_id: ["1", "John Doe"],
                    body: 'Message Body',
                    date: "2018-12-11 12:34:00",
                    model: 'account.move',
                    res_id: 1,
                    message_type: 'snailmail',
                }],
            },
            "ir.attachment": {
                fields: {},
                records: [],
            }
        };
    },
    afterEach: function () {
        $('.popover').remove();
        $('.modal').remove();
    }
});

QUnit.test('Sent', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'sent',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    await testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-check').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Sent")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    assert.containsNone($('.modal'), "No modal should open on click");

    form.destroy();
});

QUnit.test('Canceled', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'canceled',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-trash-o').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Canceled")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    assert.containsNone($('.modal'), "No modal should open on click");

    form.destroy();
});

QUnit.test('Pending', async function (assert) {
    assert.expect(6);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'ready',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-clock-o').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Awaiting Dispatch")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    assert.containsNone($('.modal'), "No modal should open on click");

    form.destroy();
});

QUnit.test('No Price Available', async function (assert) {
    assert.expect(10);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'exception',
        'failure_type': 'sn_price',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
        mockRPC: function (route, args) {
            if (args.method === 'cancel_letter' && args.model === 'mail.message' && args.args[0][0] === 11) {
                assert.step(args.method);
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-exclamation').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Error")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    var $modal = $('.modal');
    assert.ok($modal.length, "A modal should open on click");

    assert.containsOnce($modal, 'button:contains("Cancel letter")',
        "Modal should have a 'Cancel letter' button");
    var $cancelButton = $('.modal').find('button:contains("Cancel letter")');
    await testUtils.dom.click($cancelButton);
    assert.notOk($('.modal').length,
        "The modal should be closed after click on 'Cancel letter'");

    assert.verifySteps(['cancel_letter'],
        "Should have made a RPC call to 'cancel_letter'");

    form.destroy();
});

QUnit.test('Format Error', async function (assert) {
    assert.expect(7);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'exception',
        'failure_type': 'sn_format',
    }];

    testUtils.mock.patch(ThreadWidget, {
        do_action: function (action, options) {
            assert.step("do_action");
        },
    });

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
        mockRPC: function (route, args) {
            if (args.method === 'cancel_letter' && args.model === 'mail.message' && args.args[0][0] === 11) {
                assert.step(args.method);
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-exclamation').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Error")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    assert.verifySteps(['do_action'], "'do_action' should have been called");

    form.destroy();
    testUtils.mock.unpatch(ThreadWidget);
});

QUnit.test('Credit Error', async function (assert) {
    assert.expect(13);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'exception',
        'failure_type': 'sn_credit',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
        mockRPC: function (route, args) {
            if (args.model === 'mail.message') {
                if ((args.method === 'cancel_letter' && args.args[0][0] === 11) || args.method === 'send_letter') {
                    assert.step(args.method);
                    return Promise.resolve();
                }
            }
            if (args.method === 'get_credits_url' && args.model === 'iap.account') {
                return Promise.resolve('credits_url');
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-exclamation').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Error")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    var $modal = $('.modal');
    assert.ok($modal.length, "A modal should open on click");

    assert.containsOnce($modal, 'button:contains("Re-send letter")',
        "Modal should have a 'Re-send letter' button");
    var $resendButton = $('.modal').find('button:contains("Re-send letter")');
    await testUtils.dom.click($resendButton);
    assert.notOk($('.modal').length,
        "The modal should be closed after click on 'Re-send letter'");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));

    assert.containsOnce($modal, 'button:contains("Cancel letter")',
        "Modal should have a 'Cancel letter' button");
    var $cancelButton = $('.modal').find('button:contains("Cancel letter")');
    await testUtils.dom.click($cancelButton);
    assert.containsNone($('.modal'),
        "The modal should be closed after click on 'Cancel letter'");

    assert.verifySteps(['send_letter', 'cancel_letter'],
        "Should have made RPC calls to 'send_letter' and 'cancel_letter'");

    form.destroy();
});

QUnit.test('Trial Error', async function (assert) {
    assert.expect(13);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'exception',
        'failure_type': 'sn_trial',
    }];

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
        mockRPC: function (route, args) {
            if (args.model === 'mail.message') {
                if ((args.method === 'cancel_letter' && args.args[0][0] === 11) || args.method === 'send_letter') {
                    assert.step(args.method);
                    return Promise.resolve();
                }
            }
            if (args.method === 'get_credits_url' && args.model === 'iap.account') {
                return Promise.resolve('credits_url');
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-exclamation').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Error")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    var $modal = $('.modal');
    assert.ok($modal.length, "A modal should open on click");

    assert.containsOnce($modal, 'button:contains("Re-send letter")',
        "Modal should have a 'Re-send letter' button");
    var $resendButton = $('.modal').find('button:contains("Re-send letter")');
    await testUtils.dom.click($resendButton);
    assert.containsNone($('.modal'),
        "The modal should be closed after click on 'Re-send letter'");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));

    $modal = $('.modal');
    assert.containsOnce($modal, 'button:contains("Cancel letter")',
        "Modal should have a 'Cancel letter' button");
    var $cancelButton = $modal.find('button:contains("Cancel letter")');
    await testUtils.dom.click($cancelButton);
    assert.containsNone($('.modal'),
        "The modal should be closed after click on 'Cancel letter'");

    assert.verifySteps(['send_letter', 'cancel_letter'],
        "Should have made RPC calls to 'send_letter' and 'cancel_letter'");

    form.destroy();
});

QUnit.test('Missing Required Fields', async function (assert) {
    assert.expect(7);

    this.data['mail.message'].records[0].notifications = [{
        'notification_type': 'snail',
        'notification_status': 'exception',
        'failure_type': 'sn_fields',
    }];

    testUtils.mock.patch(ThreadWidget, {
        do_action: function (action, options) {
            assert.step("do_action");
        },
    });

    var form = await createView({
        View: FormView,
        model: 'account.move',
        res_id: 1,
        data: this.data,
        services: this.services,
        arch: getArch(),
        mockRPC: function (route, args) {
            if (args.model === 'snailmail.letter' && args.method === 'search') {
                return Promise.resolve([2]);
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.containsOnce(form, '.o_thread_message_notification',
        "Snailmail icon should appear on message");
    assert.containsNone(form, '.o_thread_tooltip_icon',
        "No tooltip should be present");

    testUtils.dom.triggerMouseEvent(form.$('.o_thread_message_notification'), 'mouseover');
    assert.ok($('.o_thread_tooltip_icon:visible').length,
        "Tooltip should appear when hovering the Snailmail Icon");
    assert.ok($('.o_thread_tooltip_icon .fa-exclamation').length,
        "Tooltip should show correct icon");
    assert.ok($('.o_thread_tooltip_icon:contains("Error")').length,
        "Tooltip should show correct text");

    await testUtils.dom.click(form.$('.o_thread_message_notification'));
    assert.verifySteps(['do_action'], "'do_action' should have been called");

    form.destroy();
    testUtils.mock.unpatch(ThreadWidget);
});

});

});
