/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import session from 'web.session';
import { date_to_str } from 'web.time';
import { patchWithCleanup } from '@web/../tests/helpers/utils';


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
            { date_deadline: date_to_str(tomorrow), res_id: mailTestActivityIds[2], res_model: 'mail.test.activity' },
            { date_deadline: date_to_str(yesterday), res_id: mailTestActivityIds[3], res_model: 'mail.test.activity' },
        ]);
    },
});

QUnit.test('activity menu widget: menu with no records', async function (assert) {
    assert.expect(1);

    const { click } = await start({
        mockRPC: function (route, args) {
            if (args.method === 'systray_get_activities') {
                return Promise.resolve([]);
            }
        },
    });
    await click('.o_ActivityMenuView_dropdownToggle');
    assert.containsOnce(document.body, '.o_ActivityMenuView_noActivity');
});

QUnit.test('activity menu widget: activity menu with 2 models', async function (assert) {
    assert.expect(10);

    const { click, env } = await start();

    await click('.o_ActivityMenuView_dropdownToggle');
    assert.containsOnce(document.body, '.o_ActivityMenuView', 'should contain an instance of widget');
    assert.ok(document.querySelectorAll('.o_ActivityMenuView_activityGroup').length);
    assert.containsOnce(document.body, '.o_ActivityMenuView_counter', "widget should have notification counter");
    assert.strictEqual(parseInt(document.querySelector('.o_ActivityMenuView_counter').innerText), 5, "widget should have 5 notification counter");

    var context = {};
    patchWithCleanup(env.services.action, {
        doAction(action) {
            assert.deepEqual(action.context, context, "wrong context value");
        },
    });

    // case 1: click on "late"
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
    };
    assert.containsOnce(document.body, '.o_ActivityMenuView_dropdownMenu.show', 'ActivityMenu should be open');
    await click('.o_ActivityMenuView_activityGroupFilterButton[data-model_name="mail.test.activity"][data-filter="overdue"]');
    assert.containsNone(document.body, '.show', 'ActivityMenu should be closed');
    // case 2: click on "today"
    context = {
        force_search_count: 1,
        search_default_activities_today: 1,
    };
    await click('.dropdown-toggle[title="Activities"]');
    await click('.o_ActivityMenuView_activityGroupFilterButton[data-model_name="mail.test.activity"][data-filter="today"]');
    // case 3: click on "future"
    context = {
        force_search_count: 1,
        search_default_activities_upcoming_all: 1,
    };
    await click('.dropdown-toggle[title="Activities"]');
    await click('.o_ActivityMenuView_activityGroupFilterButton[data-model_name="mail.test.activity"][data-filter="upcoming_all"]');
    // case 4: click anywere else
    context = {
        force_search_count: 1,
        search_default_activities_overdue: 1,
        search_default_activities_today: 1,
    };
    await click('.dropdown-toggle[title="Activities"]');
    await click('.o_ActivityMenuView_activityGroups > div[data-model_name="mail.test.activity"]');
});

QUnit.test('activity menu widget: activity view icon', async function (assert) {
    assert.expect(14);

    patchWithCleanup(session, { uid: 10 });
    const { click, env } = await start();

    await click('.o_ActivityMenuView_dropdownToggle');
    assert.containsN(document.body, '.o_ActivityMenuView_activityGroupActionButton', 2,
                       "widget should have 2 activity view icons");

    var first = document.querySelector('.o_ActivityMenuView_activityGroupActionButton');
    var second = document.querySelectorAll('.o_ActivityMenuView_activityGroupActionButton')[1];
    assert.strictEqual(first.getAttribute('data-model_name'), "res.partner",
                       "first activity action should link to 'res.partner'");
    assert.hasClass(first, 'fa-clock-o', "should display the activity action icon");

    assert.strictEqual(second.getAttribute('data-model_name'), "mail.test.activity",
                       "Second activity action should link to 'mail.test.activity'");
    assert.hasClass(second, 'fa-clock-o', "should display the activity action icon");

    patchWithCleanup(env.services.action, {
        doAction(action) {
            if (action.name) {
                assert.ok(action.domain, "should define a domain on the action");
                assert.deepEqual(action.domain, [["activity_ids.user_id", "=", 10]],
                    "should set domain to user's activity only");
                assert.step('do_action:' + action.name);
            } else {
                assert.step('do_action:' + action);
            }
        },
    });

    assert.hasClass(document.querySelector('.o-dropdown-menu'), 'show',
        "dropdown should be expanded");

    await click('.o_ActivityMenuView_activityGroupActionButton[data-model_name="mail.test.activity"]');
    assert.containsNone(document.body, '.o-dropdown-menu',
        "dropdown should be collapsed");

    // click on the "res.partner" activity icon
    await click('.dropdown-toggle[title="Activities"]');
    await click('.o_ActivityMenuView_activityGroupActionButton[data-model_name="res.partner"]');

    assert.verifySteps([
        'do_action:mail.test.activity',
        'do_action:res.partner'
    ]);
});

QUnit.test('activity menu widget: close on messaging menu click', async function (assert) {
    assert.expect(2);

    const { click } = await start();

    await click('.dropdown-toggle[title="Activities"]');
    assert.hasClass(
        document.querySelector('.o_ActivityMenuView_dropdownMenu'),
        'show',
        "activity menu should be shown after click on itself"
    );

    await click(`.o_MessagingMenu_toggler`);
    assert.containsNone(
        document.body,
        '.o_ActivityMenuView_dropdownMenu',
        "activity menu should be hidden after click on messaging menu"
    );
});

});
