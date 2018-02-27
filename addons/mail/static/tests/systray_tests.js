odoo.define('mail.systray_tests', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var systray = require('mail.systray');
var mailTestUtils = require('mail.testUtils');

var Bus = require('web.Bus');
var testUtils = require('web.test_utils');

var createBusService = mailTestUtils.createBusService;

QUnit.module('mail', {}, function () {

QUnit.module('ActivityMenu', {
    beforeEach: function () {
        this.services = [ChatManager, createBusService()];
        this.data = {
            'mail.activity.menu': {
                fields: {
                    name: { type: "char" },
                    model: { type: "char" },
                    type: { type: "char" },
                    planned_count: { type: "integer"},
                    today_count: { type: "integer"},
                    overdue_count: { type: "integer"},
                    total_count: { type: "integer"},
                },
                records: [{
                        name: "Contact",
                        model: "res.partner",
                        type: "activity",
                        planned_count: 0,
                        today_count: 1,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Task",
                        type: "activity",
                        model: "project.task",
                        planned_count: 1,
                        today_count: 0,
                        overdue_count: 0,
                        total_count: 1,
                    },
                    {
                        name: "Issue",
                        type: "activity",
                        model: "project.issue",
                        planned_count: 1,
                        today_count: 1,
                        overdue_count: 1,
                        total_count: 3,
                    }],
                },
            };
        }
    });

QUnit.test('activity menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var activityMenu = new systray.ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'systray_get_activities') {
                    return $.when([]);
                }
                return this._super(route, args);
            },
        });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$('.o_no_activity').hasClass('o_no_activity'), "should not have instance of widget");
    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity menu with 3 records', function (assert) {
    assert.expect(10);
    var self = this;
    var activityMenu = new systray.ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return $.when(self.data['mail.activity.menu']['records']);
            }
            return this._super(route, args);
        },
    });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.ok(activityMenu.$el.hasClass('o_mail_navbar_item'), 'should be the instance of widget');
    assert.ok(activityMenu.$('.o_mail_channel_preview').hasClass('o_mail_channel_preview'), "should instance of widget");
    assert.ok(activityMenu.$('.o_notification_counter').hasClass('o_notification_counter'), "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 5, "widget should have 5 notification counter");

    var context = {};
    testUtils.intercept(activityMenu, 'do_action', function(event) {
        assert.deepEqual(event.data.action.context, context, "wrong context value");
    }, true);

    // case 1: click on "late"
    context = {
        search_default_activities_overdue: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), true, 'ActivityMenu should be open');
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='overdue']").click();
    assert.strictEqual(activityMenu.$el.hasClass("open"), false, 'ActivityMenu should be closed');
    // case 2: click on "today"
    context = {
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='today']").click();
    // case 3: click on "future"
    context = {
        search_default_activities_upcoming_all: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='upcoming_all']").click();
    // case 4: click anywere else
    context = {
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_mail_navbar_dropdown_channels > div[data-model_name='Issue']").click();

    activityMenu.destroy();
});
});

QUnit.module('MessagingMenu', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.data = {
            'mail.channel': {
                fields: {
                    name: {
                        string: "Name",
                        type: "char",
                        required: true,
                    },
                    channel_type: {
                        string: "Channel Type",
                        type: "selection",
                    },
                    channel_message_ids: {
                        string: "Messages",
                        type: "many2many",
                        relation: 'mail.message'
                    },
                },
                records: [{
                    id: 1,
                    name: "general",
                    channel_type: "channel",
                    channel_message_ids: [1],
                }],
            },
            'mail.message': {
                fields: {
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    author_id: {
                        string: "Author",
                        relation: 'res.partner',
                    },
                    channel_ids: {
                        string: "Channels",
                        type: 'many2many',
                        relation: 'mail.channel',
                    },
                    starred: {
                        string: "Starred",
                        type: 'boolean',
                    },
                    needaction: {
                      string: "Need Action",
                      type: 'boolean',
                    },
                    starred_partner_ids: {
                      string: "partner ids",
                      type: 'integer',
                    }
                },
                records: [{
                    id: 1,
                    author_id: ['1', 'Me'],
                    body: '<p>test</p>',
                    channel_ids: [1],
                }],
            },
            initMessaging: {
                channel_slots: {
                    channel_channel: [{
                        id: 1,
                        channel_type: "channel",
                        name: "general",
                    }],
                },
            },
        };
        this.services = [ChatManager, createBusService()];
    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

QUnit.test('messaging menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var messagingMenu = new systray.MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'message_fetch') {
                    return $.when([]);
                }
                return this._super.apply(this, arguments);
            }
        });
    messagingMenu.appendTo($('#qunit-fixture'));
    messagingMenu.$('.dropdown-toggle').click();
    assert.ok(messagingMenu.$('.o_no_activity').hasClass('o_no_activity'), "should not have instance of widget");
    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: messaging menu with 1 record', function (assert) {
    assert.expect(3);
    var messagingMenu = new systray.MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: this.services,
        data: this.data,
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    messagingMenu.$('.dropdown-toggle').click();

    assert.strictEqual(messagingMenu.$('.o_mail_channel_preview').length, 1,
        "should display a channel preview");
    assert.strictEqual(messagingMenu.$('.o_channel_name').text().trim(), "general",
        "should display correct name of channel in channel preview");

    // remove any space-character inside text
    var lastMessagePreviewText =
        messagingMenu.$('.o_last_message_preview').text().replace(/\s/g, "");
    assert.strictEqual(lastMessagePreviewText,
        "Me:test",
        "should display correct last message preview in channel preview");

    messagingMenu.destroy();
});

QUnit.test('messaging menu widget: no crash when clicking on inbox notification not associated to a document', function (assert) {
    assert.expect(3);

    var bus = new Bus();

    var messagingMenu = new systray.MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: [ChatManager, createBusService(bus)],
        data: this.data,
        session: {
            partner_id: 1,
        },
        intercepts: {
            /**
             * Simulate action 'mail.mail_channel_action_client_chat'
             * successfully performed.
             *
             * @param {OdooEvent} ev
             * @param {function} ev.data.on_success called when success action performed
             */
            do_action: function (ev) {
                ev.data.on_success();
            },
        },
    });
    messagingMenu.appendTo($('#qunit-fixture'));

    // Simulate received needaction message without associated document,
    // so that we have a message in inbox without a model and a resID
    var message = {
        id: 2,
        author_id: [1, "Me"],
        body: '<p>test</p>',
        channel_ids: [],
        needaction_partner_ids: [1],
    };
    var notifications = [
        [['myDB', 'ir.needaction'], message]
    ];
    bus.trigger('notification', notifications);

    // Open messaging menu
    messagingMenu.$('.dropdown-toggle').click();

    var $firstChannelPreview =
        messagingMenu.$('.o_mail_channel_preview').first();

    assert.strictEqual($firstChannelPreview.length, 1,
        "should have at least one channel preview");
    assert.strictEqual($firstChannelPreview.data('channel_id'),
        'channel_inbox',
        "should be a preview from channel inbox");
    try {
        $firstChannelPreview.click();
        assert.ok(true, "should not have crashed when clicking on needaction preview message");
    } finally {
        messagingMenu.destroy();
    }
});

QUnit.test("messaging menu widget: messaging menu with 1 message", function ( assert ) {
    assert.expect(5);

    var records = [{
        "channel_ids": ['channel_inbox'],
        "res_id": 126,
        'is_needaction': true,
        "module_icon": "/crm/static/description/icon.png",
        "date": "2018-04-05 06:37:26",
        "subject": "Re: Interest in your Graphic Design Project",
        "model": "crm.lead",
        "body": "<span>Testing Messaging</span>"
    }];

    var messagingMenu = new systray.MessagingMenu();
    testUtils.addMockEnvironment(messagingMenu, {
        services: [ChatManager, createBusService()],
        mockRPC: function (route, args) {
            if (args.method === "message_fetch") {
                return $.when(records);
            }
            return this._super(route, args);
        },
    });

    messagingMenu.appendTo($('#qunit-fixture'));
    messagingMenu.$('.dropdown-toggle').click();
    assert.ok(messagingMenu.$el.hasClass('o_mail_navbar_item'),
        'should be the instance of widget');
    assert.strictEqual(messagingMenu.$el.hasClass("open"), true,
        'MessagingMenu should be open');
    assert.strictEqual(messagingMenu.$('.o_channel_unread').length, 1,
        "should have one unread message for channel");
    assert.strictEqual(messagingMenu.$('.o_mail_channel_mark_read').length, 1,
        "should have mark as read icon");
    testUtils.intercept(messagingMenu, 'call_service', function (event) {
        if (event.data.method === 'markAllAsRead') {
            assert.deepEqual(
                event.data.args[1],
                [["model", "=" , "crm.lead"], ["res_id", "=" ,126]],
                "The message has been read"
            );
        }
    });
    messagingMenu.$(".o_mail_channel_mark_read").click();
    messagingMenu.destroy();
});

});