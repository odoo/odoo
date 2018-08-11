odoo.define('mail.thread_window_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var framework = require('web.framework');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {
    beforeEach: function (assert) {
        var self = this;

        this.BEFORE_EACH_ASSERTIONS_NUM = 1;

        assert.strictEqual($('.o_thread_window').length, 0,
            "should have no thread windows open before the test");

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

            testUtils.addMockEnvironment(widget, params);
            return widget;
        };

        /**
         * Patch autocomplete so that we can detect when 'source' or 'select'
         * functions end.
         *
         * @param {Object} params
         * @param {$.Deferred} params.selectDef
         * @param {$.Deferred} params.sourceDef
         */
        this.patchAutocomplete = function (params) {
            var selectDef = params.selectDef;
            var sourceDef = params.sourceDef;
            self.ORIGINAL_AUTOCOMPLETE = $.fn.autocomplete;
            $.fn.autocomplete = function (params) {
                var select = params.select;
                var source = params.source;
                params.select = function () {
                    select.apply(this, arguments);
                    selectDef.resolve();
                };
                params.source = function () {
                    source.apply(this, arguments);
                    sourceDef.resolve();
                };
                return self.ORIGINAL_AUTOCOMPLETE.apply(this, arguments);
            };
        };
        /**
         * Unpatch autocomplete
         */
        this.unpatchAutocomplete = function () {
            $.fn.autocomplete = self.ORIGINAL_AUTOCOMPLETE;
        };
    },
    afterEach: function () {
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
}, function () {

    QUnit.module('ThreadWindow');
    QUnit.test('close thread window using ESCAPE key', function (assert) {
        assert.expect(5 + this.BEFORE_EACH_ASSERTIONS_NUM);

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
        assert.expect(2 + this.BEFORE_EACH_ASSERTIONS_NUM);

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
        assert.expect(1 + this.BEFORE_EACH_ASSERTIONS_NUM);

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

    QUnit.test('do not increase unread counter when receiving message with myself as author', function (assert) {
        assert.expect(4 + this.BEFORE_EACH_ASSERTIONS_NUM);

        var generalChannelID = 1;
        var myselfPartnerID = 44;

        this.data.initMessaging = {
            channel_slots: {
                channel_channel: [{
                    id: generalChannelID,
                    channel_type: 'channel',
                    name: "general",
                }],
            },
        };

        var parent = this.createParent({
            data: this.data,
            services: this.services,
            session: { partner_id: myselfPartnerID }
        });

        // get channel instance to link to thread window
        var channel = parent.call('mail_service', 'getChannel', 1);
        channel.detach();

        var threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

        assert.strictEqual(threadWindowHeaderText, "#general",
            "thread window header text should not have any unread counter initially");
        assert.strictEqual(channel.getUnreadCounter(), 0,
            "thread should have unread counter to 0 initially");

        // simulate receiving message from myself
        var messageData = {
            author_id: [myselfPartnerID, "Myself"],
            body: "<p>Test message</p>",
            id: 2,
            model: 'mail.channel',
            res_id: 1,
            channel_ids: [1],
        };
        var notification = [[false, 'mail.channel', generalChannelID], messageData];
        parent.call('bus_service', 'trigger', 'notification', [notification]);

        threadWindowHeaderText = $('.o_thread_window_header').text().replace(/\s/g, "");

        assert.strictEqual(threadWindowHeaderText, "#general",
            "thread window header text should not have any unread counter after receiving my message");
        assert.strictEqual(channel.getUnreadCounter(), 0,
            "thread should not have incremented its unread counter after receiving my message");

        parent.destroy();
    });

    QUnit.module('Blank ThreadWindow');
    QUnit.test('basic rendering blank thread window', function (assert) {
        assert.expect(5 + this.BEFORE_EACH_ASSERTIONS_NUM);

        var parent = this.createParent({
            data: this.data,
            services: this.services,
        });

        // open blank thread window
        parent.call('mail_service', 'openBlankThreadWindow');

        assert.strictEqual($('.o_thread_window').length, 1,
            "should have a thread window open");
        assert.strictEqual($('.o_thread_window_title').text().trim(),
            "New message",
            "the blank window should have the correct title");
        assert.strictEqual($('.o_composer_text_field').length, 0,
            "should have no composer in the blank window");
        assert.strictEqual($('.o_thread_search_input input').length, 1,
            "the blank window should have an input");
        assert.strictEqual($('.o_thread_search_input span').text().trim(),
            "To:",
            "the blank window should propose to type a partner next to the input");

        parent.destroy();
    });

    QUnit.test('close blank thread window', function (assert) {
        assert.expect(1 + this.BEFORE_EACH_ASSERTIONS_NUM);

        var parent = this.createParent({
            data: this.data,
            services: this.services,
        });

        // open blank thread window
        parent.call('mail_service', 'openBlankThreadWindow');

        $('.o_thread_window_close').click();

        assert.strictEqual($('.o_thread_window').length, 0,
            "blank thread window should be closed");

        parent.destroy();
    });

    QUnit.test('open new DM chat from blank thread window', function (assert) {
        assert.expect(6 + this.BEFORE_EACH_ASSERTIONS_NUM);
        var done = assert.async();

        var self = this;
        var selectDef = $.Deferred();
        var sourceDef = $.Deferred();

        this.patchAutocomplete({
            selectDef: selectDef,
            sourceDef: sourceDef,
        });

        var def = $.Deferred();

        this.data['res.partner'] = {
            fields: {},
            records: [],
        };

        var parent = this.createParent({
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'im_search') {
                    def.resolve();
                    return $.when([
                        { id: 1, name: 'DemoUser1' },
                        { id: 2, name: 'DemoUser2', }
                    ]);
                }
                if (args.method === 'channel_get_and_minimize') {
                    return $.when({
                        channel_type: 'chat',
                        direct_partner: [{ id: args.args[0][0], name: 'DemoUser1', im_status: '' }],
                        id: 50,
                        is_minimized: true,
                        name: 'DemoUser1',
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // open blank thread window
        parent.call('mail_service', 'openBlankThreadWindow');

        $('.o_thread_search_input input').val("D").trigger('keydown');

        $.when(sourceDef, def).then(function () {
            assert.strictEqual($('.ui-menu-item a').length, 2,
                "should suggest 2 partners for DM");
            assert.strictEqual($('.ui-menu-item a').eq(0).text(), "DemoUser1",
                "first suggestion should be 'DemoUser1'");
            assert.strictEqual($('.ui-menu-item a').eq(1).text(), "DemoUser2",
                "second suggestion should be 'DemoUser2'");

            $('.ui-menu-item a').eq(0).click();
        });
        selectDef.then(function () {
            assert.strictEqual($('.o_thread_window').length, 1,
                "should be a single window");
            assert.strictEqual($('.o_thread_window_title').text().trim(), "#DemoUser1",
                "should have thread window of the DM chat with 'DemoUser1'");
            assert.strictEqual($('.o_composer_text_field').length, 1,
                "should have a composer in the DM chat window");

            self.unpatchAutocomplete();
            parent.destroy();
            done();
        });
    });

    QUnit.test('open already detached DM chat from blank thread window', function (assert) {
        // when opening an already detach DM chat from the blank thread window,
        // the blank thread window should disappear
        assert.expect(6 + this.BEFORE_EACH_ASSERTIONS_NUM);
        var done = assert.async();

        var self = this;
        var selectDef = $.Deferred();
        var sourceDef = $.Deferred();

        this.patchAutocomplete({
            selectDef: selectDef,
            sourceDef: sourceDef,
        });

        var def = $.Deferred();

        this.data['res.partner'] = {
            fields: {},
            records: [],
        };
        this.data.initMessaging.channel_slots.channel_dm = [{
            channel_type: 'chat',
            direct_partner: [{ id: 1, name: 'DemoUser1', im_status: '' }],
            id: 50,
            is_minimized: true,
            name: 'DemoUser1',
        }];

        var parent = this.createParent({
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                if (args.method === 'im_search') {
                    def.resolve();
                    return $.when([
                        { id: 1, name: 'DemoUser1' },
                    ]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('.o_thread_window').length, 1,
            "should be a single window");
        assert.strictEqual($('.o_thread_window_title').text().trim(), "#DemoUser1",
            "should have thread window of the DM chat with 'DemoUser1'");
        assert.strictEqual($('.o_composer_text_field').length, 1,
            "should have a composer in the DM chat window");

        // open blank thread window
        parent.call('mail_service', 'openBlankThreadWindow');

        assert.strictEqual($('.o_thread_window').length, 2,
            "should have two thread windows open");

        $('.o_thread_search_input input').val("D").trigger('keydown');

        $.when(sourceDef, def).then(function () {
            $('.ui-menu-item a').eq(0).click();
        });
        selectDef.then(function () {
            assert.strictEqual($('.o_thread_window').length, 1,
                "should now have a single thread window open");
            assert.strictEqual($('.o_thread_window_title').text().trim(), "#DemoUser1",
                "the remaining thread window should be the DM chat with 'DemoUser1'");

            self.unpatchAutocomplete();
            parent.destroy();
            done();
        });
    });

});
});
