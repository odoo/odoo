odoo.define('mail.chatter_tests', function (require) {
"use strict";

const { getMailServices } = require('mail.messaging.testUtils');

var core = require('web.core');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');
var concurrency = require('web.concurrency');

var createView = testUtils.createView;

var Activity = require('mail.Activity');
var _t = core._t;

QUnit.module('mail', {}, function () {

QUnit.module('Chatter', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.services = getMailServices();
        this.data = {
            'res.partner': {
                fields: {
                    im_status: {
                        string: "im_status",
                        type: "char",
                    }
                },
                records: [{
                    id: 1,
                    im_status: 'online',
                }]
            },
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    message_follower_ids: {
                        string: "Followers",
                        type: "one2many",
                        relation: 'mail.followers',
                        relation_field: "res_id",
                    },
                    message_ids: {
                        string: "messages",
                        type: "one2many",
                        relation: 'mail.message',
                        relation_field: "res_id",
                    },
                    activity_ids: {
                        string: 'Activities',
                        type: 'one2many',
                        relation: 'mail.activity',
                        relation_field: 'res_id',
                    },
                    activity_exception_decoration: {
                        string: 'Decoration',
                        type: 'selection',
                        selection: [['warning', 'Alert'], ['danger', 'Error']],
                    },
                    activity_exception_icon: {
                        string: 'icon',
                        type: 'char',
                    },
                    activity_state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    message_attachment_count: {
                        string: 'Attachment count',
                        type: 'integer',
                    },
                },
                records: [{
                    id: 2,
                    message_attachment_count: 3,
                    display_name: "first partner",
                    foo: "HELLO",
                    message_follower_ids: [],
                    message_ids: [],
                    activity_ids: [],
                }]
            },
            'mail.activity': {
                fields: {
                    activity_type_id: { string: "Activity type", type: "many2one", relation: "mail.activity.type" },
                    create_uid: { string: "Created By", type: "many2one", relation: 'partner' },
                    can_write: { string: "Can write", type: "boolean" },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    activity_category: {
                        string: 'Category',
                        type: 'selection',
                        selection: [['default', 'Other'], ['upload_file', 'Upload File']],
                    },
                    note : { string: "Note", type: "char" },
                },
            },
            'mail.activity.type': {
                fields: {
                    name: { string: "Name", type: "char" },
                    category: {
                        string: 'Category',
                        type: 'selection',
                        selection: [['default', 'Other'], ['upload_file', 'Upload File']],
                    },
                    decoration_type: { string: "Decoration Type", type: "selection", selection: [['warning', 'Alert'], ['danger', 'Error']]},
                    icon: {string: 'icon', type:"char"},
                },
                records: [
                    { id: 1, name: "Type 1" },
                    { id: 2, name: "Type 2" },
                    { id: 3, name: "Type 3", category: 'upload_file' },
                    { id: 4, name: "Exception", decoration_type: "warning", icon: "fa-warning"}
                ],
            },
            'mail.message': {
                fields: {
                    attachment_ids: {
                        string: "Attachments",
                        type: 'many2many',
                        relation: 'ir.attachment',
                        default: [],
                    },
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
                    is_note: {
                        string: "Note",
                        type: 'boolean',
                    },
                    is_discussion: {
                        string: "Discussion",
                        type: 'boolean',
                    },
                    is_notification: {
                        string: "Notification",
                        type: 'boolean',
                    },
                    model: {
                        string: "Related Document Model",
                        type: 'char',
                    },
                    res_id: {
                        string: "Related Document ID",
                        type: 'integer',
                    }
                },
                records: [],
            },
            'ir.attachment': {
                fields:{
                    name:{type:'char', string:"attachment name", required:true},
                    res_model:{type:'char', string:"res model"},
                    res_id:{type:'integer', string:"res id"},
                    url:{type:'char', string:'url'},
                    type:{ type:'selection', selection:[['url',"URL"],['binary',"BINARY"]]},
                    mimetype:{type:'char', string:"mimetype"},
                },
                records:[
                    {id:1, type:'url', mimetype:'image/png', name:'filename.jpg',
                     res_id: 7, res_model: 'partner'},
                    {id:2, type:'binary', mimetype:"application/x-msdos-program",
                     name:"file2.txt", res_id: 7, res_model: 'partner'},
                    {id:3, type:'binary', mimetype:"application/x-msdos-program",
                     name:"file3.txt", res_id: 5, res_model: 'partner'},
                ],
            },
        };
    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

// {xdu} Deleted most of these tests because they are depreciated
// keeping some of them in skipped, they should be deleted/moved when working
// on activity and followers components

QUnit.skip('Activity Done keep feedback on blur', async function (assert) {
    assert.expect(3);
    var done = assert.async();

    this.data['mail.activity'].records = [
        {activity_type_id: 1, id: 1, can_write: true, user_id: 2, state: 'today', note: 'But I\'m talkin\' about Shaft'},
    ];
    this.data.partner.records[0].activity_ids = [1];

    var shownDef = testUtils.makeTestPromise();
    var hiddenDef = testUtils.makeTestPromise();
    testUtils.mock.patch(Activity, {
        _bindPopoverFocusout: function () {
            this._super.apply(this, arguments);
            shownDef.resolve();
        },
    });

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        res_id: 2,
        arch:'<form string="Partners">' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
    });
    // sanity checks
    var $activityEl = form.$('.o_mail_activity[name=activity_ids]');
    assert.strictEqual($activityEl.find('.o_thread_message').length, 1,
        'There should be one activity');
    assert.strictEqual($activityEl.find('.o_thread_message .o_thread_message_note').text().trim(),
        'But I\'m talkin\' about Shaft', 'The activity should have the right note');

    var $popoverEl = $activityEl.find('.o_thread_message_tools .o_mark_as_done');
    $popoverEl.on('hidden.bs.popover', hiddenDef.resolve.bind(hiddenDef));

    // open popover
    await testUtils.dom.click($popoverEl);

    shownDef.then(function () {
        // write a feedback and focusout
        var $feedbackPopover = $($popoverEl.data('bs.popover').tip);
        $feedbackPopover.find('#activity_feedback').val('John Shaft').focusout();

        hiddenDef.then(async function () {
            shownDef = testUtils.makeTestPromise();

            // re-open popover
            await testUtils.dom.click($popoverEl);

            shownDef.then(function () {
                var $feedbackPopover = $($popoverEl.data('bs.popover').tip);
                assert.strictEqual($feedbackPopover.find('#activity_feedback').val(), 'John Shaft',
                    "feedback should have been kept");

                form.destroy();
                testUtils.mock.unpatch(Activity);
                done();
            });
        });
    });
});

QUnit.skip('Activity Done by uploading a file', async function (assert) {
    assert.expect(4);

    // simulate (shortcut) the upload and trigger the event when the
    // attachment is created serverside.
    testUtils.mock.patch(Activity, {
        _onMarkActivityDoneUploadFile: function (ev) {
            var $markDoneBtn = $(ev.currentTarget);
            var fileuploadID = $markDoneBtn.data('fileupload-id');

            $(window).trigger(fileuploadID, [{
                id:3,
                type:'binary',
                mimetype:"application/x-msdos-program",
                name:"file2.txt",
                res_id: 5,
                res_model: 'partner'
            }]);
        },
    });

    // create the activity
    this.data['mail.activity'].records = [{
        activity_type_id: 3,
        id: 1,
        can_write: true,
        user_id: 2,
        state: 'today',
        note: "But I'm talkin' about Shaft",
        activity_category: 'upload_file'
    }];
    this.data.partner.records[0].activity_ids = [1];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        res_id: 2,
        arch:'<form string="Partners">' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'action_feedback') {
                var current_ids = this.data.partner.records[0].activity_ids;
                var done_ids = args.args[0];
                this.data.partner.records[0].activity_ids = _.difference(current_ids, done_ids);
                this.data.partner.records[0].activity_state = false;
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    });

    var $activity = form.$('.o_mail_activity[name=activity_ids]');
    assert.containsOnce($activity, '.o_thread_message', 'There should be one activity');
    assert.containsOnce($activity, '.o_hidden_input_file', 'There should be one hidden file upload form');
    assert.strictEqual($activity.find('.o_thread_message .o_thread_message_note').text().trim(),
        'But I\'m talkin\' about Shaft', 'The activity should have the right note');

    // click on "upload" button
    var $uploadBtn = $activity.find('.o_mark_as_done_upload_file');
    await testUtils.dom.click($uploadBtn);

    assert.containsNone($activity, '.o_thread_message', 'The only activity should be marked as done');

    testUtils.mock.unpatch(Activity);
    form.destroy();
});

QUnit.skip('kanban activity widget with no activity', async function (assert) {
    assert.expect(4);

    var rpcCount = 0;
    var kanban = await createView({
        View: KanbanView,
        model: 'partner',
        data: this.data,
        arch: '<kanban>' +
                    '<field name="activity_state"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="activity_ids" widget="kanban_activity"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        mockRPC: function (route, args) {
            rpcCount++;
            return this._super(route, args);
        },
        session: {uid: 2},
    });

    var $record = kanban.$('.o_kanban_record').first();
    assert.ok($record.find('.o_mail_activity .o_activity_color_default').length,
        "activity widget should have been rendered correctly");
    assert.strictEqual(rpcCount, 1, '1 RPC (search_read) should have been done');

    // click on the activity button
    await testUtils.dom.click($record.find('.o_activity_btn'));
    assert.strictEqual(rpcCount, 1, 'no RPC should have been done as there is no activity');
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    // fixme: it would be nice to be able to test the scheduling of a new activity, but not
    // possible for now as we can't mock a fields_view_get (required by the do_action)
    kanban.destroy();
});

QUnit.skip('kanban activity widget with an activity', async function (assert) {
    assert.expect(14);

    this.data.partner.records[0].activity_ids = [1, 2];
    this.data.partner.records[0].activity_state = 'today';
    this.data.partner.records[0].activity_exception_decoration = 'warning';
    this.data.partner.records[0].activity_exception_icon = 'fa-warning';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 1,
    },{
        id: 2,
        display_name: "An exception activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 4,
    }];
    var rpcCount = 0;
    var kanban = await createView({
        View: KanbanView,
        model: 'partner',
        data: this.data,
        arch: '<kanban>' +
                    '<field name="activity_state"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="activity_ids" widget="kanban_activity"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        mockRPC: function (route, args) {
            rpcCount++;
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                var current_ids = this.data.partner.records[0].activity_ids;
                var done_ids = args.args[0];
                this.data.partner.records[0].activity_ids = _.difference(current_ids, done_ids);
                this.data.partner.records[0].activity_exception_decoration = false;
                this.data.partner.records[0].activity_state = false;
                return Promise.resolve();
            }
            return this._super(route, args);
        },
        session: {uid:2},
    });

    var $record = kanban.$('.o_kanban_record').first();
    assert.ok($record.find('.o_mail_activity .o_activity_color_today').length,
        "activity widget should have been rendered correctly");
    assert.strictEqual(rpcCount, 1, '1 RPC (search_read) should have been done');

    // Check exception activity icon fa-warning
    assert.hasClass($record.find('.o_activity_btn span'), "fa-warning", "should display correct exception activity icon");
    // click on the activity button
    await testUtils.dom.click($record.find('.o_activity_btn'));
    assert.strictEqual(rpcCount, 2, 'a read should have been done to fetch the activity details');
    assert.strictEqual($record.find('.o_activity_title').length, 2, "should have two activity scheduled");
    var label = $record.find('.o_activity_log .o_activity_color_today');
    assert.strictEqual(label.find('strong').text(), "Today", "should display the correct label");
    assert.strictEqual(label.find('.badge-warning').text(), "2", "should display the correct count");

    // click on the activity button to close the dropdown
    await testUtils.dom.click($record.find('.o_activity_btn'));
    assert.strictEqual(rpcCount, 2, 'no RPC should be done when closing the dropdown');

    // click on the activity button to re-open dropdown
    await testUtils.dom.click($record.find('.o_activity_btn'));
    assert.strictEqual(rpcCount, 3, 'should have reloaded the activities');

    // mark exception activity as done
    await testUtils.dom.click($record.find('.o_mark_as_done:eq(1)'));
    await testUtils.dom.click($record.find('.o_activity_popover_done'));
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset

    // check activity icon replaced with fa-clock
    assert.hasClass($record.find('.o_activity_btn span'), "fa-clock-o", "should display correct activity icon");

    // mark activity as done
    await testUtils.dom.click($record.find('.o_mark_as_done'));
    await testUtils.dom.click($record.find('.o_activity_popover_done'));
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset
    assert.strictEqual(rpcCount, 8, 'should have done an RPC to mark activity as done, and a read');
    assert.ok($record.find('.o_mail_activity .o_activity_color_default:not(.o_activity_color_today)').length,
        "activity widget should have been updated correctly");
    assert.strictEqual($record.find('.o_mail_activity.show').length, 1,
        "dropdown should remain open when marking an activity as done");
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    kanban.destroy();
});

QUnit.skip('kanban activity widget popover test', async function (assert) {
    assert.expect(3);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 1,
    }];
    var rpcCount = 0;
    var kanban = await createView({
        View: KanbanView,
        model: 'partner',
        data: this.data,
        arch: '<kanban>' +
                    '<field name="activity_state"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="activity_ids" widget="kanban_activity"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                rpcCount++;

                var current_ids = this.data.partner.records[0].activity_ids;
                var done_ids = args.args[0];
                this.data.partner.records[0].activity_ids = _.difference(current_ids, done_ids);
                this.data.partner.records[0].activity_state = false;
                return Promise.resolve();
            }
            return this._super(route, args);
        },
    });

    var $record = kanban.$('.o_kanban_record').first();

    await testUtils.dom.click($record.find('.o_activity_btn'));

    // Click on button and see popover no RPC call
    await testUtils.dom.click($record.find('.o_mark_as_done'));
    assert.equal(rpcCount, 0, "");
    // Click on discard no RPC call
    await testUtils.dom.click($record.find('.o_activity_popover_discard'));
    assert.equal(rpcCount, 0, "");
    // Click on button and then on done and schedule next
    // RPC call
    await testUtils.dom.click($record.find('.o_activity_popover_done_next'));
    assert.equal(rpcCount, 1, "");

    kanban.destroy();
});

QUnit.skip('list activity exception widget with activity', async function (assert) {
    assert.expect(3);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records.push({
        id: 3,
        message_attachment_count: 3,
        display_name: "second partner",
        foo: "Tommy",
        message_follower_ids: [],
        message_ids: [],
        activity_ids: [2],
        activity_exception_decoration: 'warning',
        activity_exception_icon: 'fa-warning',
    });
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 1,
    },{
        id: 2,
        display_name: "An exception activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 4,
    }];

    var list = await createView({
        View: ListView,
        model: 'partner',
        data: this.data,
        arch: '<tree>' +
                '<field name="foo"/>'+
                '<field name="activity_exception_decoration" widget="activity_exception"/> ' +
            '</tree>',
    });

    assert.containsN(list, '.o_data_row', 2, "should have two records");
    assert.doesNotHaveClass(list.$('.o_data_row:eq(0) .o_activity_exception_cell div'), 'fa-warning',
        "there is no any exception activity on record");
    assert.hasClass(list.$('.o_data_row:eq(1) .o_activity_exception_cell div'), 'fa-warning',
        "there is an exception on a record");

    list.destroy();
});

QUnit.skip('form activity widget: read RPCs', async function (assert) {
    // Records of model 'mail.activity' may be updated in business flows (e.g.
    // the date of a 'Meeting' activity is updated when the associated meeting
    // is dragged&dropped in the Calendar view). Because of that, the activities
    // must be reloaded when the form is reloaded (the widget can't keep an
    // internal cache).
    assert.expect(6);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 2,
    }];

    var nbReads = 0;
    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'activity_format' && args.model === 'mail.activity') {
                nbReads++;
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(nbReads, 1, "should have read the activities");
    assert.containsOnce(form, '.o_mail_activity .o_thread_message',
        "should display an activity");
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message .o_activity_date').text(),
        'Today', "the activity should be today");

    await testUtils.form.clickEdit(form);
    await testUtils.form.clickSave(form);

    assert.strictEqual(nbReads, 1, "should not have re-read the activities");

    // simulate a date change, and a reload of the form view
    var tomorrow = moment().add(1, 'day').format("YYYY-MM-DD");
    this.data['mail.activity'].records[0].date_deadline = tomorrow;
    await form.reload();

    assert.strictEqual(nbReads, 2, "should have re-read the activities");
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message .o_activity_date').text(),
        'Tomorrow', "the activity should be tomorrow");

    form.destroy();
});

QUnit.skip('form activity widget on a new record', async function (assert) {
    assert.expect(0);

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'mail.activity') {
                throw new Error("should not do a read on mail.activity");
            }
            return this._super.apply(this, arguments);
        },
    });

    form.destroy();
});

QUnit.skip('form activity widget with another x2many field in view', async function (assert) {
    assert.expect(1);

    this.data.partner.fields.m2m = {string: "M2M", type: 'many2many', relation: 'partner'};

    this.data.partner.records[0].m2m = [2];
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 2,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<field name="m2m" widget="many2many_tags"/>' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
    });

    assert.containsOnce(form, '.o_mail_activity .o_thread_message',
        "should display an activity");

    form.destroy();
});

QUnit.skip('form activity widget: schedule next activity', async function (assert) {
    assert.expect(4);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 2,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                assert.ok(_.isEqual(args.args[0], [1]), "should call 'action_feedback_schedule_next' for id 1");
                assert.strictEqual(args.kwargs.feedback, 'everything is ok',
                    "the feedback should be sent correctly");
                return Promise.resolve('test_result');
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (event) {
                assert.strictEqual(event.data.action,'test_result' , "should do a do_action with correct parameters");
                event.data.options.on_close();
            },
        },
    });
    //Schedule next activity
    await testUtils.dom.click(form.$('.o_mail_activity .o_mark_as_done[data-activity-id=1]'));
    assert.containsOnce(form, '.o_mail_activity_feedback.popover',
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    await testUtils.dom.click(form.$('.o_activity_popover_done_next'));
    form.destroy();
});

QUnit.skip('form activity widget: do not close activity popover on click', async function (assert) {
    assert.expect(3);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 2,
    }];

    const form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: `<form string="Partners">
                <sheet>
                    <field name="foo"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids" widget="mail_thread"/>
                    <field name="activity_ids" widget="mail_activity"/>
                </div>
            </form>`,
        res_id: 2,
        mockRPC(route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback_schedule_next') {
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action(ev) {
                ev.data.options.on_close();
            },
        },
    });

    //Schedule next activity
    await testUtils.dom.click(form.$('.o_mail_activity .o_mark_as_done[data-activity-id=1]'));

    for (let i = 0; i < 2; i++) {
        // click twice in feedback area
        await testUtils.dom.click(form.$('.o_mail_activity_feedback.popover textarea'));
        const $popover = form.$('.o_mail_activity_feedback.popover');
        const $PopoverInDom = form.$(`#${$popover.attr('id')}`);
        assert.isVisible(
            $PopoverInDom,
            "the feedback popover should still be visible on click");
    }
    await concurrency.delay(250); // wait for popover transition
    const $popover = form.$('.o_mail_activity_feedback.popover');
    if (!$popover) {
        throw new Error("popover should be in DOM");
    }
    const $PopoverInDom = form.$(`#${$popover.attr('id')}`);
    assert.isVisible(
        $PopoverInDom,
        "the feedback popover should still be visible on click");

    form.destroy();
});

QUnit.skip('form activity widget: edit next activity', async function (assert) {
    assert.expect(3);
    var self = this;
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 2,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        intercepts: {
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    context: {
                      default_res_id: 2,
                      default_res_model: "partner"
                    },
                    name: "Schedule Activity",
                    res_id: 1,
                    res_model: "mail.activity",
                    target: "new",
                    type: "ir.actions.act_window",
                    view_mode: "form",
                    views: [
                      [
                        false,
                        "form"
                      ]
                    ]
                  },
                  "should do a do_action with correct parameters");
                self.data['mail.activity'].records[0].activity_type_id = 1;
                event.data.options.on_close();
            },
        },
    });
    assert.strictEqual(form.$('.o_mail_activity .o_mail_info strong:eq(1)').text(), " Type 2",
        "Initial type should be Type 2");
    await testUtils.dom.click(form.$('.o_mail_activity .o_edit_activity[data-activity-id=1]'));
    assert.strictEqual(form.$('.o_mail_activity .o_mail_info strong:eq(1)').text(), " Type 1",
        "After edit type should be Type 1");
    form.destroy();
});

QUnit.skip('form activity widget: clic mail template', async function (assert) {
    assert.expect(4);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        activity_type_id: 2,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'activity_format') {
                return this._super.apply(this, arguments).then(function (res) {
                    res[0].mail_template_ids = [{ id: 100, name: 'Temp1' }];
                    return res;
                });
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (ev) {
                assert.deepEqual(ev.data.action, {
                        name: _t('Compose Email'),
                        type: 'ir.actions.act_window',
                        res_model: 'mail.compose.message',
                        views: [[false, 'form']],
                        target: 'new',
                        context: {
                            default_res_id: 2,
                            default_model: 'partner',
                            default_use_template: true,
                            default_template_id: 100,
                            force_email: true,
                        },
                    },
                    "should do a do_action with correct parameters");
                    ev.data.options.on_close();
            },
        },
    });
    assert.containsOnce(form, '.o_mail_activity .o_thread_message',
        "we should have one activity");
    assert.containsOnce(form, '.o_activity_template_preview',
        "Activity should contains one mail template");
    await testUtils.dom.click(form.$('.o_activity_template_preview[data-template-id=100]'));
    assert.containsOnce(form, '.o_mail_activity .o_thread_message',
        "activity should still be there");
    form.destroy();
});

QUnit.skip('form activity widget: schedule activity does not discard changes', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'write') {
                assert.deepEqual(args.args[1], {foo: 'new value'},
                    "should correctly save the change");
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            do_action: function (event) {
                event.data.options.on_close();
            },
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    // update value of foo field
    await testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'new value');

    // schedule an activity (this triggers a do_action)
    await testUtils.dom.click(form.$('.o_chatter_button_schedule_activity'));

    // save the record
    await testUtils.form.clickSave(form);

    form.destroy();
});

QUnit.skip('form activity widget: mark as done and remove', async function (assert) {
    assert.expect(15);

    var self = this;

    var nbReads = 0;
    this.data.partner.records[0].activity_ids = [1, 2];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 1,
    }, {
        id: 2,
        display_name: "A second activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        can_write: true,
        state: "today",
        user_id: 2,
        create_uid: 2,
        activity_type_id: 1,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.activity/unlink') {
                assert.ok(_.isEqual(args.args[0], [1]), "should call 'unlink' for id 1");
            } else if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.ok(_.isEqual(args.args[0], [2]), "should call 'action_feedback' for id 2");
                assert.strictEqual(args.kwargs.feedback, 'everything is ok',
                    "the feedback should be sent correctly");
                // should generate a message and unlink the activity
                self.data.partner.records[0].message_ids = [1];
                this.data['mail.message'].records.push({
                    attachment_ids: [],
                    author_id: ["1", "John Doe"],
                    body: "The activity has been done",
                    date: "2016-12-20 09:35:40",
                    id: 1,
                    is_note: true,
                    is_discussion: false,
                    model: 'partner',
                    res_id: 2,
                });
                route = '/web/dataset/call_kw/mail.activity/unlink';
                args.method = 'unlink';
            } else if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read
                    assert.strictEqual(args.args[1].length, 5, 'should read all fiels the first time');
                } else if (nbReads === 2) { // second read: after the unlink
                    assert.ok(_.isEqual(args.args[1], ['activity_ids', 'display_name']),
                        'should only read the activities (+ display_name) after an unlink');
                } else { // third read: after marking an activity done
                    assert.ok(_.isEqual(args.args[1], ['activity_ids', 'message_ids', 'display_name']),
                        'should read the activities and messages (+ display_name) after marking an activity done');
                }
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.containsN(form, '.o_mail_activity .o_thread_message', 2,
        "there should be two activities");

    // remove activity 1
    await testUtils.dom.click(form.$('.o_mail_activity .o_unlink_activity[data-activity-id=1]'));
    assert.containsOnce(form, '.o_mail_activity .o_thread_message',
        "there should be one remaining activity");
    assert.ok(!form.$('.o_mail_activity .o_unlink_activity[data-activity-id=1]').length,
        "activity 1 should have been removed");

    // mark activity done
    assert.ok(!form.$('.o_mail_thread .o_thread_message').length,
        "there should be no chatter message");
    await testUtils.dom.click(form.$('.o_mail_activity .o_mark_as_done[data-activity-id=2]'));
    assert.containsOnce(form, '.o_mail_activity_feedback.popover',
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    await testUtils.dom.click(form.$('.o_activity_popover_done'));
    assert.containsNone(form, '.o_mail_activity_feedback.popover')
    assert.ok(!form.$('.o_mail_activity .o_thread_message').length,
        "there should be no more activity");
    assert.containsOnce(form, '.o_mail_thread .o_thread_message',
        "a chatter message should have been generated");
    assert.strictEqual(form.$('.o_thread_message:contains(The activity has been done)').length, 1,
        "the message's body should be correct");
    form.destroy();
});

QUnit.skip('followers widget: follow/unfollow, edit subtypes', async function (assert) {
    assert.expect(14);

    var resID = 2;
    var partnerID = 2;
    var followers = [];
    var nbReads = 0;
    var subtypes = [
        {id: 1, name: "First subtype", followed: true},
        {id: 2, name: "Second subtype", followed: true},
        {id: 3, name: "Third subtype", followed: false},
    ];
    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        res_id: resID,
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/partner/message_subscribe') {
                assert.strictEqual(args.args[0][0], resID, 'should call route for correct record');
                assert.ok(_.isEqual(args.kwargs.partner_ids, [partnerID]),
                    'should call route for correct partner');
                if (args.kwargs.subtype_ids) {
                    // edit subtypes
                    assert.ok(_.isEqual(args.kwargs.subtype_ids, [1]),
                        'should call route with the correct subtypes');
                    _.each(subtypes, function (subtype) {
                        subtype.followed = _.contains(args.kwargs.subtype_ids, subtype.id);
                    });
                } else {
                    // follow
                    this.data.partner.records[0].message_follower_ids = [1];
                    followers.push({
                        id: 1,
                        name: "Admin",
                        email: "admin@example.com",
                        partner_id: partnerID,
                        channel_id: null,
                        is_active: true
                    });
                }
                return Promise.resolve(true);
            }
            if (route === '/mail/read_followers') {
                return Promise.resolve({
                    followers: followers,
                    subtypes: subtypes,
                    // caution, subtype will only be returned if current user is in args follower list
                });
            }
            if (route === '/web/dataset/call_kw/partner/message_unsubscribe') {
                assert.strictEqual(args.args[0][0], resID, 'should call route for correct record');
                assert.ok(_.isEqual(args.args[1], [partnerID]), 'should call route for correct partner');
                this.data.partner.records[0].message_follower_ids = [];
                followers = [];
                return Promise.resolve(true);
            }
            if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read: should read all fields
                    assert.ok(args.args[1].includes('foo'), 'should read "foo"');
                    assert.ok(args.args[1].includes('message_follower_ids'), 'should read "message_follower_ids"');
                    assert.ok(args.args[1].includes('display_name'), 'should read "display_name"');
                } else { // three next reads: only read 'message_follower_ids' field
                    assert.deepEqual(args.args[1], ['message_follower_ids', 'display_name'],
                        'should only read "message_follower_ids" and "display_name"');
                }
            }
            return this._super.apply(this, arguments);
        },
        session: {partner_id: partnerID},
    });

    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');
    assert.ok(form.$('.o_followers_follow_button.o_followers_notfollow').length,
        'should display the "Follow" button');

    // click to follow the document
    await testUtils.dom.click(form.$('.o_followers_follow_button'));
    assert.strictEqual(form.$('.o_followers_count').text(), "1", 'should have one follower');
    assert.ok(form.$('.o_followers_follow_button.o_followers_following').length,
        'should display the "Following/Unfollow" button');
    assert.containsOnce(form, '.o_followers_list .o_partner',
        "there should be one follower in the follower dropdown");

    // click to unfollow
    await testUtils.dom.click(form.$('.o_followers_follow_button'));
    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');
    assert.ok(form.$('.o_followers_follow_button.o_followers_notfollow').length,
        'should display the "Follow" button');

    form.destroy();
});

QUnit.skip('followers widget: follow/unfollow confirmation dialog', async function (assert) {
    assert.expect(5);

    this.data.partner.records[0].message_follower_ids = [1, 2];
    var resID = 2;
    var partnerID = 2;
    var followers = [{
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        partner_id: partnerID,
        channel_id: null,
        is_active: true   
    }, {
        id: 2,
        name: "Demo",
        email: "demo@example.com",
        partner_id: 1,
        channel_id: null,
        is_active: true
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        res_id: resID,

        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/partner/message_unsubscribe') {
                this.data.partner.records[0].message_follower_ids.shift();
                followers.shift();
                return Promise.resolve(true);
            }
            if (route === '/mail/read_followers') {
                return Promise.resolve({
                    followers: followers,
                });
            }
            return this._super.apply(this, arguments);
        },
        session: {partner_id: partnerID},
    });

    assert.strictEqual(form.$('.o_followers_count').text(), "2", 'should have 2 followers');
    // click to unfollow current user
    await testUtils.dom.click(form.$('.o_followers_follow_button'));
    assert.containsNone($, '.modal', 'a confirm modal should not be opened');
    assert.strictEqual(form.$('.o_followers_count').text(), "1", 'should have 1 follower');

    await testUtils.dom.click(form.$('.o_followers_title_box [data-toggle="dropdown"]'));
    // remove demo user from followers
    await testUtils.dom.click(form.$('.o_remove_follower'));
    assert.containsOnce($, '.modal', 'a confirm modal should be opened');
    await testUtils.dom.click($('.modal .modal-footer .btn-primary'));
    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');

    form.destroy();
});

QUnit.skip('followers widget: do not display follower duplications', async function (assert) {
    assert.expect(2);

    this.data.partner.records[0].message_follower_ids = [1];
    var resID = 2;
    var partnerID = 1;
    var followers = [{
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        partner_id: partnerID,
        channel_id: null,
        is_active: true   
    }];
    var def;
    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form>' +
                '<sheet></sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/mail/read_followers') {
                return Promise.resolve(def).then(function () {
                    return {
                        followers: _.filter(followers, function (follower) {
                            return _.contains(args.follower_ids, follower.id);
                        }),
                        subtypes: [],
                    };
                });
            }
            return this._super.apply(this, arguments);
        },
        res_id: resID,
        session: {partner_id: partnerID},
    });


    followers.push({
        id: 2,
        name: "A follower",
        email: "follower@example.com",
        res_id: resID,
        partner_id: 555,
        channel_id: null,
        is_active: true
    });
    this.data.partner.records[0].message_follower_ids.push(2);

    // simulate concurrent calls to read_followers and check that those followers
    // are not added twice in the dropdown
    def = testUtils.makeTestPromise();
    form.reload();
    form.reload();
    await def.resolve();
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_followers_count').text(), '2',
        "should have 2 followers");
    assert.containsN(form, '.o_followers_list .o_partner', 2,
        "there should be 2 followers in the follower dropdown");

    form.destroy();
});

QUnit.skip('followers widget: display inactive followers with a different style', async function (assert) {
    assert.expect(6);

    this.data.partner.records[0].message_follower_ids = [1,2,3];

    var followers = [{
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        partner_id: 101,
        channel_id: false,
        is_active: true,
    },{
        id: 2,
        name: "Active_partner",
        email: "active_partner@example.com",
        partner_id: 102,
        channel_id: false,
        is_active: true,
    },{
        id: 3,
        name: "Inactive_partner",
        email: "inactive_partner@example.com",
        partner_id: 103,
        channel_id: false,
        is_active: false,
    }];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/mail/read_followers') {
                return Promise.resolve({
                    followers: _.filter(followers, function (follower) {
                        return _.contains(args.follower_ids, follower.id);
                    }),
                });
            }
            return this._super.apply(this, arguments);
        },
        res_id: 2,
    });

    assert.doesNotHaveClass(form.$(".o_partner:has(a[data-oe-id='101'])"), 'o_inactive', 'Partner should be active');
    assert.hasAttrValue(form.$(".o_partner:has(a[data-oe-id='101']) > a"),'title','Admin');
    assert.doesNotHaveClass(form.$(".o_partner:has(a[data-oe-id='102'])"), 'o_inactive', 'Partner should be active');
    assert.hasAttrValue(form.$(".o_partner:has(a[data-oe-id='102']) > a"),'title','Active_partner');
    assert.hasClass(form.$(".o_partner:has(a[data-oe-id='103'])"), 'o_inactive', 'Partner should be inactive');
    assert.hasAttrValue(form.$(".o_partner:has(a[data-oe-id='103']) > a"),'title','Inactive_partner \n(inactive)');

    form.destroy();
});

QUnit.skip('chatter: suggested partner auto-follow on message post', async function (assert) {
    // need post_refresh 'recipient' to auto-follow suggested recipients
    // whose checkbox is checked.
    assert.expect(20);

    var self = this;
    this.data.partner.records[0].message_follower_ids = [1];
    this.data.partner.records[0].message_ids = [1];
    this.data['mail.message'].records = [{
        author_id: ["1", "John Doe"],
        body: "A message",
        date: "2016-12-20 09:35:40",
        id: 1,
        is_note: false,
        is_discussion: true,
        is_notification: false,
        model: 'partner',
        res_id: 2,
    }];

    var followers = [];
    followers.push({
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        partner_id: 5,
    });

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                    '<field name="message_ids" widget="mail_thread" options="{\'post_refresh\': \'recipients\'}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/mail/get_suggested_recipients') {
                return Promise.resolve({2: [
                        [
                            8,
                            'DemoUser <demo-user@example.com>',
                            'Customer Email',
                        ],
                    ]
                });
            }
            if (args.method === 'message_post') {
                assert.ok(args.kwargs.context.mail_post_autofollow,
                    "should autofollow checked suggested partners when posting message");
                assert.deepEqual(args.kwargs.partner_ids, [8],
                    "should have provided Demo User to auto-follow chatter on message_post");

                // add demo user in followers
                self.data.partner.records[0].message_follower_ids.push(2);
                followers.push({
                    id: 2,
                    name: "Demo User",
                    email: "demo-user@example.com",
                    partner_id: 8,
                    channel_id: false,
                    is_active: true
                });

                // post a legit message so that it does not crashes
                var lastMessageData = _.max(this.data['mail.message'].records, function (messageData) {
                    return messageData.id;
                });
                var messageID = lastMessageData.id + 1;
                this.data['mail.message'].records.push({
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    date: "2016-12-20 10:35:40",
                    id: messageID,
                    is_note: args.kwargs.subtype_xmlid === 'mail.mt_note',
                    is_discussion: args.kwargs.subtype_xmlid === 'mail.mt_comment',
                    is_notification: false,
                    model: 'partner',
                    res_id: 2,
                });
                return Promise.resolve(messageID);
            }
            if (route === '/mail/read_followers') {
                return Promise.resolve({
                    followers: followers,
                });
            }
            return this._super(route, args);
        },
        session: {},
    });

    assert.containsOnce(form, '.o_thread_message', "thread should contain one message");
    assert.ok(form.$('.o_thread_message:first().o_mail_discussion').length,
        "the message should be a discussion");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('A message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('John Doe') >= 0,
        "the message's author should be correct");
    assert.containsOnce(form, '.o_followers',
        "should display follower widget");
    assert.strictEqual(form.$('.o_followers_count').text(), "1",
        "should have a single follower (widget counter)");
    assert.containsOnce(form, '.o_followers_list > div.o_partner',
        "should have a single follower (listed partners)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a').text().trim(), "Admin",
        "should have 'Admin' as follower");

    // open composer
    await testUtils.dom.click(form.$('.o_chatter_button_new_message'));
    assert.isVisible($('.oe_chatter .o_thread_composer'), "chatter should be opened");
    assert.strictEqual($('.o_composer_suggested_partners').length, 1,
        "should display suggested partners");
    assert.strictEqual($('.o_composer_suggested_partners > div').length, 1,
        "should display 1 suggested partner");
    assert.ok($('.o_composer_suggested_partners input').is(':checked'),
        "should have checkbox that is checked by default");
    assert.strictEqual($('.o_composer_suggested_partners input').data('fullname'),
        "DemoUser <demo-user@example.com>",
        "should have partner suggestion with correct fullname (data)");
    assert.strictEqual($('.o_composer_suggested_partners label').text().replace(/\s+/g, ''),
        "DemoUser(demo-user@example.com)",
        "should have partner suggestion with correct fullname (rendering)");

    // send message
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    await testUtils.dom.click(form.$('.oe_chatter .o_composer_button_send'));

    assert.strictEqual(form.$('.o_followers_count').text(), "2",
        "should have a two followers (widget counter)");
    assert.containsN(form, '.o_followers_list > div.o_partner', 2,
        "should have two followers (listed partners)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a[data-oe-id="5"]').text().trim(),
        "Admin",
        "should have 'Admin' as follower");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a[data-oe-id="8"]').text().trim(),
        "Demo User",
        "should have 'Demo User' as follower");

    //cleanup
    form.destroy();
});

QUnit.skip('chatter: mention prefetched partners (followers & employees)', async function (assert) {
    // Note: employees are in prefeteched partner for mentions in chatter when
    // the module hr is installed.
    assert.expect(10);

    var followerSuggestions = [{
        id: 1,
        name: 'FollowerUser1',
        email: 'follower-user1@example.com',
    }, {
        id: 2,
        name: 'FollowerUser2',
        email: 'follower-user2@example.com',
    }];

    var nonFollowerSuggestions = [{
        id: 3,
        name: 'NonFollowerUser1',
        email: 'non-follower-user1@example.com',
    }, {
        id: 4,
        name: 'NonFollowerUser2',
        email: 'non-follower-user2@example.com',
    }];

    // link followers
    this.data.partner.records[0].message_follower_ids = [10, 20];

    // prefetched partners
    this.data.initMessaging = {
        mention_partner_suggestions: [followerSuggestions.concat(nonFollowerSuggestions)],
    };

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_follower_ids" widget="mail_followers"/>' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === '/mail/read_followers') {
                return Promise.resolve({
                    followers: [{
                        id: 10,
                        name: 'FollowerUser1',
                        email: 'follower-user1@example.com',
                        partner_id: 1,
                        channel_id: null,
                        is_active: true
                    }, {
                        id: 20,
                        name: 'FollowerUser2',
                        email: 'follower-user2@example.com',
                        partner_id: 2,
                        channel_id: null,
                        is_active: true,
                    }],
                    subtypes: [],
                });
            }
            if (route === '/mail/get_suggested_recipients') {
                return Promise.resolve({2: []});
            }
            if (args.method === 'get_mention_suggestions') {
                throw new Error('should not fetch partners for mentions');
            }
            return this._super(route, args);
        },
        session: {},
    });

    assert.strictEqual(form.$('.o_followers_count').text(), '2',
        "should have two followers of this document");
    assert.strictEqual(form.$('.o_followers_list > .o_partner').text().replace(/\s+/g, ''),
        'FollowerUser1FollowerUser2',
        "should have correct follower names");
    assert.strictEqual(form.$('.o_composer_mention_dropdown').length, 0,
        "should not show the mention suggestion dropdown");

    await testUtils.dom.click(form.$('.o_chatter_button_new_message'));
    var $input = form.$('.oe_chatter .o_composer_text_field:first()');
    $input.val('@');
    // the cursor position must be set for the mention manager to detect that we are mentionning
    $input[0].selectionStart = 1;
    $input[0].selectionEnd = 1;
    $input.trigger('keyup');
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_composer_mention_dropdown').length, 1,
        "should show the mention suggestion dropdown");

    assert.strictEqual(form.$('.o_mention_proposition').length, 4,
        "should show 4 mention suggestions");
    assert.strictEqual(form.$('.o_mention_proposition').eq(0).text().replace(/\s+/g, ''),
        "FollowerUser1(follower-user1@example.com)",
        "should display correct 1st mention suggestion");
    assert.strictEqual(form.$('.o_mention_proposition').eq(1).text().replace(/\s+/g, ''),
        "FollowerUser2(follower-user2@example.com)",
        "should display correct 2nd mention suggestion");
    assert.ok(form.$('.o_mention_proposition').eq(1).next().hasClass('dropdown-divider'),
        "should have a mention separator after last follower mention suggestion");
    assert.strictEqual(form.$('.o_mention_proposition').eq(2).text().replace(/\s+/g, ''),
        "NonFollowerUser1(non-follower-user1@example.com)",
        "should display correct 3rd mention suggestion");
    assert.strictEqual(form.$('.o_mention_proposition').eq(3).text().replace(/\s+/g, ''),
        "NonFollowerUser2(non-follower-user2@example.com)",
        "should display correct 4th mention suggestion");

    //cleanup
    form.destroy();
});

QUnit.skip('chatter: display suggested partners only once', async function (assert) {
    assert.expect(3);

    let isMessageSent = false;

    const form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="foo"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids" widget="mail_followers"/>
                    <field name="message_ids" widget="mail_thread" options="{'display_log_button': True}"/>
                </div>
            </form>`,
        res_id: 2,
        async mockRPC(route, args) {
            if (route === '/mail/read_followers') {
                return {
                    followers: [],
                    subtypes: [],
                };
            }
            if (route === '/mail/get_suggested_recipients') {
                if (isMessageSent) {
                    return {
                        2: [],
                    };
                }
                return {
                    2: [[2, "Jack <jack@example.com>", "Partner Profile"]],
                };
            }
            if (args.method === 'message_post') {
                isMessageSent = true;
                return 57923;
            }
            if (args.method === 'message_format') {
                return [{
                    author_id: ["42", "Me"],
                    model: 'partner',
                }];
            }
            return this._super(route, args);
        },
        session: {},
    });

    await testUtils.dom.click(form.$('.o_chatter_button_new_message'));
    const $input = form.$('.oe_chatter .o_composer_text_field:first()');
    assert.containsOnce(
        form,
        'div.o_composer_suggested_partners input',
        "should show one suggested recipient");
    assert.strictEqual(
        form.$('div.o_composer_suggested_partners label').text().replace(/\s+/g, ''),
        "Jack(jack@example.com)",
        "should have the correct label");

    $input.val("BBQ and beers tonight! Are you in?");
    await testUtils.dom.click(form.$('.o_composer_button_send'));
    // Open composer for new message
    await testUtils.dom.click(form.$('.o_chatter_button_new_message'));
    assert.containsNone(
        form,
        'div.o_composer_suggested_partners input',
        "should no longer show the suggested recipient");

    form.destroy();
});

QUnit.skip('chatter: suggested recipients reflect saved changes', async function (assert) {
    assert.expect(6);

    this.data.partner.records[0].foo = "Marc";

    let suggestedRecipients = { 2: [[2, "Marc"]] };

    const form = await createView({
        View: FormView,
        model: 'partner',
        res_id: 2,
        data: this.data,
        services: this.services,
        arch: `
            <form string="Partners">
                <sheet>
                    <field name="foo"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids" widget="mail_thread"/>
                </div>
            </form>`,
        viewOptions: { mode: 'edit' },
        async mockRPC(route, args) {
            if (args.model === 'partner' && args.method === 'write') {
                const partnerName = args.args[1].foo;
                suggestedRecipients = { 2: [[2, partnerName]] };
            }
            if (route === '/mail/get_suggested_recipients') {
                assert.step('get_suggested_recipients');
                return Promise.resolve(suggestedRecipients);
            }
            return this._super(route, args);
        },
    });

    await testUtils.dom.click(form.$('.o_chatter_button_new_message'));
    assert.strictEqual(
        form.$('div.o_composer_suggested_partners label').text().replace(/\s+/g, ''),
        "Marc",
        "should have the correct original recipient name");
    assert.verifySteps(['get_suggested_recipients'],
        'get_suggested_recipients route should be called');

    await testUtils.fields.editInput(form.$('.o_field_char'), 'Bob');
    await testUtils.dom.click(form.$('.o_form_button_save'));
    assert.verifySteps(['get_suggested_recipients'],
        'get_suggested_recipients route should be called');
    assert.strictEqual(
        form.$('div.o_composer_suggested_partners label').text().replace(/\s+/g, ''),
        "Bob",
        "should have the correct modified recipient name");

    form.destroy();
});

QUnit.module('FieldMany2ManyTagsEmail', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    timmy: [],
                }],
            },
            partner_type: {
                fields: {
                    name: {string: "Partner Type", type: "char"},
                    email: {string: "Email", type: "char"},
                },
                records: [
                    {id: 12, display_name: "gold", email: 'coucou@petite.perruche'},
                    {id: 14, display_name: "silver", email: ''},
                ]
            },
        };
    },
});

QUnit.test('fieldmany2many tags email', function (assert) {
    assert.expect(13);
    var done = assert.async();

    this.data.partner.records[0].timmy = [12, 14];

    // the modals need to be closed before the form view rendering
    createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        res_id: 1,
        arch:'<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method ==='read' && args.model === 'partner_type') {
                assert.step(JSON.stringify(args.args[0]));
                assert.deepEqual(args.args[1] , ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    }).then(async function (form) {
        // should read it 3 times (1 with the form view, one with the form dialog and one after save)
        assert.verifySteps(['[12,14]', '[14]', '[14]']);
        await testUtils.nextTick();
        assert.containsN(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0', 2,
            "two tags should be present");
        var firstTag = form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').first();
        assert.strictEqual(firstTag.find('.o_badge_text').text(), "gold",
            "tag should only show display_name");
        assert.hasAttrValue(firstTag.find('.o_badge_text'), 'title', "coucou@petite.perruche",
            "tag should show email address on mouse hover");
        form.destroy();
        done();
    });
    testUtils.nextTick().then(function() {
        assert.strictEqual($('.modal-body.o_act_window').length, 1,
            "there should be one modal opened to edit the empty email");
        assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
            "the opened modal should be a form view dialog with the partner_type 14");
        assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
            "there should be an email field in the modal");

        // set the email and save the modal (will render the form view)
        testUtils.fields.editInput($('.modal-body.o_act_window input[name="email"]'), 'coucou@petite.perruche');
        testUtils.dom.click($('.modal-footer .btn-primary'));
    });

});

QUnit.test('fieldmany2many tags email (edition)', async function (assert) {
    assert.expect(15);

    this.data.partner.records[0].timmy = [12];

    var form = await createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        res_id: 1,
        arch:'<form string="Partners">' +
                '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags_email"/>' +
                '</sheet>' +
            '</form>',
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method ==='read' && args.model === 'partner_type') {
                assert.step(JSON.stringify(args.args[0]));
                assert.deepEqual(args.args[1] , ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    });

    assert.verifySteps(['[12]']);
    assert.containsOnce(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0',
        "should contain one tag");

    // add an other existing tag
    await testUtils.fields.many2one.clickOpenDropdown('timmy');
    await testUtils.fields.many2one.clickHighlightedItem('timmy');

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
        "the opened modal in edit mode should be a form view dialog with the partner_type 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will rerender the form view)
    await testUtils.fields.editInput($('.modal-body.o_act_window input[name="email"]'), 'coucou@petite.perruche');
    await testUtils.dom.click($('.modal-footer .btn-primary'));

    assert.containsN(form, '.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0', 2,
        "should contain the second tag");
    // should have read [14] three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps(['[14]', '[14]', '[14]']);

    form.destroy();
});

});
});
