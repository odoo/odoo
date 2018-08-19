odoo.define('mail.discuss_typing_notification_test', function (require) {
"use strict";

var Timer = require('mail.model.Timer');
var CCThrottleFunctionObject = require('mail.model.CCThrottleFunctionObject');
var mailTestUtils = require('mail.testUtils');

var createDiscuss = mailTestUtils.createDiscuss;

/**
 * This is the test suite related to the feature 'is typing...' on the Discuss
 * App.
 *
 * Untested aspects of the 'is typing' feature:
 *
 *   - timeout on receiver's end, if someone is not typing something for some
 *     time (the user becomes unregistered in the list of typing partners).
 *   - is typing shown on thread windows
 *   - show that it works on DM chat and livechat in the backend too
 */
QUnit.module('mail', {}, function () {
QUnit.module('Discuss (Typing Notifications)', {
    beforeEach: function () {
        var self = this;

        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        // patch Timer and CCThrottleFunction so that there are no
        // timers at all in the Thread that have the Thread Typing Mixin.
        this.patch = function () {

            self.ORIGINAL_TIMER_CLEAR = Timer.prototype.clear;
            self.ORIGINAL_TIMER_RESET = Timer.prototype.reset;
            self.ORIGINAL_TIMER_START = Timer.prototype.start;
            Timer.prototype.clear = function () {};
            Timer.prototype.reset = function () {};
            Timer.prototype.start = function () { this._onTimeout(); };

            self.ORIGINAL_CCTFO_DO = CCThrottleFunctionObject.prototype.do;
            CCThrottleFunctionObject.prototype.do = function () { this._func.apply(this, arguments); };
        };
        this.unpatch = function () {
            Timer.prototype.clear = self.ORIGINAL_TIMER_CLEAR;
            Timer.prototype.reset = self.ORIGINAL_TIMER_RESET;
            Timer.prototype.start = self.ORIGINAL_TIMER_START;

            CCThrottleFunctionObject.prototype.do = self.ORIGINAL_CCTFO_DO;
        };
        this.patch();

        // Frequently used data for tests
        this.generalChannelID = 1;
        this.myName = "Myself";
        this.myPartnerID = 30;

        this.data = {
            initMessaging: {
                channel_slots: {
                    channel_channel: [{
                        id: this.generalChannelID,
                        channel_type: "channel",
                        name: "general",
                    }],
                },
            },
            'mail.message': {
                fields: {
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    author_id: {
                        string: "Author",
                        relation: 'res.partner',
                    },
                    channel_ids: {
                        string: "Channels",
                        type: 'many2many',
                        relation: 'mail.channel',
                    },
                    starred: {
                        string: "Starred",
                        type: 'boolean',
                    },
                    needaction: {
                        string: "Need Action",
                        type: 'boolean',
                    },
                    starred_partner_ids: {
                        string: "partner ids",
                        type: 'integer',
                    },
                    model: {
                        string: "Related Document model",
                        type: 'char',
                    },
                    res_id: {
                        string: "Related Document ID",
                        type: 'integer',
                    },
                    need_moderation: {
                        string: "Need moderation",
                        type: 'boolean',
                    },
                },
                // There must be at least one message in the thread in order to
                // display the "is typing..." notification text, so this is just
                // a message to pass this requirement.
                records: [{
                    author_id: [this.myPartnerID, this.myName],
                    body: "<p>first message</p>",
                    channel_ids: [this.generalChannelID],
                    id: 100,
                    model: 'mail.channel',
                    res_id: this.generalChannelID,
                }],
            },
        };
        this.services = mailTestUtils.getMailServices();

        /**
         * Simulate that someone typing something (or stops typing)
         *
         * @param {Object} params
         * @param {integer} params.channelID
         * @param {boolean} params.isTyping
         * @param {integer} params.partnerID
         * @param {Widget} params.widget a widget that can call the bus_service
         */
        this.simulateIsTyping = function (params) {
            var typingData = {
                info: 'typing_status',
                partner_id: params.partnerID,
                is_typing: params.isTyping,
            };
            var notification = [[false, 'mail.channel', params.channelID], typingData];
            params.widget.call('bus_service', 'trigger', 'notification', [notification]);
        };

    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;

        // unpatch Timer and CCThrottleFunction to re-enable timers
        // with the Thread Typing Mixin
        this.unpatch();
    }
});

QUnit.test('notify is typing', function (assert) {
    assert.expect(11);
    var done = assert.async();

    var self = this;
    // this is to track the step that we are testing in the `notify_typing`
    // mocked RPC
    var step = 1;

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'notify_typing') {
                assert.step(args.method);
                var channelID = args.args[0];
                if (step === 1) {
                    // user notify that he is typing
                    assert.strictEqual(channelID, self.generalChannelID,
                        "should send a typing notification on general channel");
                    assert.strictEqual(args.kwargs.is_typing, true,
                        "should send a currently typing notification");
                    step++;
                } else if (step === 2) {
                    assert.strictEqual(channelID, self.generalChannelID,
                        "should send a typing notification on general channel");
                    assert.strictEqual(args.kwargs.is_typing, false,
                        "should send a stopped typing notification");
                }
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {

        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        assert.strictEqual($general.length, 1,
            "should have the channel item with id 1");
        assert.strictEqual($general.attr('title'), 'general',
            "should have the title 'general'");

        // click on general
        $general.click();

        var $input = discuss.$('textarea.o_composer_text_field').first();
        assert.ok($input.length, "should display a composer input");

        // STEP 1: current user is typing something
        step = 1;
        $input.focus();
        $input.val("1");
        $input.trigger('input');
        assert.verifySteps(['notify_typing']);

        // STEP 2: current user clears input
        step = 2;
        $input.val("");
        $input.trigger('input');
        assert.verifySteps(['notify_typing', 'notify_typing']);

        discuss.destroy();
        done();
    });
});

QUnit.test('receive is typing notification', function (assert) {
    assert.expect(7);
    var done = assert.async();

    var self = this;
    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        assert.strictEqual($general.length, 1,
            "should have the channel item with id 1");
        assert.strictEqual($general.attr('title'), 'general',
            "should have the title 'general'");

        // click on general
        $general.click();
        assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').length, 1,
                "there should be a typing notification bar on the thread");
        assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden by default");

        self.simulateIsTyping({
            channelID: self.generalChannelID,
            isTyping: true,
            partnerID: 42,
            widget: discuss,
        });

        fetchListenersDef.then(function () {
            assert.notOk(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be visible when someone is typing something");
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Someone is typing...",
                "It should display that the other user is typing something");

            self.simulateIsTyping({
                channelID: self.generalChannelID,
                isTyping: false,
                partnerID: 42,
                widget: discuss,
            });
            assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden when someone stops typing something");

            discuss.destroy();
            done();
        });
    });
});

QUnit.test('receive message of someone that was typing something', function (assert) {
    assert.expect(4);
    var done = assert.async();

    var self = this;
    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {
        // click on general channel
        discuss.$('.o_mail_discuss_sidebar')
               .find('.o_mail_discuss_item[data-thread-id=1]')
               .click();

        assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden by default");

        self.simulateIsTyping({
            channelID: self.generalChannelID,
            isTyping: true,
            partnerID: 42,
            widget: discuss,
        });

        fetchListenersDef.then(function () {
            assert.notOk(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be visible when someone is typing something");
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Someone is typing...",
                "It should display that the other user is typing something");

            // Simulate receive message from the person typing something
            var messageData = {
                author_id: [42, 'Someone'],
                body: "<p>test</p>",
                channel_ids: [self.generalChannelID],
                id: 101,
                model: 'mail.channel',
                res_id: self.generalChannelID,
            };
            var notification = [[false, 'mail.channel', self.generalChannelID], messageData];
            discuss.call('bus_service', 'trigger', 'notification', [notification]);

            assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden when receiving message from someone that was typing some text");

            discuss.destroy();
            done();
        });
    });
});

QUnit.test('do not display myself as typing', function (assert) {
    assert.expect(3);
    var done = assert.async();

    var self = this;
    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([
                    { id: self.myPartnerID, name: self.myName },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        $general.click();
        assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').length, 1,
                "there should be a typing notification bar on the thread");
        assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden by default");

        self.simulateIsTyping({
            channelID: self.generalChannelID,
            isTyping: true,
            partnerID: self.myPartnerID,
            widget: discuss,
        });

        fetchListenersDef.then(function () {
            assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should still be hidden when I am typing something");

            discuss.destroy();
            done();
        });
    });
});

QUnit.test('several users typing something at the same time', function (assert) {
    // The order to display several typing partners name is not random:
    // it shows at most 2 typing partners, which are the typing partners that
    // have been typing something for the longest time.
    // @see mail.model.ThreadTypingMixin:getTypingMembersToText for the rule
    // applied for displaying the typing notification text.
    assert.expect(9);
    var done = assert.async();

    var self = this;
    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                    { id: 43, name: "Anonymous" },
                    { id: 44, name: "Shy Guy" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {

        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        assert.strictEqual($general.length, 1,
            "should have the channel item with id 1");
        assert.strictEqual($general.attr('title'), 'general',
            "should have the title 'general'");

        // click on general
        $general.click();
        assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').length, 1,
                "there should be a typing notification bar on the thread");
        assert.ok(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be hidden by default");

        self.simulateIsTyping({
            channelID: self.generalChannelID,
            isTyping: true,
            partnerID: 42,
            widget: discuss,
        });

        fetchListenersDef.then(function () {
            assert.notOk(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be visible when someone is typing something");
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Someone is typing...",
                "It should display that the other user is typing something");

            self.simulateIsTyping({
                channelID: self.generalChannelID,
                isTyping: true,
                partnerID: 43,
                widget: discuss,
            });
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Someone and Anonymous are typing...",
                "It should display the two users that are typing something");

            self.simulateIsTyping({
                channelID: self.generalChannelID,
                isTyping: true,
                partnerID: 44,
                widget: discuss,
            });
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Someone, Anonymous and more are typing...",
                "It should display that several users are typing something");

            self.simulateIsTyping({
                channelID: self.generalChannelID,
                isTyping: false,
                partnerID: 42,
                widget: discuss,
            });

            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "Anonymous and Shy Guy are typing...",
                "It should omit Someone that is typing");

            discuss.destroy();
            done();
        });

    });
});


QUnit.test('long typing partner A and in-between short typing partner B', function (assert) {
    // Let's suppose that A is typing a very long message. If B types a short
    // and sends it, it should display that B is typing, remove B from display
    // when receiving the message, but still keep A in the typing notification.
    assert.expect(4);
    var done = assert.async();

    var self = this;
    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "A" },
                    { id: 43, name: "B" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    }).then(function (discuss) {
        // click on general channel
        discuss.$('.o_mail_discuss_sidebar')
               .find('.o_mail_discuss_item[data-thread-id=1]')
               .click();

        self.simulateIsTyping({
            channelID: self.generalChannelID,
            isTyping: true,
            partnerID: 42,
            widget: discuss,
        });

        fetchListenersDef.then(function () {
            assert.notOk(discuss.$('.o_thread_typing_notification_bar').hasClass('o_hidden'),
                "the typing notification bar should be visible when someone is typing something");
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "A is typing...",
                "It should display that A is typing something");

            self.simulateIsTyping({
                channelID: self.generalChannelID,
                isTyping: true,
                partnerID: 43,
                widget: discuss,
            });

            // B comes after A in the display, because A is oldest typing partner.
            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "A and B are typing...",
                "It should display that A and B are typing something");

            // Simulate receive message from B
            var messageData = {
                author_id: [43, 'Someone'],
                body: "<p>test</p>",
                channel_ids: [self.generalChannelID],
                id: 101,
                model: 'mail.channel',
                res_id: self.generalChannelID,
            };
            var notification = [[false, 'mail.channel', self.generalChannelID], messageData];
            discuss.call('bus_service', 'trigger', 'notification', [notification]);

            assert.strictEqual(discuss.$('.o_thread_typing_notification_bar').text(),
                "A is typing...",
                "It should display that A is still typing something");

            discuss.destroy();
            done();
        });
    });
});

});
});
