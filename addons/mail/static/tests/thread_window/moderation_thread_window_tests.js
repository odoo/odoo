odoo.define('mail.moderationThreadWindowTests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Moderation', {
    beforeEach: function () {
        var self = this;

        // define channel to link to chat window
        this.data = {
            'mail.message': {
                fields: {
                    author_id: {
                        string: "Author",
                        relation: 'res.partner',
                    },
                    channel_ids: {
                        string: "Channels",
                        type: 'many2many',
                        relation: 'mail.channel',
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
                    moderation_status: {
                        string: "Moderation Status",
                        type: 'integer',
                        selection: [
                            ['pending_moderation', 'Pending Moderation'],
                            ['accepted', 'Accepted'],
                            ['rejected', 'Rejected']
                        ],
                    },
                },
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
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = this.ORIGINAL_THREAD_WINDOW_APPENDTO;
    },
});

QUnit.test('moderator: moderated channel with pending moderation message', async function (assert) {
    assert.expect(5);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                moderation: true,
            }],
        },
        is_moderator: true,
        moderation_counter: 1,
        moderation_channel_ids: [1],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Someone"],
        body: "<p>test</p>",
        id: 100,
        model: 'mail.channel',
        moderation_status: 'pending_moderation',
        need_moderation: true,
        res_id: 1,
    }];

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });
    await testUtils.nextTick();
    // detach channel 1, so that it opens corresponding thread window.
    parent.call('mail_service', 'getChannel', 1).detach();
    await testUtils.nextTick();

    assert.strictEqual($('.o_thread_message ').length, 1,
        "should display a message in the thread window");
    assert.strictEqual($('.o_thread_author').text().trim(), "Someone",
        "should be a message of 'Someone'");
    assert.strictEqual($('.o_thread_icons').text().trim(), "Pending moderation",
        "should be pending moderation");
    assert.strictEqual($('.o_thread_message_moderation').length, 0,
        "should not display any contextual moderation decisions next to the message");
    assert.strictEqual($('.moderation_checkbox').length, 0,
        "should not display any moderation checkbox next to the message");

    parent.destroy();
});

});
});
});
