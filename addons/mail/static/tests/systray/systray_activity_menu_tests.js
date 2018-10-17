odoo.define('mail.systray.ActivityMenuTests', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('ActivityMenu', {
    beforeEach: function () {
        this.services = mailTestUtils.getMailServices();
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
                    actions: [{
                        icon: { type: "char" },
                        name: { type: "char" },
                        action_xmlid: { type: "char" },
                    }],
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
                        actions : [{
                            icon: "fa-clock-o",
                            name: "summary",
                        }],
                    },
                    {
                        name: "Note",
                        type: "activity",
                        model: "partner",
                        planned_count: 1,
                        today_count: 1,
                        overdue_count: 1,
                        total_count: 3,
                        actions: [{
                            icon: "fa-clock-o",
                            name: "summary",
                            action_xmlid: "mail.mail_activity_type_view_tree",
                        }],
                    }],
                },
            };
        }
    });

QUnit.test('activity menu widget: menu with no records', function (assert) {
    assert.expect(1);

    var activityMenu = new ActivityMenu();
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
    var activityMenu = new ActivityMenu();
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
    assert.ok(activityMenu.$el.hasClass('o_mail_systray_item'), 'should be the instance of widget');
    assert.ok(activityMenu.$('.o_mail_preview').hasClass('o_mail_preview'), "should instance of widget");
    assert.ok(activityMenu.$('.o_notification_counter').hasClass('o_notification_counter'), "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 8, "widget should have 8 notification counter");

    var context = {};
    testUtils.intercept(activityMenu, 'do_action', function (event) {
        assert.deepEqual(event.data.action.context, context, "wrong context value");
    }, true);

    // case 1: click on "late"
    context = {
        search_default_activities_overdue: 1,
    };
    activityMenu.$('.dropdown-toggle').click();
    assert.strictEqual(activityMenu.$el.hasClass("show"), true, 'ActivityMenu should be open');
    activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='overdue']").click();
    assert.strictEqual(activityMenu.$el.hasClass("show"), false, 'ActivityMenu should be closed');
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
    activityMenu.$(".o_mail_systray_dropdown_items > div[data-model_name='Issue']").click();

    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity view icon', function (assert) {
    assert.expect(8);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return $.when(self.data['mail.activity.menu'].records);
            }
            return this._super(route, args);
        },
    });
    activityMenu.appendTo($('#qunit-fixture'));
    assert.strictEqual(activityMenu.$('.o_mail_activity_action').length, 2,
                       "widget should have 2 activity view icons");

    var $first = activityMenu.$('.o_mail_activity_action').eq(0);
    var $second = activityMenu.$('.o_mail_activity_action').eq(1);
    assert.strictEqual($first.data('model_name'), "Issue",
                       "first activity action should link to 'Issue'");
    assert.ok($first.hasClass('fa-clock-o'), "should display the activity action icon");

    assert.strictEqual($second.data('model_name'), "Note",
                       "Second activity action should link to 'Note'");
    assert.ok($second.hasClass('fa-clock-o'), "should display the activity action icon");

    testUtils.intercept(activityMenu, 'do_action', function (event) {
        assert.step('do_action:' +
                    (event.data.action.name ? event.data.action.name : event.data.action));
    }, true);

    // click on the "Issue" activity icon
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_mail_activity_action[data-model_name='Issue']").click();

    // click on the "Note" activity icon
    activityMenu.$('.dropdown-toggle').click();
    activityMenu.$(".o_mail_activity_action[data-model_name='Note']").click();

    assert.verifySteps([
        'do_action:Issue',
        'do_action:mail.mail_activity_type_view_tree'
    ]);

    activityMenu.destroy();
});
});
});
