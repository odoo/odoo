odoo.define('mail.discuss_typing_notification_test', function (require) {
"use strict";

var Timer = require('mail.model.Timer');
var CCThrottleFunctionObject = require('mail.model.CCThrottleFunctionObject');
var mailTestUtils = require('mail.testUtils');
var testUtils = require('web.test_utils');

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
        this.myName = "Myself";
        this.myPartnerID = 30;

        this.data = {
            initMessaging: {
                channel_slots: {
                    channel_channel: [{
                        id: 1,
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
                    channel_ids: [1],
                    id: 100,
                    model: 'mail.channel',
                    res_id: 1,
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

QUnit.test('notify is typing', async function (assert) {
    assert.expect(11);

    // this is to track the step that we are testing in the `notify_typing`
    // mocked RPC
    var step = 1;

    var discuss = await createDiscuss({
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
                    assert.strictEqual(channelID, 1,
                        "should send a typing notification on general channel");
                    assert.strictEqual(args.kwargs.is_typing, true,
                        "should send a currently typing notification");
                    step++;
                } else if (step === 2) {
                    assert.strictEqual(channelID, 1,
                        "should send a typing notification on general channel");
                    assert.strictEqual(args.kwargs.is_typing, false,
                        "should send a stopped typing notification");
                }
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });

    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($general.length, 1,
        "should have the channel item with id 1");
    assert.hasAttrValue($general, 'title', 'general',
        "should have the title 'general'");

    // click on general
    await testUtils.dom.click($general);

    var $input = discuss.$('textarea.o_composer_text_field').first();
    assert.ok($input.length, "should display a composer input");

    // STEP 1: current user is typing something
    step = 1;
    $input.focus();
    await testUtils.fields.editInput($input, '1');

    assert.verifySteps(['notify_typing']);

    // STEP 2: current user clears input
    step = 2;
    await testUtils.fields.editInput($input, '');

    assert.verifySteps(['notify_typing']);

    discuss.destroy();
});

QUnit.test('receive is typing notification', async function (assert) {
    assert.expect(10);

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($general.length, 1,
        "should have the channel item with id 1");
    assert.hasAttrValue($general, 'title', 'general',
        "should have the title 'general'");

    // pick 1st composer (basic), not 2nd composer (extended, hidden)
    var $composer = discuss.$('.o_thread_composer').first();

    // click on general
    await testUtils.dom.click($general);
    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should no longer show someone is typing in sidebar of discuss");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(), "",
        "should no longer show someone is typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsOnce($general, '.o_mail_thread_typing_icon',
        "should have a thread typing icon next to general icon in the sidebar");
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Someone is typing...",
        "should show who is typing on hover on this thread typing icon");
    assert.containsOnce($composer, '.o_composer_thread_typing',
        "should show typing info on the composer of active thread");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Someone is typing...",
        "should show who is typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: false,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should no longer show someone is typing in sidebar of discuss");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(), "",
        "should no longer show someone is typing on the composer of active thread");

    discuss.destroy();
});

QUnit.test('receive message of someone that was typing something', async function (assert) {
    assert.expect(6);

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    // click on general channel
    var $general = discuss.$('.o_mail_discuss_sidebar .o_mail_discuss_item[data-thread-id=1]');
    await testUtils.dom.click($general);

    // pick 1st composer (basic), not 2nd composer (extended, hidden)
    var $composer = discuss.$('.o_thread_composer').first();

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsOnce($general, '.o_mail_thread_typing_icon',
        "should have a thread typing icon next to general icon in the sidebar");
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Someone is typing...",
        "should show who is typing on hover on this thread typing icon");
    assert.containsOnce($composer, '.o_composer_thread_typing',
        "should show typing info on the composer of active thread");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Someone is typing...",
        "should show who is typing on the composer of active thread");

    // Simulate receive message from the person typing something
    var messageData = {
        author_id: [42, 'Someone'],
        body: "<p>test</p>",
        channel_ids: [1],
        id: 101,
        model: 'mail.channel',
        res_id: 1,
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    await discuss.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should no longer show someone is typing in sidebar of discuss, after receiving message");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(), "",
        "should no longer show someone is typing on the composer of active thread, after receiving message");

    discuss.destroy();
});

QUnit.test('do not display myself as typing', async function (assert) {
    assert.expect(2);

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    // click on general channel
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    await testUtils.dom.click($general);
    // pick 1st composer (basic), not 2nd composer (extended, hidden)
    var $composer = discuss.$('.o_thread_composer').first();

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: self.myPartnerID,
        widget: discuss,
    });

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should not show current user is typing in sidebar of discuss");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(), "",
        "should not show current user is typing on the composer of active thread");

    discuss.destroy();
});

QUnit.test('several users typing something at the same time', async function (assert) {
    // The order to display several typing partners name is not random:
    // it shows at most 2 typing partners, which are the typing partners that
    // have been typing something for the longest time.
    // @see mail.model.ThreadTypingMixin:getTypingMembersToText for the rule
    // applied for displaying the typing notification text.
    assert.expect(10);

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                    { id: 43, name: "Anonymous" },
                    { id: 44, name: "Shy Guy" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    // click on general channel
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');

    // click on general
    await testUtils.dom.click($general);

    // pick 1st composer (basic), not 2nd composer (extended, hidden)
    var $composer = discuss.$('.o_thread_composer').first();

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsOnce($general, '.o_mail_thread_typing_icon',
        "should have a thread typing icon next to general icon in the sidebar");
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Someone is typing...",
        "should show someone is typing on hover on this thread typing icon");
    assert.containsOnce($composer, '.o_composer_thread_typing',
        "should show typing info on the composer of active thread");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Someone is typing...",
        "should show someone is typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 43,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Someone and Anonymous are typing...",
        "should show someone and anonymous are simultaneously typing on hover on this thread typing icon");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Someone and Anonymous are typing...",
        "should show someone and anonymous are simultaneously typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 44,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Someone, Anonymous and more are typing...",
        "should show 2 and more users are simultaneously typing on hover on this thread typing icon");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Someone, Anonymous and more are typing...",
        "should show 2 and more users are simultaneously typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: false,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "Anonymous and Shy Guy are typing...",
        "should no longer show than someone is typing on hover on this thread typing icon");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "Anonymous and Shy Guy are typing...",
        "should no longer show than someone is typing on the composer of active thread");

    discuss.destroy();
});


QUnit.test('long typing partner A and in-between short typing partner B', async function (assert) {
    // Let's suppose that A is typing a very long message. If B types a short
    // and sends it, it should display that B is typing, remove B from display
    // when receiving the message, but still keep A in the typing notification.
    assert.expect(8);

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "A" },
                    { id: 43, name: "B" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    // click on general channel
    var $general = discuss.$('.o_mail_discuss_sidebar .o_mail_discuss_item[data-thread-id=1]');
    await testUtils.dom.click($general);
    // pick 1st composer (basic), not 2nd composer (extended, hidden)
    var $composer = discuss.$('.o_thread_composer').first();

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.containsOnce($general, '.o_mail_thread_typing_icon',
        "should have a thread typing icon next to general icon in the sidebar");
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "A is typing...",
        "should show A is typing on hover on this thread typing icon");
    assert.containsOnce($composer, '.o_composer_thread_typing',
        "should show typing info on the composer of active thread");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "A is typing...",
        "should show A is typing on the composer of active thread");

    self.simulateIsTyping({
        channelID: 1,
        isTyping: true,
        partnerID: 43,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    // B comes after A in the display, because A is oldest typing partner.
    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "A and B are typing...",
        "should show A and B are typing on hover on this thread typing icon");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "A and B are typing...",
        "should show A and B are typing on the composer of active thread");

    // Simulate receive message from B
    var messageData = {
        author_id: [43, 'Someone'],
        body: "<p>test</p>",
        channel_ids: [1],
        id: 101,
        model: 'mail.channel',
        res_id: 1,
    };
    var notification = [[false, 'mail.channel', 1], messageData];
    await discuss.call('bus_service', 'trigger', 'notification', [notification]);
    await testUtils.nextTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.hasAttrValue($general.find('.o_mail_thread_typing_icon'), 'title',
        "A is typing...",
        "should show A is still typing on hover on this thread typing icon");
    assert.strictEqual($composer.find('.o_composer_thread_typing').text().trim(),
        "A is typing...",
        "should show A is still typing on the composer of active thread");

    discuss.destroy();
});

QUnit.test('receive is typing notification from unselected thread', async function (assert) {
    assert.expect(7);

    this.data.initMessaging.channel_slots.channel_channel.push({
        id: 2,
        channel_type: "channel",
        name: "other",
    });

    var self = this;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            // when receiving an 'is typing' notification, fetch the list of
            // members of this channel if we haven't done yet.
            if (args.method === 'channel_fetch_listeners') {
                return Promise.resolve([
                    { id: self.myPartnerID, name: self.myName },
                    { id: 42, name: "Someone" },
                ]);
            }
            return this._super.apply(this, arguments);
        },
        session: { partner_id: this.myPartnerID },
    });
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    var $other = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=2]');
    assert.strictEqual($general.length, 1,
        "should have the channel item with id 1");
    assert.hasAttrValue($general, 'title', 'general',
        "should have the title 'general'");
    assert.strictEqual($other.length, 1,
        "should have the channel item with id 2");
    assert.hasAttrValue($other, 'title', 'other',
        "should have the title 'other'");

    // click on general
    await testUtils.dom.click($general);

    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should no longer show someone is typing in sidebar of discuss");

    self.simulateIsTyping({
        channelID: 2,
        isTyping: true,
        partnerID: 42,
        widget: discuss,
    });
    await testUtils.nextMicrotaskTick();

    $general = discuss.$('.o_mail_discuss_sidebar')
                .find('.o_mail_discuss_item[data-thread-id=1]');
    $other = discuss.$('.o_mail_discuss_sidebar')
                .find('.o_mail_discuss_item[data-thread-id=2]');
    assert.containsNone($general, '.o_mail_thread_typing_icon',
        "should not have a thread typing icon next to general icon in the sidebar");
    assert.containsOnce($other, '.o_mail_thread_typing_icon',
        "should have a thread typing icon next to other icon in the sidebar");

    discuss.destroy();
});

});
});
