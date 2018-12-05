odoo.define('mail.discuss_seen_indicator_tests', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');
var testUtils = require('web.test_utils');

var createDiscuss = mailTestUtils.createDiscuss;

/**
 * This is the test suite related to the feature 'seen' on the Discuss
 * App.
 */
QUnit.module('mail', {}, function () {
QUnit.module('Discuss (Seen Indicator)', {
    beforeEach: function () {
        this.data = {
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
                },
            },
        };
        this.services = mailTestUtils.getMailServices();

        /**
         * Simulate that someone received message on channel
         *
         * @param {Object} params
         * @param {string} params.action either 'received' or 'seen'
         * @param {integer} params.channelID
         * @param {integer} params.partnerID
         * @param {integer} params.lastMessageID
         * @param {Widget} params.widget a widget that can call the bus_service
         */
        this.simulate = function (params) {
            var data = {
                info: params.action === 'seen' ? 'channel_seen' : 'channel_fetched',
                last_message_id: params.lastMessageID,
                partner_id: params.partnerID,
            };
            var notification = [[false, 'mail.channel', params.channelID], data];
            params.widget.call('bus_service', 'trigger', 'notification', [notification]);
        };
    },
});

QUnit.test('2 members: 1 myself message not received initially', function (assert) {
    assert.expect(2);
    var done = assert.async();

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        discuss.destroy();
        done();
    });
});

QUnit.test('2 members: 1 myself message received by everyone initially', function (assert) {
    assert.expect(4);
    var done = assert.async();

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 100,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);
        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsOnce($seenIcon, '.fa-check', "should display a single check");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().trim(), "Received by Everyone");

        discuss.destroy();
        done();
    });
});

QUnit.test('2 members: 1 myself message seen by everyone initially', function (assert) {
    assert.expect(4);
    var done = assert.async();

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);
        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().trim(), "Seen by Everyone");

        discuss.destroy();
        done();
    });
});

QUnit.test('2 members: 1 myself message received by everyone (initially not received)', function (assert) {
    assert.expect(6);
    var done = assert.async();

    var self = this;
    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });

        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsOnce($seenIcon, '.fa-check', "should display a single check");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().trim(), "Received by Everyone");

        discuss.destroy();
        done();
    });
});

QUnit.test('2 members: 1 myself message seen by everyone (initially not received)', function (assert) {
    assert.expect(6);
    var done = assert.async();

    var self = this;
    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });

        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().trim(), "Seen by Everyone");

        discuss.destroy();
        done();
    });
});

QUnit.test('2 members: 1 other message seen by me (initially not received)', function (assert) {
    assert.expect(3);
    var done = assert.async();

    var self = this;
    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: [{
            id: 2,
            name: "Someone",
            email: "someone@example.com",
        }, {
            id: 3,
            name: "Me",
            email: "me@example.com",
        }],
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 3,
            fetched_message_id: 99,
            seen_message_id: 99,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Other"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 3,
            lastMessageID: 100,
            widget: discuss,
        });

        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        discuss.destroy();
        done();
    });
});

QUnit.test('3 members: 1 myself message received by some initially', function (assert) {
    assert.expect(4);
    var done = assert.async();

    var members = [{
        id: 2,
        name: "Someone",
        email: "someone@example.com",
    }, {
        id: 3,
        name: "Me",
        email: "me@example.com",
    }, {
        id: 4,
        name: "Other",
        email: "other@example.com",
    }];

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: members,
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 100,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 4,
            fetched_message_id: 99,
            seen_message_id: 99,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                return $.when(members);
            }
            return this._super.apply(this, arguments);
        },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);
        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsOnce($seenIcon, '.fa-check', "should display a single check");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Receivedby:Someone(someone@example.com)");

        discuss.destroy();
        done();
    });
});

QUnit.test('several members: 1 myself message seen by everyone (initially not received)', function (assert) {
    // seen icon and content should change for my messages based on other users
    // actions (received and/or seen the message)
    assert.expect(26);
    var done = assert.async();

    var self = this;
    var members = [{
        id: 2,
        name: "Someone",
        email: "someone@example.com",
    }, {
        id: 3,
        name: "Me",
        email: "me@example.com",
    }, {
        id: 4,
        name: "Other",
        email: "other@example.com",
    }, {
        id: 5,
        name: "Extra",
        email: "extra@example.com",
    }];

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: members,
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 4,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 5,
            fetched_message_id: 99,
            seen_message_id: 99,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                return $.when(members);
            }
            return this._super.apply(this, arguments);
        },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });

        var $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should display seen icon on message");
        assert.containsOnce($seenIcon, '.fa-check', "should display a single check");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        var $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Receivedby:Someone(someone@example.com)");

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 4,
            lastMessageID: 100,
            widget: discuss,
        });

        $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should still display seen icon on message");
        assert.containsOnce($seenIcon, '.fa-check', "should still display a single check");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should still display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Receivedby:Someone(someone@example.com)Other(other@example.com)");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });

        $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should still display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should now display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should still display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Seenby:Someone(someone@example.com)Receivedby:Other(other@example.com)");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 4,
            lastMessageID: 100,
            widget: discuss,
        });

        $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should still display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should still display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should still display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Seenby:Someone(someone@example.com)Other(other@example.com)");

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 5,
            lastMessageID: 100,
            widget: discuss,
        });

        $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should still display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should still display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should still display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().replace(/\s/g, ""),
            "Seenby:Someone(someone@example.com)Other(other@example.com)ReceivedbyEveryone");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 5,
            lastMessageID: 100,
            widget: discuss,
        });

        $seenIcon = discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]');
        assert.isVisible($seenIcon, "should still display seen icon on message");
        assert.containsN($seenIcon, '.fa-check', 2, "should still display 2 checks");

        testUtils.dom.triggerMouseEvent($seenIcon, 'mouseover');
        $seenIconContent = $('.o_mail_thread_message_seen_icon_content');
        assert.isVisible($seenIconContent, "should still display content on seen icon mouseover");
        assert.strictEqual($seenIconContent.text().trim(),
            "Seen by Everyone");

        discuss.destroy();
        done();
    });
});

QUnit.test('several members: other message seen by everyone (initially not received)', function (assert) {
    // seen icon should never be visible for message of others
    assert.expect(9);
    var done = assert.async();

    var self = this;
    var members = [{
        id: 2,
        name: "Someone",
        email: "someone@example.com",
    }, {
        id: 3,
        name: "Me",
        email: "me@example.com",
    }, {
        id: 4,
        name: "Other",
        email: "other@example.com",
    }, {
        id: 5,
        name: "Extra",
        email: "extra@example.com",
    }];

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: members,
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 4,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 5,
            fetched_message_id: 99,
            seen_message_id: 99,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [2, "Other"],
        body: "<p>message</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                return $.when(members);
            }
            return this._super.apply(this, arguments);
        },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);

        assert.isVisible(discuss.$('.o_thread_message[data-message-id=100]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 3,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 3,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 4,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 4,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'received',
            channelID: 1,
            partnerID: 5,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 5,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'),
            "should not display seen icon on message of other users");

        discuss.destroy();
        done();
    });
});

QUnit.test('several members: only show seen icons from last message seen by everyone', function (assert) {
    assert.expect(12);
    var done = assert.async();

    var self = this;
    var members = [{
        id: 2,
        name: "Someone",
        email: "someone@example.com",
    }, {
        id: 3,
        name: "Me",
        email: "me@example.com",
    }, {
        id: 4,
        name: "Other",
        email: "other@example.com",
    }, {
        id: 5,
        name: "Extra",
        email: "extra@example.com",
    }];

    var general = {
        id: 1,
        channel_type: "channel",
        name: "general",
        members: members,
        seen_partners_info: [{
            partner_id: 2,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 3,
            fetched_message_id: 100,
            seen_message_id: 100,
        }, {
            partner_id: 4,
            fetched_message_id: 99,
            seen_message_id: 99,
        }, {
            partner_id: 5,
            fetched_message_id: 99,
            seen_message_id: 99,
        }],
    };

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [general],
        },
    };
    this.data['mail.channel'] = {
        fields: {},
        records: [general],
    };
    this.data['mail.message'].records = [{
        author_id: [3, "Me"],
        body: "<p>message 1</p>",
        channel_ids: [1],
        id: 98,
        model: 'mail.channel',
        res_id: 1,
    }, {
        author_id: [3, "Me"],
        body: "<p>message 2</p>",
        channel_ids: [1],
        id: 99,
        model: 'mail.channel',
        res_id: 1,
    }, {
        author_id: [3, "Me"],
        body: "<p>message 3</p>",
        channel_ids: [1],
        id: 100,
        model: 'mail.channel',
        res_id: 1,
    }];

    createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                return $.when(members);
            }
            return this._super.apply(this, arguments);
        },
    }).then(function (discuss) {
        // click on general
        var $general = discuss.$('.o_mail_discuss_sidebar')
                        .find('.o_mail_discuss_item[data-thread-id=1]');
        testUtils.dom.click($general);
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=98]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=99]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 2,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=98]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=99]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 4,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=98]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=99]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        self.simulate({
            action: 'seen',
            channelID: 1,
            partnerID: 5,
            lastMessageID: 100,
            widget: discuss,
        });
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=98]'));
        assert.containsNone(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=99]'));
        assert.isVisible(discuss.$('.o_mail_thread_message_seen_icon[data-message-id=100]'));

        discuss.destroy();
        done();
    });
});

});
});
