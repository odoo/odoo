odoo.define('mail.discuss_test', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var Composers = require('mail.composer');
var mailTestUtils = require('mail.testUtils');

var concurrency = require('web.concurrency');
var testUtils = require('web.test_utils');

var BasicComposer = Composers.BasicComposer;
var createBusService = mailTestUtils.createBusService;
var createDiscuss = mailTestUtils.createDiscuss;
var patchWindowGetSelection = testUtils.patchWindowGetSelection;
var unpatchWindowGetSelection = testUtils.unpatchWindowGetSelection;

QUnit.module('mail', {}, function () {

QUnit.module('Discuss client action', {
    beforeEach: function () {
        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.services = [ChatManager, createBusService()];
    },
});

QUnit.test('basic rendering', function (assert) {
    assert.expect(5);
    var done = assert.async();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })
    .then(function (discuss) {
        // test basic rendering
        var $sidebar = discuss.$('.o_mail_chat_sidebar');
        assert.strictEqual($sidebar.length, 1,
            "should have rendered a sidebar");

        var $nocontent = discuss.$('.o_mail_chat_content');
        assert.strictEqual($nocontent.length, 1,
            "should have rendered the content");
        assert.strictEqual($nocontent.find('.o_mail_no_content').length, 1,
            "should display no content message");

        var $inbox = $sidebar.find('.o_mail_chat_channel_item[data-channel-id=channel_inbox]');
        assert.strictEqual($inbox.length, 1,
            "should have the channel item 'channel_inbox' in the sidebar");

        var $starred = $sidebar.find('.o_mail_chat_channel_item[data-channel-id=channel_starred]');
        assert.strictEqual($starred.length, 1,
            "should have the channel item 'channel_starred' in the sidebar");
        discuss.destroy();
        done();
    });
});

QUnit.test('@ mention in channel', function (assert) {
    assert.expect(9);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    // Remove the mention throttle to speed up the test
    var mentionThrottle = BasicComposer.prototype.MENTION_THROTTLE;
    BasicComposer.prototype.MENTION_THROTTLE = 1;

    var fetchListenersDef = $.Deferred();

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return $.when([ { id: 2, name: 'TestUser'} ]);
            }
            return this._super.apply(this, arguments);
        },
    })
    .then(function (discuss) {
        var $general = discuss.$('.o_mail_chat_sidebar')
                        .find('.o_mail_chat_channel_item[data-channel-id=1]');
        assert.strictEqual($general.length, 1,
            "should have the channel item with id 1");
        assert.strictEqual($general.attr('title'), 'general',
            "should have the title 'general'");

        // click on general
        $general.click();
        var $input = discuss.$('.o_composer_input').first();
        assert.ok($input.length, "should display a composer input");

        // Simulate '@' typed by user with mocked Window.getSelection
        // Note: focus is needed in order to trigger rpc 'channel_fetch_listeners'
        $input.focus();
        $input.text("@");
        patchWindowGetSelection();
        $input.trigger('keyup');

        fetchListenersDef
            .then(concurrency.delay.bind(concurrency, 0))
            .then(function () {
                assert.strictEqual(discuss.$('.dropup.o_composer_mention_dropdown.open').length, 1,
                "dropup menu for partner mentions should be open");

                var $mentionProposition = discuss.$('.o_mention_proposition');
                assert.strictEqual($mentionProposition.length, 1,
                    "should display one partner mention proposition");
                assert.strictEqual($mentionProposition.data('id'), 2,
                    "partner mention should link to the correct partner id");
                assert.strictEqual($mentionProposition.find('.o_mention_name').text(), "TestUser",
                    "partner mention should display the correct partner name");

                $mentionProposition.click();
                assert.strictEqual(discuss.$('.o_mention_proposition').length, 0,
                    "should not have any partner mention proposition after clicking on it");
                assert.strictEqual($input.find('a').text() , "@TestUser",
                    "should have the correct mention link in the composer input");

                BasicComposer.prototype.MENTION_THROTTLE = mentionThrottle;
                unpatchWindowGetSelection();
                discuss.destroy();
                done();
        });
    });
});

});
});
