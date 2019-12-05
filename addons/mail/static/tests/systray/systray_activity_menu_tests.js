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
            this.session = {
                uid: 10,
            };
        }
    });

QUnit.test('activity menu widget: menu with no records', async function (assert) {
    assert.expect(1);

    var activityMenu = new ActivityMenu();
    testUtils.mock.addMockEnvironment(activityMenu, {
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'systray_get_activities') {
                    return Promise.resolve([]);
                }
                return this._super(route, args);
            },
        });
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.containsOnce(activityMenu, '.o_no_activity');
    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity menu with 3 records', async function (assert) {
    assert.expect(10);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.mock.addMockEnvironment(activityMenu, {
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve(self.data['mail.activity.menu']['records']);
            }
            return this._super(route, args);
        },
    });
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.hasClass(activityMenu.$el, 'o_mail_systray_item', 'should be the instance of widget');
    // the assertion below has not been replace because there are includes of ActivityMenu that modify the length.
    assert.ok(activityMenu.$('.o_mail_preview').length);
    assert.containsOnce(activityMenu.$el, '.o_notification_counter', "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 8, "widget should have 8 notification counter");

    var context = {};
    testUtils.mock.intercept(activityMenu, 'do_action', function (event) {
        assert.deepEqual(event.data.action.context, context, "wrong context value");
    }, true);

    // case 1: click on "late"
    context = {
        search_default_activities_overdue: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.hasClass(activityMenu.$el, 'show', 'ActivityMenu should be open');
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='overdue']"));
    assert.doesNotHaveClass(activityMenu.$el, 'show', 'ActivityMenu should be closed');
    // case 2: click on "today"
    context = {
        search_default_activities_today: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='today']"));
    // case 3: click on "future"
    context = {
        search_default_activities_upcoming_all: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='Issue'][data-filter='upcoming_all']"));
    // case 4: click anywere else
    context = {
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_mail_systray_dropdown_items > div[data-model_name='Issue']"));

    activityMenu.destroy();
});

QUnit.test('activity menu widget: activity view icon', async function (assert) {
    assert.expect(12);
    var self = this;
    var activityMenu = new ActivityMenu();
    testUtils.mock.addMockEnvironment(activityMenu, {
        services: this.services,
        session: this.session,
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve(self.data['mail.activity.menu'].records);
            }
            return this._super(route, args);
        },
    });
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.containsN(activityMenu, '.o_mail_activity_action', 2,
                       "widget should have 2 activity view icons");

    var $first = activityMenu.$('.o_mail_activity_action').eq(0);
    var $second = activityMenu.$('.o_mail_activity_action').eq(1);
    assert.strictEqual($first.data('model_name'), "Issue",
                       "first activity action should link to 'Issue'");
    assert.hasClass($first,'fa-clock-o', "should display the activity action icon");

    assert.strictEqual($second.data('model_name'), "Note",
                       "Second activity action should link to 'Note'");
    assert.hasClass($second,'fa-clock-o', "should display the activity action icon");

    testUtils.mock.intercept(activityMenu, 'do_action', function (ev) {
        if (ev.data.action.name) {
            assert.ok(ev.data.action.domain, "should define a domain on the action");
            assert.deepEqual(ev.data.action.domain, [["activity_ids.user_id", "=", 10]],
                "should set domain to user's activity only")
            assert.step('do_action:' + ev.data.action.name);
        } else {
            assert.step('do_action:' + ev.data.action);
        }
    }, true);

    // click on the "Issue" activity icon
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.hasClass(activityMenu.$('.dropdown-menu'), 'show',
        "dropdown should be expanded");

    await testUtils.dom.click(activityMenu.$(".o_mail_activity_action[data-model_name='Issue']"));
    assert.doesNotHaveClass(activityMenu.$('.dropdown-menu'), 'show',
        "dropdown should be collapsed");

    // click on the "Note" activity icon
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_mail_activity_action[data-model_name='Note']"));

    assert.verifySteps([
        'do_action:Issue',
        'do_action:mail.mail_activity_type_view_tree'
    ]);

    activityMenu.destroy();
});
});
});
