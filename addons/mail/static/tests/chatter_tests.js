odoo.define('mail.chatter_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var concurrency = require('web.concurrency');
var core = require('web.core');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var createAsyncView = testUtils.createAsyncView;
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

        this.services = mailTestUtils.getMailServices();
        this.data = {
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
                    create_uid: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    create_user_id: { string: "Creator", type: "many2one", relation: 'partner' },
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
                    note : { string: "Note", type: "char" },
                },
            },
            'mail.activity.type': {
                fields: {
                    name: { string: "Name", type: "char" },
                },
                records: [
                    { id: 1, name: "Type 1" },
                    { id: 2, name: "Type 2" },
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
                    is_starred: {
                        string: "Starred",
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
                    datas_fname:{type:'char', string:"filename"},
                },
                records:[
                    {id:1, name:"name1", type:'url', mimetype:'image/png', datas_fname:'filename.jpg',
                     res_id: 7, res_model: 'partner'},
                    {id:2, name:"name2", type:'binary', mimetype:"application/x-msdos-program",
                     datas_fname:"file2.txt", res_id: 7, res_model: 'partner'},
                    {id:3, name:"name2", type:'binary', mimetype:"application/x-msdos-program",
                     datas_fname:"file2.txt", res_id: 5, res_model: 'partner'},
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

QUnit.test('basic rendering', function (assert) {
    assert.expect(9);

    var count = 0;
    var unwanted_read_count = 0;

    var form = createView({
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
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/web/dataset/call_kw/mail.followers/read') {
                unwanted_read_count++;
            }
            if (route === '/mail/read_followers') {
                count++;
                return $.when({
                    followers: [],
                    subtypes: [],
                });
            }
            return this._super(route, args);
        },
        res_id: 2,
    });

    assert.ok(form.$('.o_mail_activity').length, "there should be an activity widget");
    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_schedule_activity').length,
        "there should be a 'Schedule an activity' button in the chatter's topbar");
    assert.ok(form.$('.o_chatter_topbar .o_followers').length,
        "there should be a followers widget, moved inside the chatter's topbar");
    assert.ok(form.$('.o_chatter').length, "there should be a chatter widget");
    assert.ok(form.$('.o_mail_thread').length, "there should be a mail thread");
    assert.strictEqual(form.$('.o_chatter_button_attachment').length, 1, "should have one attachment button");
    assert.ok(!form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should not be available");

    form.$buttons.find('.o_form_button_edit').click();
    assert.strictEqual(count, 0, "should have done no read_followers rpc as there are no followers");
    assert.strictEqual(unwanted_read_count, 0, "followers should only be fetched with read_followers route");
    form.destroy();
});

QUnit.test('Activity Done keep feedback on blur', function (assert) {
    assert.expect(3);
    var done = assert.async();

    this.data['mail.activity'].records = [
        {activity_type_id: 1, id: 1, user_id: 2, state: 'today', note: 'But I\'m talkin\' about Shaft'},
    ];
    this.data.partner.records[0].activity_ids = [1];

    var shownDef = $.Deferred();
    var hiddenDef = $.Deferred();
    testUtils.patch(Activity, {
        _bindPopoverFocusout: function () {
            this._super.apply(this, arguments);
            shownDef.resolve();
        },
    });

    var form = createView({
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
    $popoverEl.click();

    shownDef.then(function () {
        // write a feedback and focusout
        var $feedbackPopover = $($popoverEl.data('bs.popover').tip);
        $feedbackPopover.find('#activity_feedback').val('John Shaft').focusout();

        hiddenDef.then(function () {
            shownDef = $.Deferred();

            // re-open popover
            $popoverEl.click();

            shownDef.then(function () {
                var $feedbackPopover = $($popoverEl.data('bs.popover').tip);
                assert.strictEqual($feedbackPopover.find('#activity_feedback').val(), 'John Shaft',
                    "feedback should have been kept");

                form.destroy();
                testUtils.unpatch(Activity);
                done();
            });
        });
    });
});

QUnit.test('attachmentBox basic rendering', function (assert) {
    assert.expect(11);
    this.data.partner.records.push({
        id: 7,
        display_name: "attachment_test",
    });

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                '</div>' +
            '</form>',
        res_id: 7,
    });
    var $button = form.$('.o_chatter_button_attachment');
    assert.strictEqual($button.length, 1, "should have one attachment button");
    $button.click();
    assert.strictEqual(form.$('.o_mail_chatter_attachments').length, 1,
        "attachment widget should exist after a first click on the button");
    assert.strictEqual(form.$('.o_attachment_image').length, 1, "there should be an image preview");
    assert.strictEqual(form.$('.o_attachments_previews').length, 1, "there should be a list of previews");
    assert.strictEqual(form.$('.o_attachments_list').length, 1, "there should be a list of non previewable attachments");
    assert.strictEqual(form.$('.o_attachment_title').text(), 'name1',
        "the image name should be correct");
    // since there are two elements "Download name2"; one "name" and the other "txt" as text content, the following test
    // asserts both at the same time.
    assert.strictEqual(form.$('a[title = "Download name2"]').text().trim(), 'name2txt',
        "the attachment name should be correct");
    assert.ok(form.$('.o_attachment_image').css('background-image').indexOf('/web/image/1/160x160/?crop=true') >= 0,
        "the attachment image URL should be correct");
    assert.strictEqual(form.$('.o_attachment_download').eq(0).attr('href'), '/web/content/1?download=true',
        "the download URL of name1 must be correct");
    assert.strictEqual(form.$('.o_attachment_download').eq(1).attr('href'), '/web/content/2?download=true',
        "the download URL of name2 must be correct");
    $button.click();
    assert.strictEqual(form.$('.o_mail_chatter_attachments').length, 0,
        "attachment widget should de destroyed after we reclick the button");
    form.destroy();
});

QUnit.test('chatter in create mode', function (assert) {
    assert.expect(9);

    var form = createView({
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
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
    });

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    // entering create mode
    form.$buttons.find('.o_form_button_create').click();
    assert.ok(form.$el.find('.o_form_view').hasClass('o_form_editable'),
        "we should be in create mode");
    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should still be displayed in create mode");

    // topbar buttons disabled in create mode (e.g. 'send message')
    assert.strictEqual(form.$('.o_chatter_topbar button:not(:disabled)').length, 0,
        "button should be disabled in create mode");

    // chatter containing a single message with 'Creating a record...'
    assert.strictEqual(form.$('.o_mail_thread').length, 1,
        "there should be a mail thread");
    assert.strictEqual(form.$('.o_thread_message').length, 1,
        "there should be a single thread message");
    assert.strictEqual(form.$('.o_thread_message_content').text().trim(),
        "Creating a new record...",
        "the content of the message should be 'Creating a new record...'");

    // getting out of create mode by saving
    form.$('.o_field_char').val('coucou').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should still be displayed after saving from create mode");

    // check if chatter buttons still work
    form.$('.o_chatter_button_new_message').click();
    assert.strictEqual(form.$('.o_thread_composer:visible').length, 1,
        "chatter should be opened");

    form.destroy();
});

QUnit.test('chatter rendering inside the sheet', function (assert) {
    assert.expect(5);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                    '<notebook>' +
                        '<page>' +
                            '<div class="oe_chatter">' +
                                '<field name="message_ids" widget="mail_thread"/>' +
                            '</div>' +
                        '</page>' +
                    '</notebook>' +
                '</sheet>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
    });

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    form.$buttons.find('.o_form_button_create').click();
    assert.ok(form.$el.find('.o_form_view').hasClass('o_form_editable'),
        "we should be in create mode");

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    form.$('.o_field_char').val('coucou').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    // check if chatter buttons still work
    form.$('.o_chatter_button_new_message').click();
    assert.strictEqual(form.$('.o_thread_composer:visible').length, 1,
        "chatter should be opened");

    form.destroy();
});

QUnit.test('kanban activity widget with no activity', function (assert) {
    assert.expect(4);

    var rpcCount = 0;
    var kanban = createView({
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
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 1, 'no RPC should have been done as there is no activity');
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    // fixme: it would be nice to be able to test the scheduling of a new activity, but not
    // possible for now as we can't mock a fields_view_get (required by the do_action)
    kanban.destroy();
});

QUnit.test('kanban activity widget with an activity', function (assert) {
    assert.expect(12);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 1,
    }];
    var rpcCount = 0;
    var kanban = createView({
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
                this.data.partner.records[0].activity_state = false;
                return $.when();
            }
            return this._super(route, args);
        },
        session: {uid:2},
    });

    var $record = kanban.$('.o_kanban_record').first();
    assert.ok($record.find('.o_mail_activity .o_activity_color_today').length,
        "activity widget should have been rendered correctly");
    assert.strictEqual(rpcCount, 1, '1 RPC (search_read) should have been done');

    // click on the activity button
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'a read should have been done to fetch the activity details');
    assert.strictEqual($record.find('.o_activity_title').length, 1, "should have an activity scheduled");
    var label = $record.find('.o_activity_log .o_activity_color_today');
    assert.strictEqual(label.find('strong').text(), "Today", "should display the correct label");
    assert.strictEqual(label.find('.badge-warning').text(), "1", "should display the correct count");

    // click on the activity button to close the dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'no RPC should be done when closing the dropdown');

    // click on the activity button to re-open dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 3, 'should have reloaded the activities');

    // mark activity as done
    $record.find('.o_mark_as_done').click();
    $record.find('.o_activity_popover_done').click();
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset
    assert.strictEqual(rpcCount, 5, 'should have done an RPC to mark activity as done, and a read');
    assert.ok($record.find('.o_mail_activity .o_activity_color_default:not(.o_activity_color_today)').length,
        "activity widget should have been updated correctly");
    assert.strictEqual($record.find('.o_mail_activity.show').length, 1,
        "dropdown should remain open when marking an activity as done");
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    kanban.destroy();
});

QUnit.test('kanban activity widget popover test', function (assert) {
    assert.expect(3);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 1,
    }];
    var rpcCount = 0;
    var kanban = createView({
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
                return $.when();
            }
            return this._super(route, args);
        },
    });

    var $record = kanban.$('.o_kanban_record').first();

    $record.find('.o_activity_btn').click();

    // Click on button and see popover no RPC call
    $record.find('.o_mark_as_done').click();
    assert.equal(rpcCount, 0, "");
    // Click on discard no RPC call
    $record.find('.o_activity_popover_discard').click();
    assert.equal(rpcCount, 0, "");
    // Click on button and then on done and schedule next
    // RPC call
    $record.find('.o_activity_popover_done_next').click();
    assert.equal(rpcCount, 1, "");

    kanban.destroy();
});

QUnit.test('chatter: post, receive and star messages', function (assert) {
    var done = assert.async();
    assert.expect(27);

    this.data.partner.records[0].message_ids = [1];
    this.data['mail.message'].records = [{
        author_id: ["1", "John Doe"],
        body: "A message",
        date: "2016-12-20 09:35:40",
        id: 1,
        is_note: false,
        is_discussion: true,
        is_notification: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];

    var getSuggestionsDef = $.Deferred();
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: []});
            }
            if (args.method === 'get_mention_suggestions') {
                getSuggestionsDef.resolve();
                return $.when([{email: "test@odoo.com", id: 1, name: "Test User"}]);
            }
            if (args.method === 'message_post') {
                var lastMessageData = _.max(this.data['mail.message'].records, function (messageData) {
                    return messageData.id;
                });
                var messageID = lastMessageData.id + 1;
                this.data['mail.message'].records.push({
                    attachment_ids: args.kwargs.attachment_ids,
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    date: "2016-12-20 10:35:40",
                    id: messageID,
                    is_note: args.kwargs.subtype === 'mail.mt_note',
                    is_discussion: args.kwargs.subtype === 'mail.mt_comment',
                    is_notification: false,
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                return $.when(messageID);
            }
            if (args.method === 'toggle_message_starred') {
                assert.ok(_.contains(args.args[0], 2),
                    "toggle_star_status should have been triggered for message 2 (twice)");
                var messageData = _.findWhere(
                    this.data['mail.message'].records,
                    { id: args.args[0][0] }
                );
                messageData.is_starred = !messageData.is_starred;
                // simulate notification received by mail_service from longpoll
                var data = {
                    info: false,
                    message_ids: [messageData.id],
                    starred: messageData.is_starred,
                    type: 'toggle_star',
                };
                var notification = [[false, 'res.partner'], data];
                form.call('bus_service', 'trigger', 'notification', [notification]);
                return $.when();
            }
            return this._super(route, args);
        },
        session: {},
    });

    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should be available");
    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain one message");
    assert.ok(form.$('.o_thread_message:first().o_mail_discussion').length,
        "the message should be a discussion");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('A message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('John Doe') >= 0,
        "the message's author should be correct");

    // send a message
    form.$('.o_chatter_button_new_message').click();
    assert.ok(!$('.oe_chatter .o_thread_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_thread_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 2, "thread should contain two messages");
    assert.ok(form.$('.o_thread_message:first().o_mail_discussion').length,
        "the last message should be a discussion");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('Me') >= 0,
        "the message's author should be correct");

    // log a note
    form.$('.o_chatter_button_log_note').click();
    assert.ok(!$('.oe_chatter .o_thread_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first note");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_thread_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 3, "thread should contain three messages");
    assert.ok(!form.$('.o_thread_message:first().o_mail_discussion').length,
        "the last message should not be a discussion");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first note') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('Me') >= 0,
        "the message's author should be correct");

    // star message 2
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star-o').length,
        "message 2 should not be starred");
    form.$('.o_thread_message[data-message-id=2] .o_thread_message_star').click();
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star').length,
        "message 2 should be starred");

    // unstar message 2
    form.$('.o_thread_message[data-message-id=2] .o_thread_message_star').click();
    assert.ok(form.$('.o_thread_message[data-message-id=2] .o_thread_message_star.fa-star-o').length,
        "message 2 should not be starred");

    // very basic test of mention
    form.$('.o_chatter_button_new_message').click();
    var $input = form.$('.oe_chatter .o_composer_text_field:first()');
    $input.val('@');
    // the cursor position must be set for the mention manager to detect that we are mentionning
    $input[0].selectionStart = 1;
    $input[0].selectionEnd = 1;
    $input.trigger('keyup');

    assert.strictEqual(getSuggestionsDef.state(), "pending",
        "the mention suggestion RPC should be throttled");

    getSuggestionsDef
        .then(concurrency.delay.bind(concurrency, 0))
        .then(function () {
            assert.strictEqual(form.$('.o_mention_proposition:visible').length, 1,
                "there should be one mention suggestion");
            assert.strictEqual(form.$('.o_mention_proposition').data('id'), 1,
                "suggestion's id should be correct");
            assert.strictEqual(form.$('.o_mention_proposition .o_mention_name').text(), 'Test User',
                "suggestion should be displayed correctly");
            assert.strictEqual(form.$('.o_mention_proposition .o_mention_info').text(), '(test@odoo.com)',
                "suggestion should be displayed correctly");

            //cleanup
            form.destroy();
            done();
        });
});

QUnit.test('chatter: post a message disable the send button', function(assert) {
    assert.expect(3);
    var form = createView({
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
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: []});
            }
            if (args.method === 'message_post') {
                assert.ok(form.$('.o_composer_button_send').prop("disabled"),
                    "Send button should be disabled when a message is being sent");
                return $.when(57923);
            }
            if (args.method === 'message_format') {
                return $.when([{
                    author_id: ["42", "Me"],
                    model: 'partner',
                }]);
            }
            return this._super(route, args);
        },
    });

    form.$('.o_chatter_button_new_message').click();
    assert.notOk(form.$('.o_composer_button_send').prop('disabled'),
        "Send button should be enabled when posting a message");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    form.$('.o_chatter_button_new_message').click();
    assert.notOk(form.$('.o_composer_button_send').prop('disabled'),
        "Send button should be enabled when posting another message");
    form.destroy();
});

QUnit.test('chatter: post message failure keep message', function(assert) {
    assert.expect(4);
    var form = createView({
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
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: []});
            }
            if (args.method === 'message_post') {
                assert.ok(form.$('.o_composer_button_send').prop("disabled"),
                    "Send button should be disabled when a message is being sent");
                // simulate failure
                return $.Deferred().reject();
            }
            if (args.method === 'message_format') {
                return $.when([]);
            }
            return this._super(route, args);
        },
    });

    form.$('.o_chatter_button_new_message').click();
    assert.notOk(form.$('.o_composer_button_send').prop('disabled'),
        "Send button should be enabled initially");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.strictEqual(form.$('.o_composer_text_field').val(), "My first message",
        "Should keep unsent message in the composer on failure");
    assert.notOk(form.$('.o_composer_button_send').prop('disabled'),
        "Send button should be re-enabled on message post failure");
    form.destroy();
});

QUnit.test('chatter: receive notif when document is open', function (assert) {
    assert.expect(2);

    var form = createView({
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
                '</div>' +
            '</form>',
        res_id: 2,
        session: {
            partner_id: 3,
        },
    });

    var thread = form.call('mail_service', 'getDocumentThread', 'partner', 2);
    assert.strictEqual(thread.getUnreadCounter(), 0,
        "document thread should have no unread messages initially");

    // simulate receiving a needaction message on this document thread
    var needactionMessageData = {
        id: 5,
        author_id: [42, "Someone"],
        body: 'important message',
        channel_ids: [],
        res_id: 2,
        model: 'partner',
        needaction: true,
        needaction_partner_ids: [3],
    };
    this.data['mail.message'].records.push(needactionMessageData);
    var notification = [[false, 'mail.channel', 1], needactionMessageData];
    form.call('bus_service', 'trigger', 'notification', [notification]);

    assert.strictEqual(thread.getUnreadCounter(), 1,
        "document thread should now have one unread message");

    form.destroy();
});

QUnit.test('chatter: access document with some notifs', function (assert) {
    assert.expect(3);

    // simulate received needaction message on this document thread
    var needactionMessageData = {
        id: 5,
        author_id: [42, "Someone"],
        body: 'important message',
        channel_ids: [],
        res_id: 2,
        model: 'partner',
        needaction: true,
        needaction_partner_ids: [3],
    };
    this.data['mail.message'].records.push(needactionMessageData);
    this.data['partner'].records[0].message_ids = [5];

    var form = createView({
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
                '</div>' +
            '</form>',
        res_id: 2,
        session: {
            partner_id: 3,
        },
        mockRPC: function (route, args) {
            if (args.method === 'set_message_done') {
                assert.step('set_message_done');
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.verifySteps(['set_message_done']);

    var thread = form.call('mail_service', 'getDocumentThread', 'partner', 2);
    assert.strictEqual(thread.getUnreadCounter(), 0,
        "document thread should have no unread messages (marked as read)");

    form.destroy();
});

QUnit.test('chatter: post a message and switch in edit mode', function (assert) {
    assert.expect(5);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: []});
            }
            if (args.method === 'message_post') {
                this.data['mail.message'].records.push({
                    attachment_ids: args.kwargs.attachment_ids,
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    date: "2016-12-20 10:35:40",
                    id: 42,
                    is_note: args.kwargs.subtype === 'mail.mt_note',
                    is_discussion: args.kwargs.subtype === 'mail.mt_comment',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                return $.when(42);
            }

            return this._super(route, args);
        },
    });

    assert.strictEqual(form.$('.o_thread_message').length, 0, "thread should not contain messages");

    // send a message
    form.$('.o_chatter_button_new_message').click();
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain a message");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first message') >= 0,
        "the message's body should be correct");

    // switch in edit mode
    form.$buttons.find('.o_form_button_edit').click();
    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain a message");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first message') >= 0,
        "the message's body should be correct");

    form.destroy();
});

QUnit.test('chatter: discard changes on message post with post_refresh "always"', function (assert) {
    // After posting a message that always reloads the record, if the record
    // is dirty (= has some unsaved changes), we should warn the user that
    // these changes will be lost if he proceeds.
    assert.expect(2);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"' +
                        ' options="{\'display_log_button\': True, \'post_refresh\': \'always\'}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    // Make record dirty
    form.$('.o_form_sheet input').val('trululu').trigger('input');

    // Send a message
    form.$('.o_chatter_button_new_message').click();
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();

    var $modal = $('.modal-dialog');
    assert.strictEqual($modal.length, 1, "should have a modal opened");
    assert.strictEqual($modal.find('.modal-body').text(),
        "The record has been modified, your changes will be discarded. Do you want to proceed?",
        "should warn the user that any unsaved changes will be lost");

    form.destroy();
});

QUnit.test('chatter: discard changes on message post without post_refresh', function (assert) {
    // After posting a message, if the record is dirty and there are no
    // post_refresh rule, it will not discard the changes on the record.
    assert.expect(2);

    var hasDiscardChanges = false; // set if `discard_changes` has been triggered up
    var messages = [];
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"' +
                        ' options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            if (args.method === 'message_format') {
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(args.args[0], msg.id);
                });
                return $.when(requested_msgs);
            }
            if (args.method === 'message_post') {
                messages.push({
                    attachment_ids: [],
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    date: moment().format('YYYY-MM-DD HH:MM:SS'), // now
                    displayed_author: "Me",
                    id: 42,
                    is_note: args.kwargs.subtype === 'mail.mt_note',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                return $.when(42);
            }
            return this._super(route, args);
        },
        intercepts: {
            discard_changes: function () {
                hasDiscardChanges = true; // should not do that
            },
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    // Make record dirty
    form.$('.o_form_sheet input').val('trululu').trigger('input');

    // Send a message
    form.$('.o_chatter_button_new_message').click();
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();

    var $modal = $('.modal-dialog');
    assert.strictEqual($modal.length, 0, "should have no modal opened");
    assert.notOk(hasDiscardChanges);

    form.destroy();
});

QUnit.test('chatter: discard changes on message post with post_refresh "recipients"', function (assert) {
    // After posting a message with mentions, the record will be reloaded,
    // as the rpc `message_post` may make changes on some fields of the record.
    // If the record is dirty (= has some unsaved changes), we should warn the
    // user that these changes will be lost if he proceeds.
    assert.expect(2);
    var done = assert.async();

    var getSuggestionsDef = $.Deferred();

    var messages = [];
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"' +
                        ' options="{\'display_log_button\': True, \'post_refresh\': \'recipients\'}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: [[42, "Me"]]});
            }
            if (args.method === 'get_mention_suggestions') {
                getSuggestionsDef.resolve();
                return $.when([{email: "me@odoo.com", id: 42, name: "Me"}]);
            }
            if (args.method === 'message_format') {
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(args.args[0], msg.id);
                });
                return $.when(requested_msgs);
            }
            if (args.method === 'message_post') {
                messages.push({
                    attachment_ids: [],
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    date: moment().format('YYYY-MM-DD HH:MM:SS'), // now
                    displayed_author: "Me",
                    id: 42,
                    is_note: args.kwargs.subtype === 'mail.mt_note',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                return $.when(42);
            }
            return this._super(route, args);
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    // Make record dirty
    form.$('.o_form_sheet input').val('trululu').trigger('input');

    // create a new message
    form.$('.o_chatter_button_new_message').click();

    // Add a user as mention
    form.$('.oe_chatter .o_composer_text_field:first()').val("@");

    var $input = form.$('.oe_chatter .o_composer_text_field:first()');
    $input.val('@');
    // the cursor position must be set for the mention manager to detect that we are mentionning
    $input[0].selectionStart = 1;
    $input[0].selectionEnd = 1;
    $input.trigger('keyup');

    getSuggestionsDef
        .then(concurrency.delay.bind(concurrency, 0))
        .then(function () {
            // click on mention
            $input.trigger($.Event('keyup', {which: $.ui.keyCode.ENTER}));

            // untick recipient as follower (prompts a res.partner form otherwise)
            form.$('input[type="checkbox"]').prop('checked', false);

            // send message
            form.$('.oe_chatter .o_composer_button_send').click();

            var $modal = $('.modal-dialog');
            assert.strictEqual($modal.length, 1, "should have a modal opened");
            assert.strictEqual($modal.find('.modal-body').text(),
                "The record has been modified, your changes will be discarded. Do you want to proceed?",
                "should warn the user that any unsaved changes will be lost");

            form.destroy();
            done();
        });
});

QUnit.test('chatter: discard changes on opening full-composer', function (assert) {
    // When we open the full-composer, any following operations by the user
    // will reload the record (even closing the full-composer). Therefore,
    // we should warn the user when we open the full-composer if the record
    // is dirty (= has some unsaved changes).
    assert.expect(2);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"' +
                        ' options="{\'display_log_button\': True,' +
                        ' \'post_refresh\': \'always\'}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
        mockRPC: function (route, args) {
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
        viewOptions: {
            mode: 'edit',
        },
    });

    // Make record dirty
    form.$('.o_form_sheet input').val('trululu').trigger('input');

    // Open full-composer
    form.$('.o_chatter_button_new_message').click();
    form.$('.o_composer_button_full_composer').click();

    var $modal = $('.modal-dialog');
    assert.strictEqual($modal.length, 1, "should have a modal opened");
    assert.strictEqual($modal.find('.modal-body').text(),
        "The record has been modified, your changes will be discarded. Do you want to proceed?",
        "should warn the user that any unsaved changes will be lost");

    form.destroy();
});

QUnit.test('chatter in x2many form view', function (assert) {
    // the purpose of this test is to ensure that it doesn't crash when a x2many
    // record is opened in form view (thus in a dialog), and when there is a
    // chatter in the arch (typically, this may occur when the view used for the
    // x2many is a default one, which is also used in another context, as the
    // chatter is hidden in the dialog anyway)
    assert.expect(2);

    this.data.partner.fields.o2m = {
        string: "one2many field", type: "one2many", relation: 'partner',
    };
    this.data.partner.records[0].o2m = [2];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form><field name="o2m"/></form>',
        archs: {
            'partner,false,form': '<form>' +
                '<field name="foo"/>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread"/>' +
                '</div>' +
            '</form>',
            'partner,false,list': '<tree><field name="display_name"/></tree>',
        },
        res_id: 2,
        viewOptions: {
            mode: 'edit',
        },
    });

    form.$('.o_data_row:first').click();

    assert.strictEqual($('.modal .o_form_view').length, 1,
        "should have open a form view in a modal");
    assert.strictEqual($('.modal .o_chatter:visible').length, 0,
        "chatter should be hidden (as in a dialog)");

    form.destroy();
});

QUnit.test('chatter: Attachment viewer', function (assert) {
    assert.expect(6);
    this.data.partner.records[0].message_ids = [1];
    this.data['mail.message'].records = [{
        attachment_ids: [{
            filename: 'image1.jpg',
            id:1,
            checksum: 999,
            mimetype: 'image/jpeg',
            name: 'Test Image 1',
            url: '/web/content/1?download=true'
        },{
            filename: 'image2.jpg',
            id:2,
            checksum: 999,
            mimetype: 'image/jpeg',
            name: 'Test Image 2',
            url: '/web/content/2?download=true'
        },{
            filename: 'image3.jpg',
            id:3,
            checksum: 999,
            mimetype: 'image/jpeg',
            name: 'Test Image 3',
            url: '/web/content/3?download=true'
        },{
            filename: 'pdf1.pdf',
            id:4,
            mimetype: 'application/pdf',
            name: 'Test PDF 1',
            url: '/web/content/4?download=true'
        }],
        author_id: ["1", "John Doe"],
        body: "Attachement viewer test",
        date: "2016-12-20 09:35:40",
        id: 1,
        is_note: false,
        is_discussion: true,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (_.str.contains(route, '/mail/attachment/preview/') ||
                _.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')){
                var canvas = document.createElement('canvas');
                return $.when(canvas.toDataURL());
            }
            return this._super.apply(this, arguments);
        },
    });
    assert.strictEqual(form.$('.o_thread_message .o_attachment').length, 4,
        "there should be three attachment on message");
    assert.strictEqual(form.$('.o_thread_message .o_attachment a').first().attr('href'), '/web/content/1?download=true',
        "image caption should have correct download link");
    // click on first image attachement
    form.$('.o_thread_message .o_attachment .o_image_box .o_image_overlay').first().click();
    assert.strictEqual($('.o_modal_fullscreen img.o_viewer_img[data-src="/web/image/1?unique=1&signature=999"]').length, 1,
        "Modal popup should open with first image src");
    //  click on next button
    $('.modal .arrow.arrow-right.move_next span').click();
    assert.strictEqual($('.o_modal_fullscreen img.o_viewer_img[data-src="/web/image/2?unique=1&signature=999"]').length, 1,
        "Modal popup should have now second image src");
    assert.strictEqual($('.o_modal_fullscreen .o_viewer_toolbar .o_download_btn').length, 1,
        "Modal popup should have download button");
    // close attachment popup
    $('.o_modal_fullscreen .o_viewer-header .o_close_btn').click();
    // click on pdf attachement
    form.$('span:contains(Test PDF 1)').click();
    assert.strictEqual($('.o_modal_fullscreen iframe[data-src*="/web/content/4"]').length, 1,
        "Modal popup should open with the pdf preview");
    // close attachment popup
    $('.o_modal_fullscreen .o_viewer-header .o_close_btn').click();
    form.destroy();
});

QUnit.test('form activity widget: read RPCs', function (assert) {
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
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 2,
    }];

    var nbReads = 0;
    var form = createView({
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
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "should display an activity");
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message .o_activity_date').text(),
        'Today', "the activity should be today");

    form.$buttons.find('.o_form_button_edit').click();
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(nbReads, 1, "should not have re-read the activities");

    // simulate a date change, and a reload of the form view
    var tomorrow = moment().add(1, 'day').format("YYYY-MM-DD");
    this.data['mail.activity'].records[0].date_deadline = tomorrow;
    form.reload();

    assert.strictEqual(nbReads, 2, "should have re-read the activities");
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message .o_activity_date').text(),
        'Tomorrow', "the activity should be tomorrow");

    form.destroy();
});

QUnit.test('form activity widget on a new record', function (assert) {
    assert.expect(0);

    var form = createView({
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

QUnit.test('form activity widget with another x2many field in view', function (assert) {
    assert.expect(1);

    this.data.partner.fields.m2m = {string: "M2M", type: 'many2many', relation: 'partner'};

    this.data.partner.records[0].m2m = [2];
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 2,
    }];

    var form = createView({
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

    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "should display an activity");

    form.destroy();
});

QUnit.test('form activity widget: schedule next activity', function (assert) {
    assert.expect(4);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 2,
    }];

    var form = createView({
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
                return $.when('test_result');
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
    form.$('.o_mail_activity .o_mark_as_done[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 1,
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    form.$('.o_activity_popover_done_next').click(); // schedule next activity
    form.destroy();
});


QUnit.test('form activity widget: edit next activity', function (assert) {
    assert.expect(3);
    var self = this;
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 2,
    }];

    var form = createView({
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
                    res_id: 1,
                    res_model: "mail.activity",
                    target: "new",
                    type: "ir.actions.act_window",
                    view_mode: "form",
                    view_type: "form",
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
    form.$('.o_mail_activity .o_edit_activity[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity .o_mail_info strong:eq(1)').text(), " Type 1", 
        "After edit type should be Type 1");
    form.destroy();
});

QUnit.test('form activity widget: clic mail template', function (assert) {
    assert.expect(4);
    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 2,
    }];

    var form = createView({
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
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "we should have one activity");
    assert.strictEqual(form.$('.o_activity_template_preview').length, 1,
        "Activity should contains one mail template");
    form.$('.o_activity_template_preview[data-template-id=100]').click();
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "activity should still be there");
    form.destroy();
});

QUnit.test('form activity widget: schedule activity does not discard changes', function (assert) {
    assert.expect(1);

    var form = createView({
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
    form.$('.o_field_widget[name=foo]').val('new value').trigger('input');

    // schedule an activity (this triggers a do_action)
    form.$('.o_chatter_button_schedule_activity').click();

    // save the record
    form.$buttons.find('.o_form_button_save').click();

    form.destroy();
});

QUnit.test('form activity widget: mark as done and remove', function (assert) {
    assert.expect(15);

    var self = this;

    var nbReads = 0;
    this.data.partner.records[0].activity_ids = [1, 2];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 1,
    }, {
        id: 2,
        display_name: "A second activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        create_user_id: 2,
        activity_type_id: 1,
    }];

    var form = createView({
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

    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 2,
        "there should be two activities");

    // remove activity 1
    form.$('.o_mail_activity .o_unlink_activity[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "there should be one remaining activity");
    assert.ok(!form.$('.o_mail_activity .o_unlink_activity[data-activity-id=1]').length,
        "activity 1 should have been removed");

    // mark activity done
    assert.ok(!form.$('.o_mail_thread .o_thread_message').length,
        "there should be no chatter message");
    form.$('.o_mail_activity .o_mark_as_done[data-activity-id=2]').click();
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 1,
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    form.$('.o_activity_popover_done').click(); // send feedback
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 0,
        "the feedback popover should be closed");
    assert.ok(!form.$('.o_mail_activity .o_thread_message').length,
        "there should be no more activity");
    assert.strictEqual(form.$('.o_mail_thread .o_thread_message').length, 1,
        "a chatter message should have been generated");
    assert.strictEqual(form.$('.o_thread_message:contains(The activity has been done)').length, 1,
        "the message's body should be correct");
    form.destroy();
});

QUnit.test('followers widget: follow/unfollow, edit subtypes', function (assert) {
    assert.expect(24);

    var resID = 2;
    var partnerID = 1;
    var followers = [];
    var nbReads = 0;
    var subtypes = [
        {id: 1, name: "First subtype", followed: true},
        {id: 2, name: "Second subtype", followed: true},
        {id: 3, name: "Third subtype", followed: false},
    ];
    var form = createView({
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
                        is_uid: true,
                        name: "Admin",
                        email: "admin@example.com",
                        res_id: resID,
                        res_model: 'partner',
                    });
                }
                return $.when(true);
            }
            if (route === '/mail/read_followers') {
                return $.when({
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
                return $.when(true);
            }
            if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read: should read all fields
                    assert.strictEqual(args.args[1].length, 3,
                        'should read "foo", "message_follower_ids" and "display_name"');
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
    form.$('.o_followers_follow_button').click();
    assert.strictEqual(form.$('.o_followers_count').text(), "1", 'should have one follower');
    assert.ok(form.$('.o_followers_follow_button.o_followers_following').length,
        'should display the "Following/Unfollow" button');
    assert.strictEqual(form.$('.o_followers_list .o_partner').length, 1,
        "there should be one follower in the follower dropdown");

    // edit the subtypes
    assert.strictEqual(form.$('.o_subtypes_list .o_subtype').length, 3,
        'subtype list should contain 3 subtypes');
    assert.strictEqual(form.$('.o_subtypes_list .o_subtype_checkbox:checked').length, 2,
        'two subtypes should be checked by default');
    form.$('.o_subtypes_list .dropdown-toggle').click(); // click to open the dropdown
    assert.ok(form.$('.o_subtypes_list.show').length, 'dropdown should be opened');
    form.$('.o_subtypes_list .o_subtype input[data-id=2]').click(); // uncheck second subtype
    assert.ok(form.$('.o_subtypes_list.show').length, 'dropdown should remain opened');
    assert.ok(!form.$('.o_subtypes_list .o_subtype_checkbox[data-id=2]:checked').length,
        'second subtype should now be unchecked');

    // click to unfollow
    form.$('.o_followers_follow_button').click(); // click to open the dropdown
    assert.ok($('.modal').length, 'a confirm modal should be opened');
    $('.modal .modal-footer .btn-primary').click(); // click on 'OK'
    assert.strictEqual(form.$('.o_followers_count').text(), "0", 'should have no followers');
    assert.ok(form.$('.o_followers_follow_button.o_followers_notfollow').length,
        'should display the "Follow" button');

    form.destroy();
});

QUnit.test('followers widget: do not display follower duplications', function (assert) {
    assert.expect(2);

    this.data.partner.records[0].message_follower_ids = [1];
    var resID = 2;
    var followers = [{
        id: 1,
        name: "Admin",
        email: "admin@example.com",
        res_id: resID,
        res_model: 'partner',
    }];
    var def;
    var form = createView({
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
                return $.when(def).then(function () {
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
        session: {partner_id: 1},
    });


    followers.push({
        id: 2,
        is_uid: false,
        name: "A follower",
        email: "follower@example.com",
        res_id: resID,
        res_model: 'partner',
    });
    this.data.partner.records[0].message_follower_ids.push(2);

    // simulate concurrent calls to read_followers and check that those followers
    // are not added twice in the dropdown
    def = $.Deferred();
    form.reload();
    form.reload();
    def.resolve();

    assert.strictEqual(form.$('.o_followers_count').text(), '2',
        "should have 2 followers");
    assert.strictEqual(form.$('.o_followers_list .o_partner').length, 2,
        "there should be 2 followers in the follower dropdown");

    form.destroy();
});

QUnit.test('does not render and crash when destroyed before chat system is ready', function (assert) {
    assert.expect(0);

    var def = $.Deferred();

    var form = createView({
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
                    '<field name="message_ids" widget="mail_thread"/>' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'message_format') {
                return $.when([{
                    attachment_ids: [],
                    body: "",
                    date: "2016-12-20 09:35:40",
                    id: 34,
                    res_id: 3,
                    author_id: ["3", "Fu Ck Mil Grom"],
                }]);
            }
            if (route === '/mail/read_followers') {
                return $.when({
                    followers: [],
                    subtypes: [],
                });
            }
            return this._super(route, args);
        },
        intercepts: {
            get_session: function (event) {
                event.stopPropagation();
                event.data.callback({uid: 1, origin: 'http://web'});
            },
        },
    });

    form.destroy();
    // here, the chat service system is ready, and the chatter can try to render
    // itself. We simply make sure here that no crashes occur (since the form
    // view is destroyed, all rpcs will be dropped, and many other mechanisms
    // relying on events will not work, such as the chat bus)
    def.resolve();
});

QUnit.test('chatter: do not duplicate messages on (un)star message', function (assert) {
    assert.expect(4);

    this.data.partner.records[0].message_ids = [1];
    this.data['mail.message'].records = [{
        author_id: ["1", "John Doe"],
        body: "A message",
        date: "2016-12-20 09:35:40",
        id: 1,
        is_note: false,
        is_discussion: true,
        is_notification: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'toggle_message_starred') {
                var messageData = _.findWhere(
                    this.data['mail.message'].records,
                    { id: args.args[0][0] }
                );
                messageData.is_starred = !messageData.is_starred;
                // simulate notification received by mail_service from longpoll
                var data = {
                    info: false,
                    message_ids: [messageData.id],
                    starred: messageData.is_starred,
                    type: 'toggle_star',
                };
                var notification = [[false, 'res.partner'], data];
                form.call('bus_service', 'trigger', 'notification', [notification]);
                return $.when();
            }
            return this._super(route, args);
        },
        session: {},
    });

    assert.strictEqual(form.$('.o_thread_message').length, 1,
        "there should be a single message in the chatter");
    assert.ok(form.$('.o_thread_message .o_thread_message_star.fa-star-o').length,
        "message should not be starred");

    // star message
    form.$('.o_thread_message .o_thread_message_star').click();
    assert.strictEqual(form.$('.o_thread_message').length, 1,
        "there should still be a single message in the chatter after starring the message");

    // unstar message
    form.$('.o_thread_message .o_thread_message_star').click();
    assert.strictEqual(form.$('.o_thread_message').length, 1,
        "there should still be a single message in the chatter after unstarring the message");

    //cleanup
    form.destroy();
});

QUnit.test('chatter: new messages on document without any "display_name"', function (assert) {
    assert.expect(5);

    this.data.partner.records[0].message_ids = [1];
    this.data.partner.records[0].display_name = false;
    this.data['mail.message'].records = [{
        author_id: [1, "John Doe"],
        body: "A message",
        date: "2016-12-20 09:35:40",
        id: 1,
        is_note: false,
        is_discussion: true,
        is_notification: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        services: this.services,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        session: {},
    });

    assert.strictEqual(form.$('.o_thread_message').length, 1,
        "should have a single message in the chatter");
    assert.strictEqual(form.$('.o_thread_message[data-message-id="1"]').length, 1,
        "single message should have ID 1");

    // Simulate a new message in the chatter
    this.data['mail.message'].records.push({
        author_id: [2, "Mister Smith"],
        body: "Second message",
        date: "2016-12-20 09:35:40",
        id: 2,
        is_note: false,
        is_discussion: true,
        is_notification: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    });
    this.data.partner.records[0].message_ids.push(2);

    form.reload();

    assert.strictEqual(form.$('.o_thread_message').length, 2,
        "should have a two messages in the chatter after reload");
    assert.strictEqual(form.$('.o_thread_message[data-message-id="1"]').length, 1,
        "one of the message should have ID 1");
    assert.strictEqual(form.$('.o_thread_message[data-message-id="2"]').length, 1,
        "the other message should have ID 2");

    //cleanup
    form.destroy();
});

QUnit.test('chatter: suggested partner auto-follow on message post', function (assert) {
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
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];

    var followers = [];
    followers.push({
        id: 1,
        is_uid: true,
        name: "Admin",
        email: "admin@example.com",
        res_id: 5,
        res_model: 'partner',
    });

    var form = createView({
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
            if (args.method === 'message_get_suggested_recipients') {
                return $.when({2: [
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
                    is_uid: true,
                    name: "Demo User",
                    email: "demo-user@example.com",
                    res_id: 8,
                    res_model: 'partner',
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
                    is_note: args.kwargs.subtype === 'mail.mt_note',
                    is_discussion: args.kwargs.subtype === 'mail.mt_comment',
                    is_notification: false,
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                return $.when(messageID);
            }
            if (route === '/mail/read_followers') {
                return $.when({
                    followers: followers,
                });
            }
            return this._super(route, args);
        },
        session: {},
    });

    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain one message");
    assert.ok(form.$('.o_thread_message:first().o_mail_discussion').length,
        "the message should be a discussion");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('A message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('John Doe') >= 0,
        "the message's author should be correct");
    assert.strictEqual(form.$('.o_followers').length, 1,
        "should display follower widget");
    assert.strictEqual(form.$('.o_followers_count').text(), "1",
        "should have a single follower (widget counter)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner').length, 1,
        "should have a single follower (listed partners)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a').text(), "Admin",
        "should have 'Admin' as follower");

    // open composer
    form.$('.o_chatter_button_new_message').click();
    assert.ok(!$('.oe_chatter .o_thread_composer').hasClass('o_hidden'), "chatter should be opened");
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
    form.$('.oe_chatter .o_composer_button_send').click();

    assert.strictEqual(form.$('.o_followers_count').text(), "2",
        "should have a two followers (widget counter)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner').length, 2,
        "should have two followers (listed partners)");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a[data-oe-id="5"]').text(),
        "Admin",
        "should have 'Admin' as follower");
    assert.strictEqual(form.$('.o_followers_list > div.o_partner > a[data-oe-id="8"]').text(),
        "Demo User",
        "should have 'Demo User' as follower");

    //cleanup
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
    createAsyncView({
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
                assert.step(args.args[0]);
                assert.deepEqual(args.args[1] , ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    }).then(function (form) {
        // should read it 3 times (1 with the form view, one with the form dialog and one after save)
        assert.verifySteps([[12, 14], [14], [14]]);
        assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').length, 2,
            "two tags should be present");
        var firstTag = form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').first();
        assert.strictEqual(firstTag.find('.o_badge_text').text(), "gold",
            "tag should only show display_name");
        assert.strictEqual(firstTag.find('.o_badge_text').attr('title'), "coucou@petite.perruche",
            "tag should show email address on mouse hover");
        form.destroy();
        done();
    });

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
        "the opened modal should be a form view dialog with the partner_type 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will render the form view)
    $('.modal-body.o_act_window input[name="email"]').val('coucou@petite.perruche').trigger('input');
    $('.modal-footer .btn-primary').click();
});

QUnit.test('fieldmany2many tags email (edition)', function (assert) {
    assert.expect(15);

    this.data.partner.records[0].timmy = [12];

    var form = createView({
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
                assert.step(args.args[0]);
                assert.deepEqual(args.args[1] , ['display_name', 'email'], "should read the email");
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner_type,false,form': '<form string="Types"><field name="display_name"/><field name="email"/></form>',
        },
    });

    assert.verifySteps([[12]]);
    assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').length, 1,
        "should contain one tag");

    // add an other existing tag
    var $input = form.$('.o_field_many2manytags input');
    $input.click(); // opens the dropdown
    $input.autocomplete('widget').find('li:first').click(); // add 'silver'

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
        "the opened modal in edit mode should be a form view dialog with the partner_type 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will rerender the form view)
    $('.modal-body.o_act_window input[name="email"]').val('coucou@petite.perruche').trigger('input');
    $('.modal-footer .btn-primary').click();

    assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] .badge.o_tag_color_0').length, 2,
        "should contain the second tag");
    // should have read [14] three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps([[12], [14], [14], [14]]);

    form.destroy();
});

});
});
