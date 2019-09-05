odoo.define('mail.basicThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var FormView = require('web.FormView');
var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Basic', {
    beforeEach: function () {
        var self = this;

        // define channel to link to chat window
        this.data = {
            'mail.channel': {
                fields: {
                    name: {
                        string: "Name",
                        type: "char",
                        required: true,
                    },
                    channel_type: {
                        string: "Channel Type",
                        type: "selection",
                    },
                    channel_message_ids: {
                        string: "Messages",
                        type: "many2many",
                        relation: 'mail.message'
                    },
                    message_unread_counter: {
                        string: "Amount of Unread Messages",
                        type: "integer"
                    },
                },
                records: [],
            },
            'mail.message': {
                fields: {},
                records: [],
            },
            initMessaging: {
                channel_slots: {
                    channel_channel: [{
                        id: 1,
                        channel_type: "channel",
                        name: "general",
                    }],
                },
            },
        };
        this.services = mailTestUtils.getMailServices();
        this.ORIGINAL_THREAD_WINDOW_APPENDTO = this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO;

        this.createParent = function (params) {
            var widget = new Widget();

            // in non-debug mode, append thread windows in qunit-fixture
            // note that it does not hide thread window because it uses fixed
            // position, and qunit-fixture uses absolute...
            if (params.debug) {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
            } else {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = '#qunit-fixture';
            }

            testUtils.mock.addMockEnvironment(widget, params);
            return widget;
        };
    },
    afterEach: function () {
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
});

QUnit.test('basic rendering thread window', async function (assert) {
    assert.expect(10);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    await testUtils.nextTick();
    // detach channel 1, so that it opens corresponding thread window.
    var result = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    result.detach();

    await testUtils.nextTick();
    var $threadWindow = $('.o_thread_window');
    assert.strictEqual($threadWindow.length, 1,
        "thread window should be open");
    assert.strictEqual($threadWindow.data('thread-id'), 1,
        "thread window should be related to thread ID 1");

    var $header = $threadWindow.find('.o_thread_window_header');
    assert.strictEqual($header.length, 1,
        "thread window should have a header");

    var $title = $header.find('.o_thread_window_title');
    assert.strictEqual($title.length, 1,
        "thread window should have a title in the header");
    assert.strictEqual($title.text().trim(), "#general",
        "should have the title of the general channel");

    var $buttons = $header.find('.o_thread_window_buttons');
    assert.strictEqual($buttons.length, 1,
        "should have buttons in the header of the thread window");
    assert.strictEqual($buttons.find('.o_thread_window_expand').length, 1,
        "should have a button to expand the thread window");
    assert.strictEqual($buttons.find('.o_thread_window_close').length, 1,
        "should have a button to close the thread window");

    assert.strictEqual($threadWindow.find('.o_mail_thread').length, 1,
        "should display the content of the general channel in the thread window");
    assert.strictEqual($threadWindow.find('.o_thread_composer').length, 1,
        "should display a composer in the thread window");

    parent.destroy();
});

QUnit.test('close thread window using ESCAPE key', async function (assert) {
    assert.expect(5);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fold') {
                assert.ok(true, "should call channel_fold");
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    });
    await testUtils.nextTick();

    // get channel instance to link to thread window
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    assert.ok(channel, "there should exist a channel locally with ID 1");

    channel.detach();
    await testUtils.nextTick();
    assert.strictEqual($('.o_thread_window').length, 1,
        "there should be a thread window that is opened");

    // focus on the thread window and press ESCAPE
    await testUtils.dom.click($('.o_thread_window .o_composer_text_field'));
    assert.strictEqual(document.activeElement,
        $('.o_thread_window .o_composer_text_field')[0],
        "thread window's input should now be focused");

    var upKeyEvent = $.Event( "keyup", { which: 27 });
    await testUtils.dom.triggerEvents($('.o_thread_window .o_composer_text_field'), [upKeyEvent]);

    assert.strictEqual($('.o_thread_window').length, 0,
        "the thread window should be closed");

    parent.destroy();
});

QUnit.test('thread window\'s input can still be focused when the UI is blocked', async function (assert) {
    assert.expect(2);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    var $dom = $('#qunit-fixture');

    // get channel instance to link to thread window
    await testUtils.nextTick();
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();
    var $input = $('<input/>', {type: 'text'}).appendTo($dom);
    await testUtils.dom.click($input.focus());
    assert.strictEqual(document.activeElement, $input[0],
        "fake input should be focused");

    framework.blockUI();
    // cannot force focus here otherwise the test
    // makes no sense, this test is just about
    // making sure that the code which forces the
    // focus on click is not removed
    await testUtils.dom.click($('.o_thread_window .o_composer_text_field'));
    assert.strictEqual(document.activeElement,
        $('.o_thread_window .o_composer_text_field')[0],
        "thread window's input should now be focused");

    framework.unblockUI();
    parent.destroy();
    $input.remove();
});

QUnit.test('emoji popover should open correctly in thread windows', async function (assert) {
    assert.expect(1);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    // get channel instance to link to thread window
    await testUtils.nextTick();
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();
    var $emojiButton = $('.o_composer_button_emoji');
    await testUtils.dom.click($emojiButton.trigger('focusin').focus());
    var $popover = $('.o_mail_emoji_container');

    assert.ok($popover.is(':visible'), "emoji popover should have stayed opened");
    parent.destroy();
});

QUnit.test('do not increase unread counter when receiving message with myself as author', async function (assert) {
    assert.expect(4);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 }
    });

    // get channel instance to link to thread window
    await testUtils.nextTick();
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();
    var threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

    assert.strictEqual(threadWindowHeaderText, "#general",
        "thread window header text should not have any unread counter initially");
    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should have unread counter to 0 initially");

    // simulate receiving message from myself
    var messageData = {
        author_id: [3, "Myself"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [1],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);

    await testUtils.nextTick();
    threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

    assert.strictEqual(threadWindowHeaderText, "#general",
        "thread window header text should not have any unread counter after receiving my message");
    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should not have incremented its unread counter after receiving my message");

    parent.destroy();
});

QUnit.test('do not increment unread counter with focus on thread window', async function (assert) {
    // 'hard' focus means that the user has clicked on the thread window in
    // order to set the focus on it.
    assert.expect(2);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 }
    });

    // get channel instance to link to thread window
    await testUtils.nextTick();
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();

    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should have unread counter to 0 initially");

    // hard focus on thread window composer
    await testUtils.dom.click($('.o_composer_text_field'));

    // simulate receiving message from someone else
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [1],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    assert.strictEqual(channel.getUnreadCounter(), 0,
        "thread should not have incremented its unread counter after receiving the message");

    parent.destroy();
});

QUnit.test('do not mark as read the newly open thread window from received message', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records = [{
        id: 2,
        name: "DM",
        channel_type: "chat",
        message_unread_counter: 0,
    }];

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_join_and_get_info') {
                this.data['mail.channel'].records[0].state = 'open';
                this.data['mail.channel'].records[0].is_minimized = true;
                return Promise.resolve(this.data['mail.channel'].records[0]);
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual($('.o_thread_window').length, 0,
        "no thread window should be open initially");

    // simulate receiving message from someone else in DM
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [2],
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    // Unread counter is obtained from fetched channel data, because this is
    // a new message from a new channel.
    this.data['mail.channel'].records[0].message_unread_counter++;
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();
    var $threadWindow = $('.o_thread_window');
    assert.strictEqual($threadWindow.length, 1,
        "a thread window should be open after receiving a new message on a new DM chat");
    assert.strictEqual($threadWindow.data('thread-id'), 2,
        "open thread window should be related to DM chat");
    assert.strictEqual($threadWindow.find('.o_thread_window_title').text().replace(/\s/g, ''), '#DM(1)',
        "open DM chat window should have one unread message");

    await testUtils.dom.click($threadWindow.find('.o_thread_composer'));
    assert.strictEqual($threadWindow.find('.o_thread_window_title').text().replace(/\s/g, ''), '#DM',
        "open DM chat window should have message marked as read on composer focus");

    parent.destroy();
});

QUnit.test('show document link of message linked to a document', async function (assert) {
    assert.expect(6);

    this.data['mail.channel'].records = [{
        id: 2,
        name: "R&D Tasks",
        channel_type: "channel",
    }];
    this.data['mail.message'].records.push({
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 40,
        model: 'some.document',
        record_name: 'Some Document',
        res_id: 10,
        channel_ids: [2],
    });

    this.data.initMessaging.channel_slots.channel_channel.push({
        id: 2,
        name: "R&D Tasks",
        channel_type: "public",
    });

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    });

    assert.strictEqual($('.o_thread_window').length, 0,
        "no thread window should be open initially");

    // get channel instance to link to thread window
    await testUtils.nextTick();
    var channel = parent.call('mail_service', 'getChannel', 2);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();

    var $threadWindow = $('.o_thread_window');
    assert.strictEqual($threadWindow.length, 1,
        "a thread window should be open");
    assert.strictEqual($threadWindow.find('.o_thread_window_title').text().trim(),
        "#R&D Tasks",
        "should be thread window of correct channel");
    assert.strictEqual($threadWindow.find('.o_thread_message').length, 1,
        "should contain a single message in thread window");
    assert.ok($threadWindow.find('.o_mail_info').text().replace(/\s/g, "").indexOf('Someoneelse') !== -1,
        "message should be from 'Someone else' user");
    assert.ok($threadWindow.find('.o_mail_info').text().replace(/\s/g, "").indexOf('onSomeDocument') !== -1,
        "message should link to 'Some Document'");

    parent.destroy();
});

QUnit.test('do not autofocus chat window on receiving new direct message', async function (assert) {
    // Receiving a message doesn't make other input loose focus
    assert.expect(3);

    this.data.partner = {
        fields: {
            display_name: { string: "Displayed name", type: "char" },
        },
        records: [{
            id: 1,
            display_name: "first record",
        }],
    };

    this.data['mail.channel'].records = [{
        id: 2,
        name: "DM",
        channel_type: "chat",
        message_unread_counter: 0,
        direct_partner: [{ id: 666, name: 'DemoUser1', im_status: '' }],
    }];

    var form = await testUtils.createView({
        View: FormView,
        model: 'partner',
        data: this.data,
        arch: '<form string="Partners">' +
                    '<field name="display_name" />' +
                '</form>',
        res_id: 1,
        services: mailTestUtils.getMailServices(),
        viewOptions: {
            mode: 'edit',
        },
        mockRPC: function (route, args) {
            if (args.method === 'channel_join_and_get_info') {
                return Promise.resolve(this.data['mail.channel'].records[0]);
            }
            return this._super.apply(this, arguments);
        }
    });

    var $formInput = form.$('input[name=display_name]');
    $formInput.focus();

    assert.equal(document.activeElement, $formInput[0],
        'The form input should have the focus');

    // simulate receiving message from someone else
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 1,
        channel_ids: [2],
    };

    this.data['mail.message'].records.push(messageData);
    var notification = [[false, 'mail.channel', 2], messageData];
    form.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();
    assert.ok($('.o_thread_window.o_in_home_menu').length,
        'Chat window is opened');

    assert.equal(document.activeElement, $formInput[0],
        'The form input should have kept the focus on message received');

    form.destroy();
});

QUnit.test('do not auto-focus chat window on receiving new message from new DM', async function (assert) {
    assert.expect(10);

    var self = this;
    this.data['mail.channel'].records = [{
        id: 2,
        name: "DM",
        channel_type: "chat",
        message_unread_counter: 1,
        direct_partner: [{ id: 666, name: 'DemoUser1', im_status: '' }],
        is_minimized: false,
        state: 'open',
    }];

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_join_and_get_info') {
                return Promise.resolve(_.extend({}, self.data['mail.channel'].records[0], { info: 'join' }));
            }
            if (args.method === 'channel_minimize') {
                _.extend(self.data['mail.channel'].records[0], {
                    is_minimized: true,
                    state: 'open',
                });
            }
            if (args.method === 'channel_seen') {
                throw new Error('should not mark channel as seen');
            }
            return this._super.apply(this, arguments);
        }
    });

    assert.strictEqual($('.o_thread_window').length, 0,
        "should not have any DM window open");

    // simulate receiving message from someone else
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 2,
        model: 'mail.channel',
        res_id: 2,
        channel_ids: [2],
    };
    this.data['mail.message'].records.push(messageData);
    var notification = [[false, 'mail.channel', 2], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    assert.strictEqual($('.o_thread_window').length, 1,
        "should have DM window open");
    assert.strictEqual($('.o_thread_window .o_input:focus').length, 0,
        "thread window should not have the focus on auto-open");
    assert.ok($('.o_thread_window .o_thread_window_title').text().indexOf('(1)') !== -1,
        "DM should display one unread message");

    // simulate receiving join DM notification (cross-tab synchronization)
    var dmInfo = _.extend({}, self.data['mail.channel'].records[0], {
        info: 'join',
        is_minimized: false,
        state: 'open',
    });
    notification = [[false, 'res.partner', 3], dmInfo];
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    assert.strictEqual($('.o_thread_window').length, 1,
        "should still have DM window open after receiving DM info from polling");
    assert.strictEqual($('.o_thread_window .o_input:focus').length, 0,
        "thread window should still not have the focus after receiving DM info from polling");
    assert.ok($('.o_thread_window .o_thread_window_title').text().indexOf('(1)') !== -1,
        "DM should still display one unread message after receiving DM info from polling");

    // simulate receiving detached DM notification (cross-tab synchronization)
    notification = [[false, 'res.partner', 3], self.data['mail.channel'].records[0]];
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    assert.strictEqual($('.o_thread_window').length, 1,
        "should still have DM open after receiving detached info from polling");
    assert.strictEqual($('.o_thread_window .o_input:focus').length, 0,
        "thread window should still not have the focus after receiving detached info from polling");
    assert.ok($('.o_thread_window .o_thread_window_title').text().indexOf('(1)') !== -1,
        "DM should not still have one unread message after receiving detached info from polling");

    parent.destroy();
});

QUnit.test('out-of-office status in thread window', async function (assert) {
    assert.expect(1);
    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                name: "DM",
                channel_type: "chat",
                message_unread_counter: 0,
                direct_partner: [{ id: 666, name: 'DemoUser1', im_status: 'online', out_of_office_message: 'Please don\'t disturb'}],
            }],
        },
    };
    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();

    // detach channel 1, so that it opens corresponding thread window.
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();

    var $threadWindow = $('.o_thread_window');
    assert.containsOnce($threadWindow, '.o_out_of_office_text');

    parent.destroy();
});

QUnit.test('no out-of-office status in thread window', async function (assert) {
    assert.expect(1);
    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                name: "DM",
                channel_type: "chat",
                message_unread_counter: 0,
                direct_partner: [{ id: 666, name: 'DemoUser1', im_status: 'online'}],
            }],
        },
    };
    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();

    // detach channel 1, so that it opens corresponding thread window.
    var channel = parent.call('mail_service', 'getChannel', 1);
    await testUtils.nextTick();
    channel.detach();
    await testUtils.nextTick();

    var $threadWindow = $('.o_thread_window');
    assert.containsNone($threadWindow, '.o_out_of_office_text');

    parent.destroy();
});

QUnit.test('auto-update out-of-office info on im_status change', async function (assert) {
    assert.expect(5);

    var imStatusDefs = [testUtils.makeTestPromise(), testUtils.makeTestPromise()];
    var channelInfoDefs = [testUtils.makeTestPromise(), testUtils.makeTestPromise()];
    var timeoutMock = mailTestUtils.patchMailTimeouts();
    var step = 0;

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                name: "DM",
                channel_type: "chat",
                message_unread_counter: 0,
                direct_partner: [{
                    id: 666,
                    name: 'DemoUser1',
                    im_status: 'online',
                }],
            }],
        },
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (route === '/longpolling/im_status') {
                step++;
                if (step === 1) {
                    imStatusDefs[0].resolve();
                    return Promise.resolve([
                        {
                            id: 666,
                            im_status: 'leave',
                        },
                    ]);
                } else if (step === 2) {
                    imStatusDefs[1].resolve();
                    return Promise.resolve([
                        {
                            id: 666,
                            im_status: 'online',
                        },
                    ]);
                }
            }
            if (args.method === 'channel_info') {
                if (step === 1) {
                    channelInfoDefs[0].resolve();
                    return Promise.resolve([{
                        id: 1,
                        direct_partner: [{
                            out_of_office_message: "Leave me alone",
                            out_of_office_date_end: false,
                        }],
                    }]);
                }
                else if (step === 2) {
                    channelInfoDefs[1].resolve();
                    return Promise.resolve([{
                        id: 1,
                        direct_partner: [{
                            out_of_office_message: false,
                            out_of_office_date_end: false,
                        }],
                    }]);
                }
            }
            return this._super.apply(this, arguments);
        },
    });
    await testUtils.nextTick();

    // detach channel 1, so that it opens corresponding thread window.
    parent.call('mail_service', 'getChannel', 1).detach();
    await testUtils.nextTick();

    assert.containsNone($, '.o_out_of_office',
        "should contain no out of office section on chat window initially");

    timeoutMock.addTime(51*1000); // wait for next im status fetch

    await Promise.all([imStatusDefs[0], channelInfoDefs[0]]);
    await testUtils.nextTick();
    assert.containsOnce($, '.o_out_of_office',
        "should contain out of office section on chat window");
    assert.containsOnce($, '.o_out_of_office > .o_out_of_office_text',
        "should contain out of office text on chat window");
    assert.ok(
        $('.o_out_of_office > .o_out_of_office_text')
            .text()
            .replace(/\s/g, "")
            .indexOf("Leavemealone") !== -1,
        "should contain out of office text on chat window");
    timeoutMock.addTime(51*1000); // wait for next im status fetch

    await Promise.all([imStatusDefs[1], channelInfoDefs[1]]);
    await testUtils.nextTick();
    assert.containsNone($, '.o_out_of_office',
        "should no longer contain out of office section on chat window");

    timeoutMock.runPendingTimeouts();
    parent.destroy();
});

QUnit.test('receive 2 new DM messages in quick succession (no chat window initially)', async function (assert) {
    assert.expect(3);

    const self = this;
    this.data['mail.channel'].records = [{
        channel_type: "chat",
        direct_partner: [{
            id: 5,
            name: 'Someone else',
            im_status: 'online',
        }],
        id: 10,
        is_minimized: false,
        message_unread_counter: 1,
        name: "DM",
        state: 'open',
    }];

    this.data.initMessaging.channel_slots = {
        channel_direct_message: [{
            channel_type: 'chat',
            direct_partner: [{
                id: 5,
                name: 'Someone else',
                im_status: 'online',
            }],
            id: 10,
            message_unread_counter: 0,
            name: "DM",
        }],
    };

    const parent = this.createParent({
        data: this.data,
        mockRPC(route, args) {
            if (args.method === 'channel_minimize') {
                Object.assign(self.data['mail.channel'].records[0], {
                    is_minimized: true,
                    state: 'open',
                });
            }
            return this._super(...arguments);
        },
        services: this.services,
        session: {
            partner_id: 3,
        },
    });

    await testUtils.nextTick();
    assert.containsNone(
        $,
        '.o_thread_window',
        "should not have any DM window open");

    // simulate receiving 2 new messages from someone else in quick succession
    const messageData1 = {
        author_id: [5, "Someone else"],
        body: "<p>Test message1</p>",
        channel_ids: [10],
        id: 2,
        model: 'mail.channel',
        res_id: 10,
    };
    this.data['mail.message'].records.push(messageData1);
    const notification1 = [[false, 'mail.channel', 2], messageData1];
    parent.call('bus_service', 'trigger', 'notification', [notification1]);
    // simulate short delay for receiving new message
    await testUtils.nextMicrotaskTick();
    const messageData2 = {
        author_id: [5, "Someone else"],
        body: "<p>Test message2</p>",
        channel_ids: [10],
        id: 3,
        model: 'mail.channel',
        res_id: 10,
    };
    this.data['mail.message'].records.push(messageData2);
    const notification2 = [[false, 'mail.channel', 2], messageData2];
    parent.call('bus_service', 'trigger', 'notification', [notification2]);
    await testUtils.nextTick();
    assert.containsOnce(
        $,
        '.o_thread_window',
        "should have DM window open");
    assert.containsN(
        $('.o_thread_window'),
        '.o_thread_message',
        2,
        "should have 2 messages in chat window");

    parent.destroy();
});

QUnit.test('non-deletable message attachments', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records = [{
        id: 1,
        name: "General",
        channel_type: 'channel',
    }];
    this.data['mail.message'].records = [{
        attachment_ids: [{
            filename: "text.txt",
            id: 250,
            mimetype: 'text/plain',
            name: "text.txt",
        }, {
            filename: "image.png",
            id: 251,
            mimetype: 'image/png',
            name: "image.png",
        }],
        author_id: [5, "Demo User"],
        body: "<p>test</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        record_name: "general",
        res_id: 1,
    }];
    const parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();
    const channel = parent.call('mail_service', 'getChannel', 1);
    channel.detach();
    await testUtils.nextTick();
    assert.containsOnce(
        $,
        '.o_thread_window',
        "a thread window should be open");
    assert.containsN(
        $('.o_thread_window'),
        '.o_attachment',
        2,
        "thread window should have 2 attachments");
    assert.containsNone(
        $('.o_thread_window .o_attachment'),
        'o_attachment_delete_cross',
        "attachments should not be deletable");

    parent.destroy();
});

});
});
});
