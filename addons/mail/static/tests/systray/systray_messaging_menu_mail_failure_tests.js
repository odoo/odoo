odoo.define('mail.systray.MessagingMenuMailFailureTests', function (require) {
"use strict";

var MessagingMenu = require('mail.systray.MessagingMenu');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

QUnit.module('mail', {}, function () {
QUnit.module('MessagingMenu (Mail Failures)', {
    beforeEach: function () {
        // patch _.debounce and _.throttle to be fast and synchronous
        this.underscoreDebounce = _.debounce;
        this.underscoreThrottle = _.throttle;
        _.debounce = _.identity;
        _.throttle = _.identity;

        this.data = {
            'mail.message': {
                fields: {
                    body: {
                        string: "Contents",
                        type: 'html',
                    },
                    author_id: {
                        string: "Author",
                        type: 'many2one',
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
                    needaction_partner_ids: {
                        string: "Needaction partner IDs",
                        type: 'one2many',
                        relation: 'res.partner',
                    },
                    starred_partner_ids: {
                      string: "partner ids",
                      type: 'integer',
                    }
                },
                records: [],
            },
            initMessaging: {
                mail_failures: [],
            }
        };

        this.services = mailTestUtils.getMailServices();
    },
    afterEach: function () {
        // unpatch _.debounce and _.throttle
        _.debounce = this.underscoreDebounce;
        _.throttle = this.underscoreThrottle;
    }
});

QUnit.test('preview of mail failure', async function (assert) {
    assert.expect(4);

    this.data['mail.message'].records = [{
        id: 1,
        author_id: [1, 'Me'],
        body: '<p>test</p>',
        channel_ids: [100],
    }];
    this.data.initMessaging.mail_failures = [{
        message_id: 1,
        model: 'mail.channel',
        res_id: 100,
    }];

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    await messagingMenu.appendTo($('#qunit-fixture'));
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));

    assert.containsOnce(messagingMenu, '.o_mail_preview',
        "should display one preview for the mail failure");
    assert.strictEqual(messagingMenu.$('.o_mail_preview').data('document-model'), 'mail.channel',
        "preview should link to correct document model");
    assert.strictEqual(messagingMenu.$('.o_mail_preview').data('document-id'), 100,
        "preview should link to specific document");
    assert.strictEqual(messagingMenu.$('.o_mail_preview').find('.o_preview_counter').text().trim(), "(1)",
        "should display a counter (single mail failure in this preview)");

    messagingMenu.destroy();
});

QUnit.test('preview grouped failures by document', async function (assert) {
    // If some failures linked to a document refers to a same document, a single
    // preview should group all those failures
    assert.expect(3);

    this.data['mail.message'].records = [{
        id: 1,
        author_id: [1, 'Me'],
        body: '<p>test</p>',
        channel_ids: [100],
    }, {
        id: 2,
        author_id: [1, 'Me'],
        body: '<p>test2</p>',
        channel_ids: [100],
    }, {
        id: 3,
        author_id: [1, 'Me'],
        body: '<p>test3</p>',
        res_id: 100,
        res_model: 'crm.lead',
    }];
    this.data.initMessaging.mail_failures = [{
        message_id: 1,
        model: 'mail.channel',
        res_id: 100,
    }, {
        message_id: 2,
        model: 'mail.channel',
        res_id: 100,
    }, {
        message_id: 3,
        model: 'crm.lead',
        res_id: 100,
    }];

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    await messagingMenu.appendTo($('#qunit-fixture'));
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));

    assert.containsN(messagingMenu, '.o_mail_preview', 2,
        "should have a two messaging previews for the mail failures");
    var $channelPreview = messagingMenu.$('.o_mail_preview[data-document-model="mail.channel"]');
    assert.strictEqual($channelPreview.data('document-id'), 100,
        "preview should link to specific document");
    assert.strictEqual($channelPreview.find('.o_preview_counter').text().trim(), "(2)",
        "should display counter with both mail failures");

    messagingMenu.destroy();
});

QUnit.test('preview grouped failures by document model', async function (assert) {
    // If all failures linked to a document model refers to different documents,
    // a single preview should group all failures that are linked to this
    // document model
    assert.expect(3);

    this.data['mail.message'].records = [{
        id: 1,
        author_id: [1, 'Me'],
        body: '<p>test</p>',
        channel_ids: [100],
    }, {
        id: 2,
        author_id: [1, 'Me'],
        body: '<p>test2</p>',
        channel_ids: [101],
    }, {
        id: 3,
        author_id: [1, 'Me'],
        body: '<p>test3</p>',
        res_id: 100,
        res_model: 'crm.lead',
    }];
    this.data.initMessaging.mail_failures = [{
        message_id: 1,
        model: 'mail.channel',
        res_id: 100,
    }, {
        message_id: 2,
        model: 'mail.channel',
        res_id: 101,
    }, {
        message_id: 3,
        model: 'crm.lead',
        res_id: 100,
    }];

    var messagingMenu = new MessagingMenu();
    testUtils.mock.addMockEnvironment(messagingMenu, {
        data: this.data,
        services: this.services,
    });
    await messagingMenu.appendTo($('#qunit-fixture'));
    await testUtils.dom.click(messagingMenu.$('.dropdown-toggle'));

    assert.containsN(messagingMenu, '.o_mail_preview', 2,
        "should have a two messaging previews for the mail failures");
    var $channelPreview = messagingMenu.$('.o_mail_preview[data-document-model="mail.channel"]');
    assert.notOk($channelPreview.data('document-id'),
        "channel preview should not link to any specific document");
    assert.strictEqual($channelPreview.find('.o_preview_counter').text().trim(), "(2)",
        "should display counter with both mail failures in channel preview");

    messagingMenu.destroy();
});

});
});
