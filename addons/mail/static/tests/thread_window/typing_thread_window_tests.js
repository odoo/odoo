odoo.define('mail.typingThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Typing', {
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

        /**
         * Simulate that someone typing something (or stops typing)
         *
         * @param {Object} params
         * @param {integer} params.channelID
         * @param {boolean} params.isTyping
         * @param {integer} params.partnerID
         * @param {Widget} params.widget a widget that can call the bus_service
         */
        this.simulateIsTyping = async function (params) {
            var typingData = {
                info: 'typing_status',
                partner_id: params.partnerID,
                is_typing: params.isTyping,
            };
            var notification = [[false, 'mail.channel', params.channelID], typingData];
            params.widget.call('bus_service', 'trigger', 'notification', [notification]);
            await testUtils.nextMicrotaskTick();
        };

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

QUnit.test('receive typing notification', async function (assert) {
    assert.expect(4);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
    });
    await testUtils.nextTick();

    // detach channel 1, so that it opens corresponding thread window.
    parent.call('mail_service', 'getChannel', 1).detach();
    await testUtils.nextTick();

    var $threadWindow = $('.o_thread_window');
    assert.containsNone($threadWindow, '.o_mail_thread_typing_icon',
        "should not display an icon that someone is typing something on this thread");

    await this.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 42,
        widget: parent,
    });

    assert.containsOnce($threadWindow, '.o_mail_thread_typing_icon',
        "should display an icon that someone is typing something on this thread");
    assert.hasAttrValue($threadWindow.find('.o_mail_thread_typing_icon'), 'title',
        "Someone is typing...",
        "should display someone is typing something on hover of this icon");

    await this.simulateIsTyping({
        channelID: 1,
        isTyping: false,
        partnerID: 42,
        widget: parent,
    });

    assert.containsNone($threadWindow, '.o_mail_thread_typing_icon',
        "should no longer display an icon that someone is typing something on this thread");

    parent.destroy();
});

});
});
});
