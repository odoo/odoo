odoo.define('im_livechat.discuss_test', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var createDiscuss = mailTestUtils.createDiscuss;

QUnit.module('im_livechat', {}, function () {
QUnit.module('Discuss', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.data = {
            'mail.message': {
                fields: {},
            },
        };
        this.services = mailTestUtils.getMailServices();
    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

QUnit.test('pinnned livechat in the sidebar', function (assert) {
    assert.expect(6);
    var done = assert.async();

    this.data.initMessaging = {
        channel_slots: {
            channel_livechat: [{
                id: 1,
                channel_type: "livechat",
                correspondent_name: "Visitor",
            }],
        },
    };

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    }).then(function (discuss) {
        var $sidebar = discuss.$('.o_mail_discuss_sidebar');
        assert.strictEqual($sidebar.length, 1,
            "should have rendered a sidebar");
        assert.containsOnce($sidebar, '.o_mail_discuss_sidebar_channels',
            "should display channels in the sidebar");

        var $channels = $sidebar.find('.o_mail_discuss_sidebar_channels');
        assert.ok($channels.find('.o_mail_sidebar_title h4').text().indexOf('Livechat'),
            "should have a channel category named 'Livechat'");
        assert.containsOnce($channels, '.o_mail_discuss_item[data-thread-id=1]',
            "should have a channel sidebar item with thread ID 1");

        var $livechat = $channels.find('.o_mail_discuss_item[data-thread-id=1]');
        assert.hasAttrValue($livechat, 'title', "Visitor");
        assert.strictEqual($livechat.find('.o_thread_name').text().trim(), "Visitor");

        discuss.destroy();
        done();
    });
});

});
});
