/** @odoo-module **/

import ActivityMenu from '@mail/js/systray/systray_activity_menu';
import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import testUtils from 'web.test_utils';
import { date_to_str } from 'web.time';

QUnit.module('test_mail', {}, function () {
QUnit.module('systray_activity_menu_tests.js', {
    async beforeEach() {
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv['res.partner'].create({});
        const mailTestActivityIds = pyEnv['mail.test.activity'].create([{}, {}, {}, {}]);
        pyEnv['mail.activity'].create([
            { res_id: resPartnerId1, res_model: 'res.partner' },
            { res_id: mailTestActivityIds[0], res_model: 'mail.test.activity' },
            { date_deadline: date_to_str(tomorrow), res_id: mailTestActivityIds[1], res_model: 'mail.test.activity' },
            { date_deadline: date_to_str(tomorrow), res_id: mailTestActivityIds[2],  res_model: 'mail.test.activity' },
            { date_deadline: date_to_str(yesterday), res_id: mailTestActivityIds[3], res_model: 'mail.test.activity' },
        ]);
        this.session = {
            uid: 10,
        };
    },
});

QUnit.test('activity menu widget: menu with no records', async function (assert) {
    assert.expect(1);

    const { widget } = await start({
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve([]);
            }
            return this._super(route, args);
        },
    });
    const activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.containsOnce(activityMenu, '.o_no_activity');
    widget.destroy();
});

QUnit.test('activity menu widget: activity menu with 2 models', async function (assert) {
    assert.expect(10);

    const { widget } = await start();
    var activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.hasClass(activityMenu.$el, 'o_mail_systray_item', 'should be the instance of widget');
    // the assertion below has not been replace because there are includes of ActivityMenu that modify the length.
    assert.ok(activityMenu.$('.o_mail_preview').length);
    assert.containsOnce(activityMenu.$el, '.o_notification_counter', "widget should have notification counter");
    assert.strictEqual(parseInt(activityMenu.el.innerText), 5, "widget should have 5 notification counter");

    var context = {};
    testUtils.mock.intercept(activityMenu, 'do_action', function (event) {
        assert.deepEqual(event.data.action.context, context, "wrong context value");
    }, true);

    // case 1: click on "late"
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.hasClass(activityMenu.$el, 'show', 'ActivityMenu should be open');
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='mail.test.activity'][data-filter='overdue']"));
    assert.doesNotHaveClass(activityMenu.$el, 'show', 'ActivityMenu should be closed');
    // case 2: click on "today"
    context = {
        force_search_count: 1,
        search_default_activities_today: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='mail.test.activity'][data-filter='today']"));
    // case 3: click on "future"
    context = {
        force_search_count: 1,
        search_default_activities_upcoming_all: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_activity_filter_button[data-model_name='mail.test.activity'][data-filter='upcoming_all']"));
    // case 4: click anywere else
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_mail_systray_dropdown_items > div[data-model_name='mail.test.activity']"));

    widget.destroy();
});

QUnit.test('activity menu widget: activity view icon', async function (assert) {
    assert.expect(14);

    const { widget } = await start({
        session: this.session,
    });
    var activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();
    assert.containsN(activityMenu, '.o_mail_activity_action', 2,
                       "widget should have 2 activity view icons");

    var $first = activityMenu.$('.o_mail_activity_action').eq(0);
    var $second = activityMenu.$('.o_mail_activity_action').eq(1);
    assert.strictEqual($first.data('model_name'), "res.partner",
                       "first activity action should link to 'res.partner'");
    assert.hasClass($first, 'fa-clock-o', "should display the activity action icon");

    assert.strictEqual($second.data('model_name'), "mail.test.activity",
                       "Second activity action should link to 'mail.test.activity'");
    assert.hasClass($second, 'fa-clock-o', "should display the activity action icon");

    testUtils.mock.intercept(activityMenu, 'do_action', function (ev) {
        if (ev.data.action.name) {
            assert.ok(ev.data.action.domain, "should define a domain on the action");
            assert.deepEqual(ev.data.action.domain, [["activity_ids.user_id", "=", 10]],
                "should set domain to user's activity only");
            assert.step('do_action:' + ev.data.action.name);
        } else {
            assert.step('do_action:' + ev.data.action);
        }
    }, true);

    // click on the "mail.test.activity" activity icon
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.hasClass(activityMenu.$('.dropdown-menu'), 'show',
        "dropdown should be expanded");

    await testUtils.dom.click(activityMenu.$(".o_mail_activity_action[data-model_name='mail.test.activity']"));
    assert.doesNotHaveClass(activityMenu.$('.dropdown-menu'), 'show',
        "dropdown should be collapsed");

    // click on the "res.partner" activity icon
    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    await testUtils.dom.click(activityMenu.$(".o_mail_activity_action[data-model_name='res.partner']"));

    assert.verifySteps([
        'do_action:mail.test.activity',
        'do_action:res.partner'
    ]);

    widget.destroy();
});

QUnit.test('activity menu widget: close on messaging menu click', async function (assert) {
    assert.expect(2);

    const { click, createMessagingMenuComponent, widget } = await start();
    await createMessagingMenuComponent();
    const activityMenu = new ActivityMenu(widget);
    await activityMenu.appendTo($('#qunit-fixture'));
    await testUtils.nextTick();

    await testUtils.dom.click(activityMenu.$('.dropdown-toggle'));
    assert.hasClass(
        activityMenu.el.querySelector('.o_mail_systray_dropdown'),
        'show',
        "activity menu should be shown after click on itself"
    );

    await click(`.o_MessagingMenu_toggler`);
    assert.doesNotHaveClass(
        activityMenu.el.querySelector('.o_mail_systray_dropdown'),
        'show',
        "activity menu should be hidden after click on messaging menu"
    );

    widget.destroy();
});

});
