/** @odoo-module **/

import ActivityRenderer from '@mail/js/views/activity/activity_renderer';
import ActivityView from '@mail/js/views/activity/activity_view';
import testUtils from 'web.test_utils';
import domUtils from 'web.dom';

import { legacyExtraNextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { session } from '@web/session';
import { click } from "@web/../tests/helpers/utils";

let serverData;

var createView = testUtils.createView;

QUnit.module('mail', {}, function () {
QUnit.module('activity view', {
    beforeEach: function () {
        this.data = {
            task: {
                fields: {
                    id: {string: 'ID', type: 'integer'},
                    foo: {string: "Foo", type: "char"},
                    activity_ids: {
                        string: 'Activities',
                        type: 'one2many',
                        relation: 'mail.activity',
                        relation_field: 'res_id',
                    },
                },
                records: [
                    {id: 13, foo: 'Meeting Room Furnitures', activity_ids: [1]},
                    {id: 30, foo: 'Office planning', activity_ids: [2, 3]},
                ],
            },
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                },
                records: [{
                    id: 2,
                    display_name: "first partner",
                }]
            },
            'mail.activity': {
                fields: {
                    res_id: { string: 'Related document id', type: 'integer' },
                    activity_type_id: { string: "Activity type", type: "many2one", relation: "mail.activity.type" },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    can_write: { string: "Can write", type: "boolean" },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    mail_template_ids: { string: "Mail templates", type: "many2many", relation: "mail.template" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                },
                records:[
                    {
                        id: 1,
                        res_id: 13,
                        display_name: "An activity",
                        date_deadline: moment().add(3, "days").format("YYYY-MM-DD"), // now
                        can_write: true,

                        state: "planned",
                        activity_type_id: 1,
                        mail_template_ids: [8, 9],
                        user_id:2,
                    },{
                        id: 2,
                        res_id: 30,
                        display_name: "An activity",
                        date_deadline: moment().format("YYYY-MM-DD"), // now
                        can_write: true,
                        state: "today",
                        activity_type_id: 1,
                        mail_template_ids: [8, 9],
                        user_id:2,
                    },{
                        id: 3,
                        res_id: 30,
                        display_name: "An activity",
                        date_deadline: moment().subtract(2, "days").format("YYYY-MM-DD"), // now
                        can_write: true,
                        state: "overdue",
                        activity_type_id: 2,
                        mail_template_ids: [],
                        user_id:2,
                    }
                ],
            },
            'mail.template': {
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 8, name: "Template1" },
                    { id: 9, name: "Template2" },
                ],
            },
            'mail.activity.type': {
                fields: {
                    mail_template_ids: { string: "Mail templates", type: "many2many", relation: "mail.template" },
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 1, name: "Email", mail_template_ids: [8, 9]},
                    { id: 2, name: "Call" },
                    { id: 3, name: "Call for Demo" },
                    { id: 4, name: "To Do" },
                ],
            },
        };
        serverData = { models: this.data };
    }
});

var activityDateFormat = function (date) {
    return date.toLocaleDateString(moment().locale(), { day: 'numeric', month: 'short' });
};

QUnit.test('activity view: simple activity rendering', async function (assert) {
    assert.expect(14);
    var activity = await createView({
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: '<activity string="Task">' +
                    '<templates>' +
                        '<div t-name="activity-box">' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</templates>' +
            '</activity>',
        intercepts: {
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    context: {
                        default_res_id: 30,
                        default_res_model: "task",
                        default_activity_type_id: 3,
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
                event.data.options.on_close();
            },
        },
    });

    assert.containsOnce(activity, 'table',
        'should have a table');
    var $th1 = activity.$('table thead tr:first th:nth-child(2)');
    assert.containsOnce($th1, 'span:first:contains(Email)', 'should contain "Email" in header of first column');
    assert.containsOnce($th1, '.o_kanban_counter', 'should contain a progressbar in header of first column');
    assert.hasAttrValue($th1.find('.o_kanban_counter_progress .progress-bar:first'), 'data-original-title', '1 Planned',
        'the counter progressbars should be correctly displayed');
    assert.hasAttrValue($th1.find('.o_kanban_counter_progress .progress-bar:nth-child(2)'), 'data-original-title', '1 Today',
        'the counter progressbars should be correctly displayed');
    var $th2 = activity.$('table thead tr:first th:nth-child(3)');
    assert.containsOnce($th2, 'span:first:contains(Call)', 'should contain "Call" in header of second column');
    assert.hasAttrValue($th2.find('.o_kanban_counter_progress .progress-bar:nth-child(3)'), 'data-original-title', '1 Overdue',
        'the counter progressbars should be correctly displayed');
    assert.containsNone(activity, 'table thead tr:first th:nth-child(4) .o_kanban_counter',
        'should not contain a progressbar in header of 3rd column');
    assert.ok(activity.$('table tbody tr:first td:first:contains(Office planning)').length,
        'should contain "Office planning" in first colum of first row');
    assert.ok(activity.$('table tbody tr:nth-child(2) td:first:contains(Meeting Room Furnitures)').length,
        'should contain "Meeting Room Furnitures" in first colum of second row');

    var today = activityDateFormat(new Date());

    assert.ok(activity.$('table tbody tr:first td:nth-child(2).today .o_closest_deadline:contains(' + today + ')').length,
        'should contain an activity for today in second cell of first line ' + today);
    var td = 'table tbody tr:nth-child(1) td.o_activity_empty_cell';
    assert.containsN(activity, td, 2, 'should contain an empty cell as no activity scheduled yet.');

    // schedule an activity (this triggers a do_action)
    await testUtils.fields.editAndTrigger(activity.$(td + ':first'), null, ['mouseenter', 'click']);
    assert.containsOnce(activity, 'table tfoot tr .o_record_selector',
        'should contain search more selector to choose the record to schedule an activity for it');

    activity.destroy();
});

QUnit.test('activity view: no content rendering', async function (assert) {
    assert.expect(2);

    // reset incompatible setup
    this.data['mail.activity'].records = [];
    this.data.task.records.forEach(function (task) {
        task.activity_ids = false;
    });
    this.data['mail.activity.type'].records = [];

    var activity = await createView({
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: '<activity string="Task">' +
                '<templates>' +
                    '<div t-name="activity-box">' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</templates>' +
            '</activity>',
    });

    assert.containsOnce(activity, '.o_view_nocontent',
        "should display the no content helper");
    assert.strictEqual(activity.$('.o_view_nocontent .o_view_nocontent_empty_folder').text().trim(),
        "No data to display",
        "should display the no content helper text");

    activity.destroy();
});

QUnit.test('activity view: batch send mail on activity', async function (assert) {
    assert.expect(6);
    var activity = await createView({
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: '<activity string="Task">' +
                '<templates>' +
                    '<div t-name="activity-box">' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</templates>' +
            '</activity>',
        mockRPC: function(route, args) {
            if (args.method === 'activity_send_mail'){
                assert.step(JSON.stringify(args.args));
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    });
    assert.notOk(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown shouldn\'t be displayed');

    testUtils.dom.click(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v'));
    assert.ok(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown should have appeared');

    testUtils.dom.click(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template2)'));
    assert.notOk(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show').length,
        'dropdown shouldn\'t be displayed');

    testUtils.dom.click(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) i.fa-ellipsis-v'));
    testUtils.dom.click(activity.$('table thead tr:first th:nth-child(2) span:nth-child(2) .dropdown-menu.show .o_send_mail_template:contains(Template1)'));
    assert.verifySteps([
        '[[13,30],9]', // send mail template 9 on tasks 13 and 30
        '[[13,30],8]',  // send mail template 8 on tasks 13 and 30
    ]);

    activity.destroy();
});

QUnit.test('activity view: activity widget', async function (assert) {
    assert.expect(16);

    const params = {
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: '<activity string="Task">' +
                '<templates>' +
                    '<div t-name="activity-box">' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</templates>'+
            '</activity>',
        mockRPC: function(route, args) {
            if (args.method === 'activity_send_mail'){
                assert.deepEqual([[30],8],args.args, "Should send template 8 on record 30");
                assert.step('activity_send_mail');
                return Promise.resolve();
            }
            if (args.method === 'action_feedback_schedule_next'){
                assert.deepEqual([[3]],args.args, "Should execute action_feedback_schedule_next on activity 3 only ");
                assert.equal(args.kwargs.feedback, "feedback2");
                assert.step('action_feedback_schedule_next');
                return Promise.resolve({serverGeneratedAction: true});
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (ev) {
                var action = ev.data.action;
                if (action.serverGeneratedAction) {
                    assert.step('serverGeneratedAction');
                } else if (action.res_model === 'mail.compose.message') {
                    assert.deepEqual({
                        default_model: "task",
                        default_res_id: 30,
                        default_template_id: 8,
                        default_use_template: true,
                        force_email: true
                        }, action.context);
                    assert.step("do_action_compose");
                } else if (action.res_model === 'mail.activity') {
                    assert.deepEqual({
                        "default_activity_type_id": 2,
                        "default_res_id": 30,
                        "default_res_model": "task"
                    }, action.context);
                    assert.step("do_action_activity");
                } else {
                    assert.step("Unexpected action");
                }
            },
        },
    };

    var activity = await createView(params);
    var today = activity.$('table tbody tr:first td:nth-child(2).today');
    var dropdown = today.find('.dropdown-menu.o_activity');

    await testUtils.dom.click(today.find('.o_closest_deadline'));
    assert.hasClass(dropdown,'show', "dropdown should be displayed");
    assert.ok(dropdown.find('.o_activity_color_today:contains(Today)').length, "Title should be today");
    assert.ok(dropdown.find('.o_activity_title_entry[data-activity-id="2"]:first div:contains(template8)').length,
        "template8 should be available");
    assert.ok(dropdown.find('.o_activity_title_entry[data-activity-id="2"]:eq(1) div:contains(template9)').length,
        "template9 should be available");

    await testUtils.dom.click(dropdown.find('.o_activity_title_entry[data-activity-id="2"]:first .o_activity_template_preview'));
    await testUtils.dom.click(dropdown.find('.o_activity_title_entry[data-activity-id="2"]:first .o_activity_template_send'));
    var overdue = activity.$('table tbody tr:first td:nth-child(3).overdue');
    await testUtils.dom.click(overdue.find('.o_closest_deadline'));
    dropdown = overdue.find('.dropdown-menu.o_activity');
    assert.notOk(dropdown.find('.o_activity_title div div div:first span').length,
        "No template should be available");

    await testUtils.dom.click(dropdown.find('.o_schedule_activity'));
    await testUtils.dom.click(overdue.find('.o_closest_deadline'));
    await testUtils.dom.click(dropdown.find('.o_mark_as_done'));
    dropdown.find('#activity_feedback').val("feedback2");

    await testUtils.dom.click(dropdown.find('.o_activity_popover_done_next'));
    assert.verifySteps([
        "do_action_compose",
        "activity_send_mail",
        "do_action_activity",
        "action_feedback_schedule_next",
        "serverGeneratedAction"
        ]);

    activity.destroy();
});

QUnit.test("activity view: no group_by_menu and no comparison_menu", async function (assert) {
    assert.expect(4);

    serverData.actions = {
        1: {
            id: 1,
            name: "Task Action",
            res_model: "task",
            type: "ir.actions.act_window",
            views: [[false, "activity"]],
        },
    };

    serverData.views = {
        "task,false,activity":
            '<activity string="Task">' +
            "<templates>" +
            '<div t-name="activity-box">' +
            '<field name="foo"/>' +
            "</div>" +
            "</templates>" +
            "</activity>",
        "task,false,search": "<search></search>",
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

    const webClient = await createWebClient({ serverData, mockRPC , legacyParams: {withLegacyMockServer: true}});

    await doAction(webClient, 1);

    assert.containsN(
        webClient,
        ".o_search_options .dropdown button:visible",
        2,
        "only two elements should be available in view search"
    );
    assert.isVisible(
        $(webClient.el).find(".o_search_options .dropdown.o_filter_menu > button"),
        "filter should be available in view search"
    );
    assert.isVisible(
        $(webClient.el).find(".o_search_options .dropdown.o_favorite_menu > button"),
        "favorites should be available in view search"
    );
});

QUnit.test('activity view: search more to schedule an activity for a record of a respecting model', async function (assert) {
    assert.expect(5);
    _.extend(this.data.task.fields, {
        name: { string: "Name", type: "char" },
    });
    this.data.task.records[2] = { id: 31, name: "Task 3" };
    var activity = await createView({
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: '<activity string="Task">' +
                '<templates>' +
                    '<div t-name="activity-box">' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</templates>' +
            '</activity>',
        archs: {
            "task,false,list": '<tree string="Task"><field name="name"/></tree>',
            "task,false,search": '<search></search>',
        },
        mockRPC: function(route, args) {
            if (args.method === 'name_search') {
                args.kwargs.name = "Task";
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (ev) {
                assert.step('doAction');
                var expectedAction = {
                    context: {
                        default_res_id: { id: 31, display_name: undefined },
                        default_res_model: "task",
                    },
                    name: "Schedule Activity",
                    res_id: false,
                    res_model: "mail.activity",
                    target: "new",
                    type: "ir.actions.act_window",
                    view_mode: "form",
                    views: [[false, "form"]],
                };
                assert.deepEqual(ev.data.action, expectedAction,
                    "should execute an action with correct params");
                ev.data.options.on_close();
            },
        },
    });

    assert.containsOnce(activity, 'table tfoot tr .o_record_selector',
        'should contain search more selector to choose the record to schedule an activity for it');
    await testUtils.dom.click(activity.$('table tfoot tr .o_record_selector'));
    // search create dialog
    var $modal = $('.modal-lg');
    assert.strictEqual($modal.find('.o_data_row').length, 3, "all tasks should be available to select");
    // select a record to schedule an activity for it (this triggers a do_action)
    testUtils.dom.click($modal.find('.o_data_row:last'));
    assert.verifySteps(['doAction']);

    activity.destroy();
});

QUnit.test("Activity view: discard an activity creation dialog", async function (assert) {
    assert.expect(2);

    serverData.actions = {
        1: {
            id: 1,
            name: "Task Action",
            res_model: "task",
            type: "ir.actions.act_window",
            views: [[false, "activity"]],
        },
    };

    serverData.views = {
        "task,false,activity": `
        <activity string="Task">
            <templates>
                <div t-name="activity-box">
                    <field name="foo"/>
                </div>
            </templates>
        </activity>`,
        "task,false,search": "<search></search>",
        "mail.activity,false,form": `
        <form>
            <field name="display_name"/>
            <footer>
                <button string="Discard" class="btn-secondary" special="cancel"/>
            </footer>
        </form>`,
    };

    const mockRPC = (route, args) => {
        if (args.method === "check_access_rights") {
            return true;
        }
    };

    const webClient = await createWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true} });
    await doAction(webClient, 1);

    await testUtils.dom.click(
        $(webClient.el).find(".o_activity_view .o_data_row .o_activity_empty_cell")[0]
    );
    await legacyExtraNextTick();
    assert.containsOnce($, ".modal.o_technical_modal", "Activity Modal should be opened");

    await testUtils.dom.click($('.modal.o_technical_modal button[special="cancel"]'));
    await legacyExtraNextTick();
    assert.containsNone($, ".modal.o_technical_modal", "Activity Modal should be closed");
});

QUnit.test('Activity view: many2one_avatar_user widget in activity view', async function (assert) {
    assert.expect(3);

    const taskModel = serverData.models.task;

    serverData.models['res.users'] = {
        fields: {
            display_name: { string: "Displayed name", type: "char" },
            avatar_128: { string: "Image 128", type: 'image' },
        },
        records: [{
            id: 1,
            display_name: "first user",
            avatar_128: "Atmaram Bhide",
        }],
    };
    taskModel.fields.user_id = { string: "Related User", type: "many2one", relation: 'res.users' };
    taskModel.records[0].user_id = 1;

    serverData.actions = {
        1: {
            id: 1,
            name: 'Task Action',
            res_model: 'task',
            type: 'ir.actions.act_window',
            views: [[false, 'activity']],
        }
    };

    serverData.views = {
        'task,false,activity': `
            <activity string="Task">
                <templates>
                    <div t-name="activity-box">
                        <field name="user_id" widget="many2one_avatar_user"/>
                        <field name="foo"/>
                    </div>
                </templates>
            </activity>`,
        'task,false,search': '<search></search>'
    };

    const webClient = await createWebClient({ serverData, legacyParams: { withLegacyMockServer: true } });
    await doAction(webClient, 1);

    await legacyExtraNextTick();
    assert.containsN(webClient, '.o_m2o_avatar', 2);
    assert.containsOnce(webClient, 'tr[data-res-id=13] .o_m2o_avatar > img[src="/web/image/res.users/1/avatar_128"]',
        "should have m2o avatar image");
    assert.containsNone(webClient, '.o_m2o_avatar > span',
        "should not have text on many2one_avatar_user if onlyImage node option is passed");
});

QUnit.test("Activity view: on_destroy_callback doesn't crash", async function (assert) {
    assert.expect(3);

    const params = {
        View: ActivityView,
        model: 'task',
        data: this.data,
        arch: `<activity string="Task">
                <templates>
                    <div t-name="activity-box">
                        <field name="foo"/>
                    </div>
                </templates>
            </activity>`,
    };

    patchWithCleanup(ActivityRenderer.prototype, {
        mounted() {
            assert.step('mounted');
        },
        willUnmount() {
            assert.step('willUnmount');
        }
    });

    const activity = await createView(params);
    domUtils.detach([{ widget: activity }]);

    assert.verifySteps([
        'mounted',
        'willUnmount'
    ]);

    activity.destroy();
});

QUnit.test("Schedule activity dialog uses the same search view as activity view", async function (assert) {
    assert.expect(8);
    serverData.models.task.records = [];
    serverData.views = {
        "task,false,activity": `
            <activity string="Task">
                <templates>
                    <div t-name="activity-box">
                        <field name="foo"/>
                    </div>
                </templates>
            </activity>
        `,
        "task,false,list": `<list><field name="foo"/></list>`,
        "task,false,search": `<search/>`,
        'task,1,search': `<search/>`,
    };

    function mockRPC(route, args) {
        if (args.method === "load_views") {
            assert.step(JSON.stringify(args.kwargs.views));
        } 
    }

    const webClient = await createWebClient({ serverData, mockRPC, legacyParams: {withLegacyMockServer: true} });

    // open an activity view (with default search arch)
    await doAction(webClient, {
        name: 'Dashboard',
        res_model: 'task',
        type: 'ir.actions.act_window',
        views: [[false, 'activity']],
    });

    assert.verifySteps([
        '[[false,"activity"],[false,"search"]]',
    ])

    // click on "Schedule activity"
    await click(webClient.el.querySelector(".o_activity_view .o_record_selector"));

    assert.verifySteps([
        '[[false,"list"],[false,"search"]]',
    ])

    // open an activity view (with search arch 1)
    await doAction(webClient, {
        name: 'Dashboard',
        res_model: 'task',
        type: 'ir.actions.act_window',
        views: [[false, 'activity']],
        search_view_id: [1,"search"],
    });

    assert.verifySteps([
        '[[false,"activity"],[1,"search"]]',
    ])

    // click on "Schedule activity"
    await click(webClient.el.querySelector(".o_activity_view .o_record_selector"));

    assert.verifySteps([
        '[[false,"list"],[1,"search"]]',
    ])
});

QUnit.test('Activity view: apply progressbar filter', async function (assert) {
    assert.expect(9);

    serverData.actions = {
        1: {
            id: 1,
            name: 'Task Action',
            res_model: 'task',
            type: 'ir.actions.act_window',
            views: [[false, 'activity']],
        }
    };
    serverData.views = {
        'task,false,activity':
            `<activity string="Task" >
                <templates>
                    <div t-name="activity-box">
                        <field name="foo"/>
                    </div>
                </templates>
            </activity>`,
        'task,false,search': '<search></search>',
    };

    const webClient = await createWebClient({ serverData, legacyParams: { withLegacyMockServer: true } });

    await doAction(webClient, 1);

    assert.containsNone(webClient.el.querySelector('.o_activity_view thead'),
        '.o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false',
        "should not have active filter");
    assert.containsNone(webClient.el.querySelector('.o_activity_view tbody'),
        '.o_activity_filter_planned,.o_activity_filter_today,.o_activity_filter_overdue,.o_activity_filter___false',
        "should not have active filter");
    assert.strictEqual(webClient.el.querySelector('.o_activity_view tbody .o_activity_record').textContent,
        'Office planning', "'Office planning' should be first record");
    assert.containsOnce(webClient.el.querySelector('.o_activity_view tbody'), '.planned',
        "other records should be available");

    await testUtils.dom.click(webClient.el.querySelector('.o_kanban_counter_progress .progress-bar[data-filter="planned"]'));
    assert.containsOnce(webClient.el.querySelector('.o_activity_view thead'), '.o_activity_filter_planned',
        "planned should be active filter");
    assert.containsN(webClient.el.querySelector('.o_activity_view tbody'), '.o_activity_filter_planned', 5,
        "planned should be active filter");
    assert.strictEqual(webClient.el.querySelector('.o_activity_view tbody .o_activity_record').textContent,
        'Meeting Room Furnitures', "'Office planning' should be first record");
    const tr = webClient.el.querySelectorAll('.o_activity_view tbody tr')[1];
    assert.hasClass(tr.querySelectorAll('td')[1], 'o_activity_empty_cell',
        "other records should be hidden");
    assert.containsNone(webClient.el.querySelector('.o_activity_view tbody'), 'planned',
        "other records should be hidden");
});

});
