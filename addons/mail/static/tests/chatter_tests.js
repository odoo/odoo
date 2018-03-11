odoo.define('mail.chatter_tests', function (require) {
"use strict";

var Composers = require('mail.composer');

var Bus = require('web.Bus');
var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

var BasicComposer = Composers.BasicComposer;

var createAsyncView = testUtils.createAsyncView;
var createView = testUtils.createView;

QUnit.module('mail', {}, function () {

QUnit.module('Chatter', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    message_follower_ids: {
                        string: "Followers",
                        type: "one2many",
                        relation: 'mail.followers',
                        relation_field: "res_id"
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
                },
                records: [{
                    id: 2,
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
                    display_name: { string: "Display name", type: "char" },
                    date_deadline: { string: "Due Date", type: "date" },
                    user_id: { string: "Assigned to", type: "many2one", relation: 'partner' },
                    state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['overdue', 'Overdue'], ['today', 'Today'], ['planned', 'Planned']],
                    },
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
            }
        };
    }
});

QUnit.test('basic rendering', function (assert) {
    assert.expect(8);

    var count = 0;
    var unwanted_read_count = 0;
    // var msgRpc = 0;

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
            if ('/web/dataset/call_kw/mail.followers/read' === route) {
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
        intercepts: {
            get_messages: function (event) {
                // msgRpc++;
                event.stopPropagation();
                event.data.callback($.when([{
                    attachment_ids: [],
                    body: "",
                    date: moment("2016-12-20 09:35:40"),
                    id: 34,
                    res_id: 3,
                    author_id: ["3", "Fu Ck Mil Grom"],
                }]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
            get_session: function (event) {
                event.stopPropagation();
                event.data.callback({uid: 1});
            },
        },
    });

    assert.ok(form.$('.o_mail_activity').length, "there should be an activity widget");
    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_schedule_activity').length,
        "there should be a 'Schedule an activity' button in the chatter's topbar");
    assert.ok(form.$('.o_chatter_topbar .o_followers').length,
        "there should be a followers widget, moved inside the chatter's topbar");
    assert.ok(form.$('.o_chatter').length, "there should be a chatter widget");
    assert.ok(form.$('.o_mail_thread').length, "there should be a mail thread");
    assert.ok(!form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should not be available");
    // assert.strictEqual(msgRpc, 1, "should have fetched messages once");

    form.$buttons.find('.o_form_button_edit').click();
    // assert.strictEqual(msgRpc, 1, "should still have fetched messages only once");
    assert.strictEqual(count, 0, "should have done no read_followers rpc as there are no followers");
    assert.strictEqual(unwanted_read_count, 0, "followers should only be fetched with read_followers route");
    form.destroy();
});

QUnit.test('chatter is not rendered in mode === create', function (assert) {
    assert.expect(4);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
        },
    });

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    form.$buttons.find('.o_form_button_create').click();

    assert.strictEqual(form.$('.o_chatter').length, 0,
        "chatter should not be displayed");

    form.$('.o_field_char').val('coucou').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    // check if chatter buttons still work
    form.$('.o_chatter_button_new_message').click();
    assert.strictEqual(form.$('.o_chat_composer:visible').length, 1,
        "chatter should be opened");

    form.destroy();
});

QUnit.test('chatter rendering inside the sheet', function (assert) {
    assert.expect(4);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
        },
    });

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    form.$buttons.find('.o_form_button_create').click();

    assert.strictEqual(form.$('.o_chatter').length, 0,
        "chatter should not be displayed");

    form.$('.o_field_char').val('coucou').trigger('input');
    form.$buttons.find('.o_form_button_save').click();

    assert.strictEqual(form.$('.o_chatter').length, 1,
        "chatter should be displayed");

    // check if chatter buttons still work
    form.$('.o_chatter_button_new_message').click();
    assert.strictEqual(form.$('.o_chat_composer:visible').length, 1,
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
    assert.expect(11);

    this.data.partner.records[0].activity_ids = [1];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
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
    var label_text = $record.find('.o_activity_label .o_activity_color_today').text();
    assert.ok(label_text.indexOf('Today (1)') >= 0, "should display the correct label and count");

    // click on the activity button to close the dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 2, 'no RPC should be done when closing the dropdown');

    // click on the activity button to re-open dropdown
    $record.find('.o_activity_btn').click();
    assert.strictEqual(rpcCount, 3, 'should have reloaded the activities');

    // mark activity as done
    $record.find('.o_mark_as_done').click();
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset
    assert.strictEqual(rpcCount, 5, 'should have done an RPC to mark activity as done, and a read');
    assert.ok($record.find('.o_mail_activity .o_activity_color_default:not(.o_activity_color_today)').length,
        "activity widget should have been updated correctly");
    assert.strictEqual($record.find('.o_mail_activity.open').length, 1,
        "dropdown should remain open when marking an activity as done");
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    kanban.destroy();
});

QUnit.test('chatter: post, receive and star messages', function (assert) {
    var done = assert.async();
    assert.expect(27);

    // Remove the mention throttle to speed up the test
    var mentionThrottle = BasicComposer.prototype.MENTION_THROTTLE;
    BasicComposer.prototype.MENTION_THROTTLE = 1;

    this.data.partner.records[0].message_ids = [1];
    var messages = [{
        attachment_ids: [],
        author_id: ["1", "John Doe"],
        body: "A message",
        date: moment("2016-12-20 09:35:40"),
        displayed_author: "John Doe",
        id: 1,
        is_note: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];
    var bus = new Bus();
    var getSuggestionsDef = $.Deferred();
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
            return this._super(route, args);
        },
        session: {},
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(event.data.options.ids, msg.id);
                });
                event.data.callback($.when(requested_msgs));
            },
            post_message: function (event) {
                event.stopPropagation();
                var msg_id = messages[messages.length-1].id + 1;
                messages.push({
                    attachment_ids: [],
                    author_id: ["42", "Me"],
                    body: event.data.message.content,
                    date: moment(), // now
                    displayed_author: "Me",
                    id: msg_id,
                    is_note: event.data.message.subtype === 'mail.mt_note',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                bus.trigger('new_message', {
                    id: msg_id,
                    model: event.data.options.model,
                    res_id: event.data.options.res_id,
                });
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(bus);
            },
            toggle_star_status: function (event) {
                event.stopPropagation();
                assert.strictEqual(event.data.message_id, 2,
                    "toggle_star_status should have been triggered for message 2 (twice)");
                var msg = _.findWhere(messages, {id: event.data.message_id});
                msg.is_starred = !msg.is_starred;
                bus.trigger('update_message', msg);
            },
        },
    });

    assert.ok(form.$('.o_chatter_topbar .o_chatter_button_log_note').length,
        "log note button should be available");
    assert.strictEqual(form.$('.o_thread_message').length, 1, "thread should contain one message");
    assert.ok(!form.$('.o_thread_message:first() .o_mail_note').length,
        "the message shouldn't be a note");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('A message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('John Doe') >= 0,
        "the message's author should be correct");

    // send a message
    form.$('.o_chatter_button_new_message').click();
    assert.ok(!$('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first message");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 2, "thread should contain two messages");
    assert.ok(!form.$('.o_thread_message:first() .o_mail_note').length,
        "the last message shouldn't be a note");
    assert.ok(form.$('.o_thread_message:first() .o_thread_message_core').text().indexOf('My first message') >= 0,
        "the message's body should be correct");
    assert.ok(form.$('.o_thread_message:first() .o_mail_info').text().indexOf('Me') >= 0,
        "the message's author should be correct");

    // log a note
    form.$('.o_chatter_button_log_note').click();
    assert.ok(!$('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be opened");
    form.$('.oe_chatter .o_composer_text_field:first()').val("My first note");
    form.$('.oe_chatter .o_composer_button_send').click();
    assert.ok($('.oe_chatter .o_chat_composer').hasClass('o_hidden'), "chatter should be closed");
    assert.strictEqual(form.$('.o_thread_message').length, 3, "thread should contain three messages");
    assert.ok(form.$('.o_thread_message:first() .o_mail_note').length,
        "the last message should be a note");
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

            BasicComposer.prototype.MENTION_THROTTLE = mentionThrottle;
            form.destroy();
            done();
        });
});

QUnit.test('chatter: post a message and switch in edit mode', function (assert) {
    assert.expect(5);

    var messages = [];
    var bus = new Bus();
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
            }
            return this._super(route, args);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(event.data.options.ids, msg.id);
                });
                event.data.callback($.when(requested_msgs));
            },
            post_message: function (event) {
                event.stopPropagation();
                messages.push({
                    attachment_ids: [],
                    author_id: ["42", "Me"],
                    body: event.data.message.content,
                    date: moment(), // now
                    displayed_author: "Me",
                    id: 42,
                    is_note: event.data.message.subtype === 'mail.mt_note',
                    is_starred: false,
                    model: 'partner',
                    res_id: 2,
                });
                bus.trigger('new_message', {
                    id: 42,
                    model: event.data.options.model,
                    res_id: event.data.options.res_id,
                });
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(bus);
            },
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

QUnit.test('chatter: Attachment viewer', function (assert) {
    assert.expect(6);
    this.data.partner.records[0].message_ids = [1];
    var messages = [{
        attachment_ids: [{
            filename: 'image1.jpg',
            id:1,
            mimetype: 'image/jpeg',
            name: 'Test Image 1',
            url: '/web/content/1?download=true'
        },{
            filename: 'image2.jpg',
            id:2,
            mimetype: 'image/jpeg',
            name: 'Test Image 2',
            url: '/web/content/2?download=true'
        },{
            filename: 'image3.jpg',
            id:3,
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
        date: moment("2016-12-20 09:35:40"),
        displayed_author: "John Doe",
        id: 1,
        is_note: false,
        is_starred: false,
        model: 'partner',
        res_id: 2,
    }];
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<sheet>' +
                    '<field name="foo"/>' +
                '</sheet>' +
                '<div class="oe_chatter">' +
                    '<field name="message_ids" widget="mail_thread" options="{\'display_log_button\': True}"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route) {
            if(_.str.contains(route, '/mail/attachment/preview/') ||
                _.str.contains(route, '/web/static/lib/pdfjs/web/viewer.html')){
                var canvas = document.createElement('canvas');
                return $.when(canvas.toDataURL());
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                var requested_msgs = _.filter(messages, function (msg) {
                    return _.contains(event.data.options.ids, msg.id);
                });
                event.data.callback($.when(requested_msgs));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
        },
    });
    assert.strictEqual(form.$('.o_thread_message .o_attachment').length, 4,
        "there should be three attachment on message");
    assert.strictEqual(form.$('.o_thread_message .o_attachment .caption a').first().attr('href'), '/web/content/1?download=true',
        "image caption should have correct download link");
    // click on first image attachement
    form.$('.o_thread_message .o_attachment .o_image_box .o_image_overlay').first().click();
    assert.strictEqual($('.o_modal_fullscreen img.o_viewer_img[src*="/web/image/1?unique=1"]').length, 1,
        "Modal popup should open with first image src");
    //  click on next button
    $('.modal .arrow.arrow-right.move_next span').click();
    assert.strictEqual($('.o_modal_fullscreen img.o_viewer_img[src*="/web/image/2?unique=1"]').length, 1,
        "Modal popup should have now second image src");
    assert.strictEqual($('.o_modal_fullscreen .o_viewer_toolbar .o_download_btn').length, 1,
        "Modal popup should have download button");
    // close attachment popup
    $('.o_modal_fullscreen .o_viewer-header .o_close_btn').click();
    // click on pdf attachement
    form.$('.o_thread_message .o_attachment .o_image_box .o_image_overlay').eq(3).click();
    assert.strictEqual($('.o_modal_fullscreen iframe[src*="/web/content/4"]').length, 1,
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
        activity_type_id: 2,
    }];

    var nbReads = 0;
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                '<div class="oe_chatter">' +
                    '<field name="activity_ids" widget="mail_activity"/>' +
                '</div>' +
            '</form>',
        res_id: 2,
        mockRPC: function (route, args) {
            if (args.method === 'read' && args.model === 'mail.activity') {
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
        activity_type_id: 2,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
    assert.expect(5);
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

    var checkReadArgs = false;
    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
            if (route === '/web/dataset/call_kw/mail.activity/action_feedback') {
                assert.ok(_.isEqual(args.args[0], [1]), "should call 'action_feedback' for id 1");
                assert.strictEqual(args.kwargs.feedback, 'everything is ok',
                    "the feedback should be sent correctly");
                return $.when();
            }
            if (args.method === 'read' && args.model === 'partner' && checkReadArgs) {
                assert.deepEqual(args.args[1], ['activity_ids', 'message_ids', 'display_name'],
                    "should only read the mail fields");
            }
            return this._super.apply(this, arguments);
        },
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    context: {
                        default_res_id: 2,
                        default_res_model: "partner",
                        default_previous_activity_type_id: 2,
                    },
                    res_id: false,
                    res_model: 'mail.activity',
                    type: 'ir.actions.act_window',
                    target: "new",
                    view_mode: "form",
                    view_type: "form",
                    views: [[false, "form"]],
                }, "should do a do_action with correct parameters");
                checkReadArgs = true; // should re-read the activities when closing the dialog
                event.data.options.on_close();
            },
        },
    });
    //Schedule next activity
    form.$('.o_mail_activity .o_activity_done[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity_feedback.popover').length, 1,
        "a feedback popover should be visible");
    $('.o_mail_activity_feedback.popover textarea').val('everything is ok'); // write a feedback
    form.$('.o_activity_popover_done_next').click(); // schedule next activity
    form.destroy();
});

QUnit.test('form activity widget: schedule activity does not discard changes', function (assert) {
    assert.expect(1);

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
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
    assert.expect(14);

    var self = this;

    var nbReads = 0;
    var messages = [];
    this.data.partner.records[0].activity_ids = [1, 2];
    this.data.partner.records[0].activity_state = 'today';
    this.data['mail.activity'].records = [{
        id: 1,
        display_name: "An activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 1,
    }, {
        id: 2,
        display_name: "A second activity",
        date_deadline: moment().format("YYYY-MM-DD"), // now
        state: "today",
        user_id: 2,
        activity_type_id: 1,
    }];

    var form = createView({
        View: FormView,
        model: 'partner',
        data: this.data,
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
                messages.push({
                    attachment_ids: [],
                    author_id: ["1", "John Doe"],
                    body: "The activity has been done",
                    date: moment("2016-12-20 09:35:40"),
                    displayed_author: "John Doe",
                    id: 1,
                    is_note: true,
                });
                route = '/web/dataset/call_kw/mail.activity/unlink';
                args.method = 'unlink';
            } else if (route === '/web/dataset/call_kw/partner/read') {
                nbReads++;
                if (nbReads === 1) { // first read
                    assert.strictEqual(args.args[1].length, 4, 'should read all fiels the first time');
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
        intercepts: {
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when(messages));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            }
        },
    });

    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 2,
        "there should be two activities");

    // remove activity 1
    form.$('.o_mail_activity .o_activity_unlink[data-activity-id=1]').click();
    assert.strictEqual(form.$('.o_mail_activity .o_thread_message').length, 1,
        "there should be one remaining activity");
    assert.ok(!form.$('.o_mail_activity .o_activity_unlink[data-activity-id=1]').length,
        "activity 1 should have been removed");

    // mark activity done
    assert.ok(!form.$('.o_mail_thread .o_thread_message').length,
        "there should be no chatter message");
    form.$('.o_mail_activity .o_activity_done[data-activity-id=2]').click();
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
                    // hack: the server creates a new follower each time the subtypes are updated
                    // so we need here to mock that weird behavior here, as the followers widget
                    // relies on that behavior
                    this.data.partner.records[0].message_follower_ids = [2];
                    followers[0].id = 2;
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
    assert.ok(form.$('.o_subtypes_list.open').length, 'dropdown should be opened');
    form.$('.o_subtypes_list .o_subtype input[data-id=2]').click(); // uncheck second subtype
    assert.ok(form.$('.o_subtypes_list.open').length, 'dropdown should remain opened');
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
            if (route === '/mail/read_followers') {
                return $.when({
                    followers: [],
                    subtypes: [],
                });
            }
            return this._super(route, args);
        },
        intercepts: {
            chat_manager_ready: function (event) {
                // we delay the return of the chat_manager ready event
                event.data.callback(def);
            },
            get_messages: function (event) {
                event.stopPropagation();
                event.data.callback($.when([{
                    attachment_ids: [],
                    body: "",
                    date: moment("2016-12-20 09:35:40"),
                    id: 34,
                    res_id: 3,
                    author_id: ["3", "Fu Ck Mil Grom"],
                }]));
            },
            get_bus: function (event) {
                event.stopPropagation();
                event.data.callback(new Bus());
            },
            get_session: function (event) {
                event.stopPropagation();
                event.data.callback({uid: 1});
            },
        },
    });

    form.destroy();
    // here, the chat_manager system is ready, and the chatter can try to render
    // itself. We simply make sure here that no crashes occur (since the form
    // view is destroyed, all rpcs will be dropped, and many other mechanisms
    // relying on events will not work, such as _getBus)
    def.resolve();
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
    var nameGottenIds = [[12], [12, 14]];

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
            if (route === "/web/dataset/call_kw/partner_type/name_get") {
                assert.deepEqual(args.args[0], nameGottenIds.shift(),
                    "partner with email should be name_get'ed");
            }
            else if (args.method ==='read' && args.model === 'partner_type') {
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
        assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] span.o_tag_color_0').length, 2,
            "the second tag should be present");

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
    assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] span.o_tag_color_0').length, 1,
        "should contain one tag");

    // add an other existing tag
    var $input = form.$('.o_field_many2manytags input');
    $input.click(); // opens the dropdown
    $input.autocomplete('widget').find('li:first').click(); // add 'silver'

    assert.strictEqual($('.modal-body.o_act_window').length, 1,
        "there should be one modal opened to edit the empty email");
    assert.strictEqual($('.modal-body.o_act_window input[name="display_name"]').val(), "silver",
        "the opened modal should be a form view dialog with the partner_type 14");
    assert.strictEqual($('.modal-body.o_act_window input[name="email"]').length, 1,
        "there should be an email field in the modal");

    // set the email and save the modal (will rerender the form view)
    $('.modal-body.o_act_window input[name="email"]').val('coucou@petite.perruche').trigger('input');
    $('.modal-footer .btn-primary').click();

    assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] span.o_tag_color_0').length, 2,
        "should contain the second tag");
    // should have read [14] three times: when opening the dropdown, when opening the modal, and
    // after the save
    assert.verifySteps([[12], [14], [14], [14]]);

    form.destroy();
});

});
});
