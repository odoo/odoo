odoo.define('mail.chatter_tests', function (require) {
"use strict";

var Bus = require('web.Bus');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');

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
    assert.expect(2);

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
            if (route === '/mail/read_followers') {
                return $.when({
                    followers: [],
                    subtypes: [],
                });
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

    assert.ok(form.$('.o_chatter').length, "there should be a chatter widget");
    form.$buttons.find('.o_form_button_create').click();
    assert.ok(!form.$('.o_chatter').length, "there should not be a chatter widget");
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
            if (route === '/web/dataset/call_kw/mail.activity/action_done') {
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
    assert.strictEqual(rpcCount, 2, 'no RPC should be done as the activities are now in cache');

    // mark activity as done
    $record.find('.o_mark_as_done').click();
    $record = kanban.$('.o_kanban_record').first(); // the record widget has been reset
    assert.strictEqual(rpcCount, 4, 'should have done an RPC to mark activity as done, and a read');
    assert.ok($record.find('.o_mail_activity .o_activity_color_default:not(.o_activity_color_today)').length,
        "activity widget should have been updated correctly");
    assert.strictEqual($record.find('.o_mail_activity.open').length, 1,
        "dropdown should remain open when marking an activity as done");
    assert.strictEqual($record.find('.o_no_activity').length, 1, "should have no activity scheduled");

    kanban.destroy();
});

QUnit.test('chatter: post, receive and star messages', function (assert) {
    assert.expect(22);

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
            if (route === "/web/dataset/call_kw/partner/message_get_suggested_recipients") {
                return $.when({2: []});
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
            } else if (route === '/web/dataset/call_kw/mail.activity/action_done') {
                assert.ok(_.isEqual(args.args[0], [2]), "should call 'action_done' for id 2");
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
                    assert.ok(_.isEqual(args.args[1], ['activity_ids']),
                        'should only read the activities after an unlink');
                } else { // third read: after marking an activity done
                    assert.ok(_.isEqual(args.args[1], ['activity_ids', 'message_ids']),
                        'should read the activities and messages after marking an activity done');
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
                    assert.ok(_.isEqual(args.args[1], ['message_follower_ids']),
                        'should only read "message_follower_ids"');
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
});
});
