odoo.define('mail.hiddenThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Hidden', {
    beforeEach: function () {
        var self = this;

        // define channel to link to chat window
        this.data = {
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
        // remove thread window dropup appended by mail service
        var $target = $(this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO);
        $target.find('.o_thread_window_dropdown').remove();
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
});

QUnit.test('hidden thread windows dropdown when not enough horizontal space (version 1)', async function (assert) {
    // This test has hard-set global width, so that it does not depend on
    // the width of the screen: at most 2 thread windows visible at the
    // same time, and additional thread windows are in hidden while and
    // still showing 2 visible thread windows. It assumes that the width
    // of the 'hidden thread window' button is less than the width of a
    // single thread window.
    assert.expect(13);

    testUtils.mock.patch(this.services.mail_service, {
        HIDDEN_THREAD_WINDOW_DROPDOWN_BUTTON_WIDTH: 100,
        THREAD_WINDOW_WIDTH: 300,
        _getGlobalWidth: function () { return 800; },
    });

    var channels = [];
    for (var i = 0; i < 3; i++) {
        channels.push({
            id: i,
            channel_type: 'channel',
            name: "channel" + i,
        });
    }

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: channels,
        },
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();
    parent.call('mail_service', 'getChannel', 0).detach();
    parent.call('mail_service', 'getChannel', 1).detach();
    await testUtils.nextTick();

    var $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');

    assert.strictEqual($visibleThreadWindows.length, 2,
        "should have 2 thread windows visible (as many as available slots)");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="0"]').length, 1,
        "the thread window with ID 0 should be visible");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="1"]').length, 1,
        "the thread window with ID 1 should be visible");
    assert.strictEqual($('.o_thread_window.o_hidden').length, 0,
        "there should be no hidden thread when less or exactly as many as available slots");
    assert.strictEqual($('.o_thread_window_dropdown').length, 0,
        "there should be no thread window dropdown when all thread windows are visible");

    // detach a channel so that it exceeds available slots
    parent.call('mail_service', 'getChannel', 2).detach();
    await testUtils.nextTick();
    // update list of visible thread windows
    $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');

    assert.strictEqual($visibleThreadWindows.length, 2,
        "should have as many thread window visible as available slots");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="0"]').length, 1,
        "the thread window with ID 0 should be visible");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="2"]').length, 1,
        "the thread window with ID 2 should be visible (swapped with ID 1)");
    assert.strictEqual($('.o_thread_window.o_hidden').length, 1,
        "there should be a hidden thread when more windows than available slots");
    assert.strictEqual($('.o_thread_window.o_hidden').data('thread-id'), 1,
        "hidden thread window should be thread window with ID 1 (swapped with ID 2)");
    var $hiddenDropdown = $('.o_thread_window_dropdown');
    assert.strictEqual($hiddenDropdown.length, 1,
        "there should be a thread window dropdown");
    assert.strictEqual($('.o_thread_window_dropdown_toggler').text().trim(), "1",
        "should display that there is one hidden thread window");
    assert.strictEqual($hiddenDropdown.find('.o_thread_window_header[data-thread-id="1"]').length,
        1, "should contain thread window with ID 1 in hidden dropdown menu");

    parent.destroy();
    testUtils.mock.unpatch(this.services.mail_service);
});

QUnit.test('hidden thread windows dropdown when not enough horizontal space (version 2)', async function (assert) {
    // This is almost the same test as the one before, except there are
    // at most 3 thread windows visible, and 2 thread windows are visible
    // when it shows the 'hidden thread window' button.
    // This case occurs when the amount of available slots depends on
    // whether the hidden button should be displayed or not
    // Example:
    //      - global width of 800px
    //      - button width of 100px
    //      - thread width of 250px
    //
    // Without button: 3 thread windows (3*250px = 750px < 800px)
    //    With button: 2 thread windows (2*250px + 100px = 600px < 800px)
    assert.expect(16);

    testUtils.mock.patch(this.services.mail_service, {
        HIDDEN_THREAD_WINDOW_DROPDOWN_BUTTON_WIDTH: 100,
        THREAD_WINDOW_WIDTH: 250,
        _getGlobalWidth: function () { return 800; },
    });

    var channels = [];
    for (var i = 0; i < 4; i++) {
        channels.push({
            id: i,
            channel_type: 'channel',
            name: "channel" + i,
        });
    }

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: channels,
        },
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();
    parent.call('mail_service', 'getChannel', 0).detach();
    parent.call('mail_service', 'getChannel', 1).detach();
    parent.call('mail_service', 'getChannel', 2).detach();
    await testUtils.nextTick();

    var $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');

    assert.strictEqual($visibleThreadWindows.length, 3,
        "should have 3  thread windows visible (as many as available slots)");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="0"]').length, 1,
        "the thread window with ID 0 should be visible");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="1"]').length, 1,
        "the thread window with ID 1 should be visible");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="2"]').length, 1,
        "the thread window with ID 2 should be visible");
    assert.strictEqual($('.o_thread_window.o_hidden').length, 0,
        "there should be no hidden thread when exactly as many as available slots");
    assert.strictEqual($('.o_thread_window_dropdown').length, 0,
        "there should be no thread window dropdown when all thread windows are visible");

    // detach a channel so that it exceeds available slots
    parent.call('mail_service', 'getChannel', 3).detach();
    await testUtils.nextTick();
    // update list of visible thread windows
    $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');

    assert.strictEqual($visibleThreadWindows.length, 2,
        "should have 2 thread windows visible (as many as available slots)");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="0"]').length, 1,
        "the thread window with ID 0 should be visible");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="3"]').length, 1,
        "the thread window with ID 3 should be visible (swapped with IDs 1 and 2)");
    assert.strictEqual($('.o_thread_window.o_hidden').length, 2,
        "there should be two hidden thread when more windows than available slots");
    assert.strictEqual($('.o_thread_window.o_hidden[data-thread-id="1"]').length, 1,
        "thread window with ID 1 should be hidden");
    assert.strictEqual($('.o_thread_window.o_hidden[data-thread-id="2"]').length, 1,
        "thread window with ID 2 should be hidden");
    var $hiddenDropdown = $('.o_thread_window_dropdown');
    assert.strictEqual($hiddenDropdown.length, 1,
        "there should be a thread window dropdown");
    assert.strictEqual($('.o_thread_window_dropdown_toggler').text().trim(), "2",
        "should display that there is 2 hidden thread windows");
    assert.strictEqual($hiddenDropdown.find('.o_thread_window_header[data-thread-id="1"]').length,
        1, "should contain thread window with ID 1 in hidden dropdown menu");
    assert.strictEqual($hiddenDropdown.find('.o_thread_window_header[data-thread-id="2"]').length,
        1, "should contain thread window with ID 2 in hidden dropdown menu");

    parent.destroy();
    testUtils.mock.unpatch(this.services.mail_service);
});

QUnit.test('receive message from hidden thread window', async function (assert) {
    // This is almost the same test as the one before, except there are
    // at most 3 thread windows visible, and 2 thread windows are visible
    // when it shows the 'hidden thread window' button.
    // This case occurs when the amount of available slots depends on
    // whether the hidden button should be displayed or not
    // Example:
    //      - global width of 400px
    //      - button width of 100px
    //      - thread width of 250px
    //
    // Without button: 1 thread window (250px < 800px)
    //    With button: 1 thread window (250px + 100px = 350px < 400px)
    assert.expect(7);

    testUtils.patch(this.services.mail_service, {
        HIDDEN_THREAD_WINDOW_DROPDOWN_BUTTON_WIDTH: 100,
        THREAD_WINDOW_WIDTH: 250,
        _getGlobalWidth: function () { return 400; },
    });

    var channels = [{
        id: 1,
        channel_type: 'channel',
        name: "channel" + 1,
    }, {
        id: 2,
        channel_type: 'channel',
        name: "channel" + 2,
    }];

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: channels,
        },
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();

    // detach channel 2 first, so that chanel 1 is open and channel 2 is hidden
    parent.call('mail_service', 'getChannel', 2).detach();
    parent.call('mail_service', 'getChannel', 1).detach();
    await testUtils.nextTick();

    var $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');

    assert.strictEqual($visibleThreadWindows.length, 1,
        "should have 1 thread windows visible (as many as available slots)");
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="1"]').length, 1,
        "the thread window with ID 1 should be visible");
    assert.strictEqual($('.o_thread_window.o_hidden[data-thread-id="2"]').length, 1,
        "the thread window with ID 2 should be hidden");
    assert.strictEqual(
        $('.o_thread_window_dropdown .o_total_unread_counter').text().trim(),
        "",
        "should have no unread counter on hidden dropup menu");

    // simulate receiving a message in channel ID 2
    var messageData = {
        author_id: [5, "Someone else"],
        body: "<p>Test message</p>",
        id: 1,
        model: 'mail.channel',
        res_id: 2,
        channel_ids: [2],
    };
    var notification = [[false, 'mail.channel', 2], messageData];
    parent.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    $visibleThreadWindows = $('.o_thread_window:not(.o_thread_window_dropdown, .o_hidden)');
    assert.strictEqual($visibleThreadWindows.filter('[data-thread-id="1"]').length, 1,
        "the thread window with ID 1 should stay visible");
    assert.strictEqual($('.o_thread_window.o_hidden[data-thread-id="2"]').length, 1,
        "the thread window with ID 2 should stay hidden");
    assert.strictEqual(
        $('.o_thread_window_dropdown .o_total_unread_counter').text().trim(),
        "1",
        "should have unread counter of 1 on hidden dropup menu");

    parent.destroy();
    testUtils.unpatch(this.services.mail_service);
});

});
});
});
