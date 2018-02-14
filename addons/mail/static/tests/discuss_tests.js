odoo.define('mail.discuss_test', function (require) {
"use strict";

var ChatManager = require('mail.ChatManager');
var mailTestUtils = require('mail.testUtils');

var createBusService = mailTestUtils.createBusService;
var createDiscuss = mailTestUtils.createDiscuss;

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

});
});
