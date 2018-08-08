odoo.define('mail.thread_window_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {
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
            if (params.debug) {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
            } else {
                self.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = '#qunit-fixture';
            }

            testUtils.addMockEnvironment(widget, params);
            return widget;
        };
    },
    afterEach: function () {
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
}, function () {

    QUnit.module('thread_window');

    QUnit.test('close thread window using ESCAPE key', function (assert) {
        assert.expect(5);

        var parent = this.createParent({
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'channel_fold') {
                    assert.ok(true, "should call channel_fold");
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        });

        // get channel instance to link to thread window
        var channel = parent.call('mail_service', 'getChannel', 1);
        assert.ok(channel, "there should exist a channel locally with ID 1");

        channel.detach();
        assert.strictEqual($('.o_thread_window').length, 1,
            "there should be a thread window that is opened");

        // focus on the thread window and press ESCAPE
        $('.o_thread_window .o_composer_text_field').click();
        assert.strictEqual(document.activeElement,
            $('.o_thread_window .o_composer_text_field')[0],
            "thread window's input should now be focused");

        var upKeyEvent = $.Event( "keyup", { which: 27 });
        $('.o_thread_window .o_composer_text_field').trigger(upKeyEvent);

        assert.strictEqual($('.o_thread_window').length, 0,
            "the thread window should be closed");

        parent.destroy();
    });

    QUnit.test('thread window\'s input can still be focused when the UI is blocked', function (assert) {
        assert.expect(2);

        var parent = this.createParent({
            data: this.data,
            services: this.services,
        });

        var $dom = $('#qunit-fixture');

        // get channel instance to link to thread window
        var channel = parent.call('mail_service', 'getChannel', 1);
        channel.detach();

        var $input = $('<input/>', {type: 'text'}).appendTo($dom);
        $input.focus().click();
        assert.strictEqual(document.activeElement, $input[0],
            "fake input should be focused");

        framework.blockUI();
        // cannot force focus here otherwise the test
        // makes no sense, this test is just about
        // making sure that the code which forces the
        // focus on click is not removed
        $('.o_thread_window .o_composer_text_field').click();
        assert.strictEqual(document.activeElement,
            $('.o_thread_window .o_composer_text_field')[0],
            "thread window's input should now be focused");

        framework.unblockUI();
        parent.destroy();
    });

    QUnit.test('emoji popover should open correctly in thread windows', function (assert) {
        assert.expect(1);

        var parent = this.createParent({
            data: this.data,
            services: this.services,
        });

        // get channel instance to link to thread window
        var channel = parent.call('mail_service', 'getChannel', 1);
        channel.detach();

        var $emojiButton = $('.o_composer_button_emoji');
        $emojiButton.trigger('focusin').focus().click();
        var $popover = $('.o_mail_emoji_container');

        var done = assert.async();
        // Async is needed as the popover focusout hiding is deferred
        setTimeout(function () {
            assert.ok($popover.is(':visible'), "emoji popover should have stayed opened");
            parent.destroy();
            done();
        }, 0);
    });
});
});
