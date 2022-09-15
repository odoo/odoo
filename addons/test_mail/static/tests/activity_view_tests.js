/** @odoo-module **/

import ActivityRenderer from '@mail/js/views/activity/activity_renderer';
import { start, startServer } from '@mail/../tests/helpers/test_utils';

import testUtils from 'web.test_utils';

import { legacyExtraNextTick, patchWithCleanup, click } from "@web/../tests/helpers/utils";
import { doAction } from "@web/../tests/webclient/helpers";
import { session } from '@web/session';

let serverData;
let pyEnv;

QUnit.module('test_mail', {}, function () {
QUnit.module('activity view', {
    async beforeEach() {
        pyEnv = await startServer();
        const mailTemplateIds = pyEnv['mail.template'].create([{ name: "Template1" }, { name: "Template2" }]);
        // reset incompatible setup
        pyEnv['mail.activity.type'].unlink(pyEnv['mail.activity.type'].search([]));
        const mailActivityTypeIds = pyEnv['mail.activity.type'].create([
            { name: "Email", mail_template_ids: mailTemplateIds },
            { name: "Call" },
            { name: "Call for Demo" },
            { name: "To Do" },
        ]);
        const resUsersId1 = pyEnv['res.users'].create({ display_name: 'first user' });
        const mailActivityIds = pyEnv['mail.activity'].create([
            {
                display_name: "An activity",
                date_deadline: moment().add(3, "days").format("YYYY-MM-DD"), // now
                can_write: true,
                state: "planned",
                activity_type_id: mailActivityTypeIds[0],
                mail_template_ids: mailTemplateIds,
                user_id: resUsersId1,
            },
            {
                display_name: "An activity",
                date_deadline: moment().format("YYYY-MM-DD"), // now
                can_write: true,
                state: "today",
                activity_type_id: mailActivityTypeIds[0],
                mail_template_ids: mailTemplateIds,
                user_id: resUsersId1,
            },
            {
                res_model: 'mail.test.activity',
                display_name: "An activity",
                date_deadline: moment().subtract(2, "days").format("YYYY-MM-DD"), // now
                can_write: true,
                state: "overdue",
                activity_type_id: mailActivityTypeIds[1],
                user_id: resUsersId1,
            },
        ]);
        pyEnv['mail.test.activity'].create([
            { name: 'Meeting Room Furnitures', activity_ids: [mailActivityIds[0]] },
            { name: 'Office planning', activity_ids: [mailActivityIds[1], mailActivityIds[2]] },
        ]);
        serverData = {
            views: {
                'mail.test.activity,false,activity':
                    '<activity string="MailTestActivity">' +
                            '<templates>' +
                                '<div t-name="activity-box">' +
                                    '<field name="name"/>' +
                                '</div>' +
                            '</templates>' +
                    '</activity>',
            },
        };
    }
});

var activityDateFormat = function (date) {
    return date.toLocaleDateString(moment().locale(), { day: 'numeric', month: 'short' });
};

QUnit.test('activity view: simple activity rendering', async function (assert) {
    assert.expect(14);
    const mailTestActivityIds = pyEnv['mail.test.activity'].search([]);
    const mailActivityTypeIds = pyEnv['mail.activity.type'].search([]);

    const { env, openView } = await start({
        serverData,
    });
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.deepEqual(action, {
                context: {
                    default_res_id: mailTestActivityIds[1],
                    default_res_model: "mail.test.activity",
                    default_activity_type_id: mailActivityTypeIds[2],
                },
                res_id: false,
                res_model: "mail.activity",
                target: "new",
                type: "ir.actions.act_window",
                view_mode: "form",
                view_type: "form",
                views: [[false, "form"]]
            },
            "should do a do_action with correct parameters");
            options.onClose();
            return Promise.resolve();
        },
    });

    const $activity = $(document.querySelector('.o_activity_view'));
    assert.containsOnce($activity, 'table',
        'should have a table');
    var $th1 = $activity.find('table thead tr:first th:nth-child(2)');
    assert.containsOnce($th1, 'span:first:contains(Email)', 'should contain "Email" in header of first column');
    assert.containsOnce($th1, '.o_legacy_kanban_counter', 'should contain a progressbar in header of first column');
    assert.hasAttrValue($th1.find('.o_kanban_counter_progress .progress-bar:first'), 'data-bs-original-title', '1 Planned',
        'the counter progressbars should be correctly displayed');
    assert.hasAttrValue($th1.find('.o_kanban_counter_progress .progress-bar:nth-child(2)'), 'data-bs-original-title', '1 Today',
        'the counter progressbars should be correctly displayed');
    var $th2 = $activity.find('table thead tr:first th:nth-child(3)');
    assert.containsOnce($th2, 'span:first:contains(Call)', 'should contain "Call" in header of second column');
    assert.hasAttrValue($th2.find('.o_kanban_counter_progress .progress-bar:nth-child(3)'), 'data-bs-original-title', '1 Overdue',
        'the counter progressbars should be correctly displayed');
    assert.containsNone($activity, 'table thead tr:first th:nth-child(4) .o_kanban_counter',
        'should not contain a progressbar in header of 3rd column');
    assert.ok($activity.find('table tbody tr:first td:first:contains(Office planning)').length,
        'should contain "Office planning" in first colum of first row');
    assert.ok($activity.find('table tbody tr:nth-child(2) td:first:contains(Meeting Room Furnitures)').length,
        'should contain "Meeting Room Furnitures" in first colum of second row');

    var today = activityDateFormat(new Date());

    assert.ok($activity.find('table tbody tr:first td:nth-child(2).today .o_closest_deadline:contains(' + today + ')').length,
        'should contain an activity for today in second cell of first line ' + today);
    var td = 'table tbody tr:nth-child(1) td.o_activity_empty_cell';
    assert.containsN($activity, td, 2, 'should contain an empty cell as no activity scheduled yet.');

    // schedule an activity (this triggers a do_action)
    await testUtils.fields.editAndTrigger($activity.find(td + ':first'), null, ['mouseenter', 'click']);
    assert.containsOnce($activity, 'table tfoot tr .o_record_selector',
        'should contain search more selector to choose the record to schedule an activity for it');
});

QUnit.test('activity view: no content rendering', async function (assert) {
    assert.expect(2);

    const { openView, pyEnv } = await start({
        serverData,
    });
    // reset incompatible setup
    pyEnv['mail.activity.type'].unlink(pyEnv['mail.activity.type'].search([]));
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    const $activity = $(document);

    assert.containsOnce($activity, '.o_view_nocontent',
        "should display the no content helper");
    assert.strictEqual($activity.find('.o_view_nocontent .o_view_nocontent_empty_folder').text().trim(),
        "No data to display",
        "should display the no content helper text");
});

QUnit.test('activity view: batch send mail on activity', async function (assert) {
    assert.expect(6);

    const mailTestActivityIds = pyEnv['mail.test.activity'].search([]);
    const mailTemplateIds = pyEnv['mail.template'].search([]);
    const { openView } = await start({
        serverData,
        mockRPC: function(route, args) {
            if (args.method === 'activity_send_mail') {
                assert.step(JSON.stringify(args.args));
                return Promise.resolve(true);
            }
        },
    });
    await openView({
        res_model: "mail.test.activity",
        views: [[false, "activity"]],
    });
    const $activity = $(document);
    assert.notOk($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown shouldn\'t be displayed');

    testUtils.dom.click($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v'));
    assert.ok($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown should have appeared');

    testUtils.dom.click($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template2)'));
    assert.notOk($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown shouldn\'t be displayed');

    testUtils.dom.click($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v'));
    testUtils.dom.click($activity.find('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template1)'));
    assert.verifySteps([
        `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[1]}]`, // send mail template 1 on mail.test.activity 1 and 2
        `[[${mailTestActivityIds[0]},${mailTestActivityIds[1]}],${mailTemplateIds[0]}]`, // send mail template 2 on mail.test.activity 1 and 2
    ]);
});

QUnit.test('activity view: activity widget', async function (assert) {
    assert.expect(16);

    const mailActivityTypeIds = pyEnv['mail.activity.type'].search([]);
    const [mailTestActivityId2] = pyEnv['mail.test.activity'].search([['name', '=', 'Office planning']]);
    const [mailTemplateId1] = pyEnv['mail.template'].search([['name', '=', 'Template1']]);
    const { env, openView } = await start({
        mockRPC: function (route, args) {
            if (args.method === 'activity_send_mail') {
                assert.deepEqual([[mailTestActivityId2], mailTemplateId1], args.args, "Should send template related to mailTestActivity2");
                assert.step('activity_send_mail');
                // random value returned in order for the mock server to know that this route is implemented.
                return true;
            }
            if (args.method === 'action_feedback_schedule_next') {
                assert.deepEqual(
                    [pyEnv['mail.activity'].search([['state', '=', 'overdue']])],
                    args.args,
                    "Should execute action_feedback_schedule_next only on the overude activity"
                );
                assert.equal(args.kwargs.feedback, "feedback2");
                assert.step('action_feedback_schedule_next');
                return Promise.resolve({ serverGeneratedAction: true });
            }
        },
        serverData,
    });
    await openView({
        res_model: 'mail.test.activity',
        views: [[false, 'activity']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action) {
            if (action.serverGeneratedAction) {
                assert.step('serverGeneratedAction');
            } else if (action.res_model === 'mail.compose.message') {
                assert.deepEqual({
                    default_model: 'mail.test.activity',
                    default_res_id: mailTestActivityId2,
                    default_template_id: mailTemplateId1,
                    default_use_template: true,
                    force_email: true
                    }, action.context);
                assert.step("do_action_compose");
            } else if (action.res_model === 'mail.activity') {
                assert.deepEqual({
                    "default_activity_type_id": mailActivityTypeIds[1],
                    "default_res_id": mailTestActivityId2,
                    "default_res_model": 'mail.test.activity',
                }, action.context);
                assert.step("do_action_activity");
            } else {
                assert.step("Unexpected action");
            }
            return Promise.resolve();
        },
    });

    await testUtils.dom.click(document.querySelector('.today .o_closest_deadline'));
    assert.hasClass(document.querySelector('.today .dropdown-menu.o_activity'), 'show', "dropdown should be displayed");
    assert.ok(document.querySelector('.o_activity_color_today').textContent.includes('Today'), "Title should be today");
    assert.ok([...document.querySelectorAll('.today .o_activity_title_entry')].filter(el => el.textContent.includes('Template1')).length,
        "Template1 should be available");
    assert.ok([...document.querySelectorAll('.today .o_activity_title_entry')].filter(el => el.textContent.includes('Template2')).length,
        "Template2 should be available");

    await testUtils.dom.click(document.querySelector('.o_activity_title_entry[data-activity-id="2"] .o_activity_template_preview'));
    await testUtils.dom.click(document.querySelector('.o_activity_title_entry[data-activity-id="2"] .o_activity_template_send'));
    await testUtils.dom.click(document.querySelector('.overdue .o_closest_deadline'));
    assert.notOk(document.querySelector('.overdue .o_activity_template_preview'),
        "No template should be available");

    await testUtils.dom.click(document.querySelector('.overdue .o_schedule_activity'));
    await testUtils.dom.click(document.querySelector('.overdue .o_closest_deadline'));
    await testUtils.dom.click(document.querySelector('.overdue .o_mark_as_done'));
    document.querySelector('.overdue #activity_feedback').value = "feedback2";

    await testUtils.dom.click(document.querySelector('.overdue .o_activity_popover_done_next'));
    assert.verifySteps([
        "do_action_compose",
        "activity_send_mail",
        "do_action_activity",
        "action_feedback_schedule_next",
        "serverGeneratedAction"
    ]);

});

QUnit.test("activity view: no group_by_menu and no comparison_menu", async function (assert) {
    assert.expect(4);

    serverData.actions = {
        1: {
            id: 1,
            name: "MailTestActivity Action",
            res_model: "mail.test.activity",
            type: "ir.actions.act_window",
            views: [[false, "activity"]],
        },
    };

    const mockRPC = (route, args) => {
        if (args.method === "get_activity_data") {
            assert.strictEqual(
                args.kwargs.context.lang,
                "zz_ZZ",
                "The context should have been passed"
            );
        }
    };

    patchWithCleanup(session.user_context, { lang: "zz_ZZ" });

    const { webClient } = await start({ serverData, mockRPC });

    await doAction(webClient, 1);

    assert.containsN(
        document.body,
        ".o_search_options .dropdown button:visible",
        2,
        "only two elements should be available in view search"
    );
    assert.isVisible(
        document.querySelector(".o_search_options .dropdown.o_filter_menu > button"),
        "filter should be available in view search"
    );
    assert.isVisible(
        document.querySelector(".o_search_options .dropdown.o_favorite_menu > button"),
        "favorites should be available in view search"
    );
});

QUnit.test('activity view: search more to schedule an activity for a record of a respecting model', async function (assert) {
    assert.expect(5);
    const mailTestActivityId1 = pyEnv['mail.test.activity'].create({ name: 'MailTestActivity 3' });
    Object.assign(serverData.views, {
        'mail.test.activity,false,list': '<tree string="MailTestActivity"><field name="name"/></tree>',
    });
    const { env, openView } = await start({
        mockRPC(route, args) {
            if (args.method === 'name_search') {
                args.kwargs.name = "MailTestActivity";
            }
        },
        serverData,
    });
    await openView({
        res_model: 'mail.test.activity',
        views: [[false, 'activity']],
    });
    patchWithCleanup(env.services.action, {
        doAction(action, options) {
            assert.step('doAction');
            var expectedAction = {
                context: {
                    default_res_id: mailTestActivityId1,
                    default_res_model: "mail.test.activity",
                },
                name: "Schedule Activity",
                res_id: false,
                res_model: "mail.activity",
                target: "new",
                type: "ir.actions.act_window",
                view_mode: "form",
                views: [[false, "form"]],
            };
            assert.deepEqual(action, expectedAction,
                "should execute an action with correct params");
            options.onClose();
            return Promise.resolve();
        },
    });

    const activity = $(document);
    assert.containsOnce(activity, 'table tfoot tr .o_record_selector',
        'should contain search more selector to choose the record to schedule an activity for it');
    await testUtils.dom.click(activity.find('table tfoot tr .o_record_selector'));
    // search create dialog
    var $modal = $('.modal-lg');
    assert.strictEqual($modal.find('.o_data_row').length, 3, "all mail.test.activity should be available to select");
    // select a record to schedule an activity for it (this triggers a do_action)
    await testUtils.dom.click($modal.find('.o_data_row:last .o_data_cell'));
    assert.verifySteps(['doAction']);
});

QUnit.test("Activity view: discard an activity creation dialog", async function (assert) {
    assert.expect(2);

    serverData.actions = {
        1: {
            id: 1,
            name: "MailTestActivity Action",
            res_model: "mail.test.activity",
            type: "ir.actions.act_window",
            views: [[false, "activity"]],
        },
    };

    Object.assign(serverData.views, {
        'mail.activity,false,form':
            `<form>
                <field name="display_name"/>
                <footer>
                    <button string="Discard" class="btn-secondary" special="cancel"/>
                </footer>
            </form>`,
    });

    const mockRPC = (route, args) => {
        if (args.method === "check_access_rights") {
            return true;
        }
    };

    const { webClient } = await start({ serverData, mockRPC });
    await doAction(webClient, 1);

    await testUtils.dom.click(
        document.querySelector(".o_activity_view .o_data_row .o_activity_empty_cell")
    );
    await legacyExtraNextTick();
    assert.containsOnce($, ".modal.o_technical_modal", "Activity Modal should be opened");

    await testUtils.dom.click($('.modal.o_technical_modal button[special="cancel"]'));
    await legacyExtraNextTick();
    assert.containsNone($, ".modal.o_technical_modal", "Activity Modal should be closed");
});

QUnit.test('Activity view: many2one_avatar_user widget in activity view', async function (assert) {
    assert.expect(3);

    const [mailTestActivityId1] = pyEnv['mail.test.activity'].search([['name', '=', 'Meeting Room Furnitures']]);
    const resUsersId1 = pyEnv['res.users'].create({
        display_name: "first user",
        avatar_128: "Atmaram Bhide",
    });
    pyEnv['mail.test.activity'].write([mailTestActivityId1], { activity_user_id: resUsersId1 });
    Object.assign(serverData.views, {
        'mail.test.activity,false,activity':
            `<activity string="MailTestActivity">
                <templates>
                    <div t-name="activity-box">
                        <field name="activity_user_id" widget="many2one_avatar_user"/>
                        <field name="name"/>
                    </div>
                </templates>
            </activity>`,
    });
    serverData.actions = {
        1: {
            id: 1,
            name: 'MailTestActivity Action',
            res_model: 'mail.test.activity',
            type: 'ir.actions.act_window',
            views: [[false, 'activity']],
        }
    };

    const { webClient } = await start({ serverData });
    await doAction(webClient, 1);

    await legacyExtraNextTick();
    assert.containsN(document.body, '.o_m2o_avatar', 2);
    assert.containsOnce(document.body, `tr[data-res-id=${mailTestActivityId1}] .o_m2o_avatar > img[data-src="/web/image/res.users/${resUsersId1}/avatar_128"]`,
        "should have m2o avatar image");
    assert.containsNone(document.body, '.o_m2o_avatar > span',
        "should not have text on many2one_avatar_user if onlyImage node option is passed");
});

QUnit.test("Activity view: on_destroy_callback doesn't crash", async function (assert) {
    assert.expect(3);

    patchWithCleanup(ActivityRenderer.prototype, {
        setup() {
            this._super();
            owl.onMounted(() => {
                assert.step('mounted');
            });
            owl.onWillUnmount(() => {
                assert.step('willUnmount');
            });
        }
    });

    const { openView } = await start({
        serverData,
    });
    await openView({
        res_model: 'mail.test.activity',
        views: [[false, 'activity']],
    });
    // force the unmounting of the activity view by opening another one
    await openView({
        res_model: 'mail.test.activity',
        views: [[false, 'form']],
    });

    assert.verifySteps([
        'mounted',
        'willUnmount'
    ]);
});

QUnit.test("Schedule activity dialog uses the same search view as activity view", async function (assert) {
    assert.expect(8);
    pyEnv['mail.test.activity'].unlink(pyEnv['mail.test.activity'].search([]));
    Object.assign(serverData.views, {
        "mail.test.activity,false,list": `<list><field name="name"/></list>`,
        "mail.test.activity,false,search": `<search/>`,
        'mail.test.activity,1,search': `<search/>`,
    });

    function mockRPC(route, args) {
        if (args.method === "get_views") {
            assert.step(JSON.stringify(args.kwargs.views));
        }
    }

    const { webClient } = await start({ serverData, mockRPC });

    // open an activity view (with default search arch)
    await doAction(webClient, {
        name: 'Dashboard',
        res_model: 'mail.test.activity',
        type: 'ir.actions.act_window',
        views: [[false, 'activity']],
    });

    assert.verifySteps([
        '[[false,"activity"],[false,"search"]]',
    ])

    // click on "Schedule activity"
    await click(document.querySelector(".o_activity_view .o_record_selector"));

    assert.verifySteps([
        '[[false,"list"],[false,"search"]]',
    ])

    // open an activity view (with search arch 1)
    await doAction(webClient, {
        name: 'Dashboard',
        res_model: 'mail.test.activity',
        type: 'ir.actions.act_window',
        views: [[false, 'activity']],
        search_view_id: [1,"search"],
    });

    assert.verifySteps([
        '[[false,"activity"],[1,"search"]]',
    ])

    // click on "Schedule activity"
    await click(document.querySelector(".o_activity_view .o_record_selector"));

    assert.verifySteps([
        '[[false,"list"],[1,"search"]]',
    ]);
});

QUnit.test('Activity view: apply progressbar filter', async function (assert) {
    assert.expect(9);

    serverData.actions = {
        1: {
            id: 1,
            name: 'MailTestActivity Action',
            res_model: 'mail.test.activity',
            type: 'ir.actions.act_window',
            views: [[false, 'activity']],
        }
    };

    const { webClient } = await start({ serverData });

    await doAction(webClient, 1);

    assert.containsNone(document.querySelector('.o_activity_view thead'),
        '.o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false',
        "should not have active filter");
    assert.containsNone(document.querySelector('.o_activity_view tbody'),
        '.o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false',
        "should not have active filter");
    assert.strictEqual(document.querySelector('.o_activity_view tbody .o_activity_record').textContent,
        'Office planning', "'Office planning' should be first record");
    assert.containsOnce(document.querySelector('.o_activity_view tbody'), '.planned',
        "other records should be available");

    await testUtils.dom.click(document.querySelector('.o_kanban_counter_progress .progress-bar[data-filter="planned"]'));
    assert.containsOnce(document.querySelector('.o_activity_view thead'), '.o_activity_filter_planned',
        "planned should be active filter");
    assert.containsN(document.querySelector('.o_activity_view tbody'), '.o_activity_filter_planned', 5,
        "planned should be active filter");
    assert.strictEqual(document.querySelector('.o_activity_view tbody .o_activity_record').textContent,
        'Meeting Room Furnitures', "'Office planning' should be first record");
    const tr = document.querySelectorAll('.o_activity_view tbody tr')[1];
    assert.hasClass(tr.querySelectorAll('td')[1], 'o_activity_empty_cell',
        "other records should be hidden");
    assert.containsNone(document.querySelector('.o_activity_view tbody'), 'planned',
        "other records should be hidden");
});

});
