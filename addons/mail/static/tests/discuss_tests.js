odoo.define('mail.discuss_test', function (require) {
"use strict";

var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');

var createDiscuss = mailTestUtils.createDiscuss;

QUnit.module('mail', {}, function () {
QUnit.module('Discuss', {
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
                        string: "Partners with Need Action",
                        type: 'many2many',
                        relation: 'res.partner',
                    },
                    starred_partner_ids: {
                        string: "Favorited By",
                        type: 'many2many',
                        relation: 'res.partner',
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
            'res.partner': {
                fields: {
                    im_status: {
                        string: "status",
                        type: 'char',
                    },
                },
                records: [{
                    id: 1,
                    im_status: 'online',
                }]
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

QUnit.test('basic rendering', async function (assert) {
    assert.expect(5);

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });

    // test basic rendering
    var $sidebar = discuss.$('.o_mail_discuss_sidebar');
    assert.strictEqual($sidebar.length, 1,
        "should have rendered a sidebar");

    assert.containsOnce(discuss, '.o_mail_discuss_content',
        "should have rendered the content");
    assert.containsOnce(discuss, '.o_mail_no_content',
        "should display no content message");

    var $inbox = $sidebar.find('.o_mail_discuss_item[data-thread-id=mailbox_inbox]');
    assert.strictEqual($inbox.length, 1,
        "should have the channel item 'mailbox_inbox' in the sidebar");

    var $starred = $sidebar.find('.o_mail_discuss_item[data-thread-id=mailbox_starred]');
    assert.strictEqual($starred.length, 1,
        "should have the channel item 'mailbox_starred' in the sidebar");
    discuss.destroy();
});

QUnit.test('searchview options visibility', async function (assert) {
    assert.expect(5);

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });

    assert.containsOnce(discuss, '.o_control_panel .o_search_options',
        "should have search options");
    assert.hasClass(discuss.$('.o_control_panel .o_searchview_more.fa'), 'fa-search-minus',
        "should have a button to toggle search options");

    assert.isVisible(discuss.$('.o_control_panel .o_search_options'),
        "search options should be visible by default");
    await testUtils.dom.click(discuss.$('.o_control_panel .o_searchview_more.fa'));
    assert.hasClass(discuss.$('.o_control_panel .o_searchview_more.fa'), 'fa-search-plus',
        "should have a button to toggle search options");
    assert.isNotVisible(discuss.$('.o_control_panel .o_search_options'),
        "search options should be hidden after clicking on search option toggler");

    discuss.destroy();
});

QUnit.test('searchview filter messages', async function (assert) {
    assert.expect(10);

    this.data['mail.message'].records = [{
        author_id: [5, 'Demo User'],
        body: '<p>abc</p>',
        id: 1,
        needaction: true,
        needaction_partner_ids: [3],
    }, {
        author_id: [6, 'Test User'],
        body: '<p>def</p>',
        id: 2,
        needaction: true,
        needaction_partner_ids: [3],
    }];

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: {
            partner_id: 3
        },
        archs: {
            'mail.message,false,search':
                '<search>' +
                    '<field name="body"/>' +
                '</search>',
        },
    });
        assert.containsN(discuss, '.o_thread_message', 2,
            "there should be two messages in the inbox mailbox");
        assert.strictEqual($('.o_searchview_input').length, 1,
            "there should be a searchview on discuss");
        assert.strictEqual($('.o_searchview_input').val(), '',
            "the searchview should be empty initially");

        // interact with searchview so that there is only once message
        $('.o_searchview_input').val("ab").trigger('keyup');
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();
        assert.strictEqual($('.o_searchview_facet').length, 1,
            "the searchview should have a facet");
        assert.strictEqual($('.o_facet_values').text().trim(), 'ab',
            "the facet should be a search on 'ab'");
        assert.containsOnce(discuss, '.o_thread_message',
            "there should be a single message after filter");

        // interact with search view so that there are no matching messages
        await testUtils.dom.click($('.o_facet_remove'));
        $('.o_searchview_input').val("abcd").trigger('keyup');
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();

        assert.strictEqual($('.o_searchview_facet').length, 1,
            "the searchview should have a facet");
        assert.strictEqual($('.o_facet_values').text().trim(), 'abcd',
            "the facet should be a search on 'abcd'");
        assert.containsNone(discuss, '.o_thread_message',
            "there should be no message after 2nd filter");
        assert.strictEqual(discuss.$('.o_thread_title').text().trim(),
            "No matches found",
            "should display that there are no matching messages");

        discuss.destroy();

});

QUnit.test('unescape channel name in the sidebar', async function (assert) {
    // When the user creates a channel, the channel's name is escaped, this in
    // order to prevent XSS attacks. However, the user should see visually the
    // unescaped name of the channel. For instance, when the user creates a
    // channel named  "R&D", he should see "R&D" and not "R&amp;D".
    assert.expect(2);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "R&amp;D",
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });

    var $sidebar = discuss.$('.o_mail_discuss_sidebar');

    var $channel = $sidebar.find('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($channel.length, 1,
        "should have the channel item for channel 1 in the sidebar");
    assert.strictEqual($channel.find('.o_thread_name').text().replace(/\s/g, ''),
        "#R&D",
        "should have unescaped channel name in the sidebar");

    discuss.destroy();
});

QUnit.test('@ mention in channel', async function (assert) {
    assert.expect(34);

    var fetchListenersDef = testUtils.makeTestPromise();
    var receiveMessageDef = testUtils.makeTestPromise();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };
    var objectDiscuss;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return Promise.resolve([
                    {id: 1, name: 'Admin'},
                    {id: 2, name: 'TestUser'},
                    {id: 3, name: 'DemoUser'}
                ]);
            }
            if (args.method === 'message_post') {
                var data = {
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    channel_ids: [1],
                };
                var notification = [[false, 'mail.channel', 1], data];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                receiveMessageDef.resolve();
                return Promise.resolve(42);
            }
            return this._super.apply(this, arguments);
        },
    });
    objectDiscuss = discuss;
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

    // Note: focus is needed in order to trigger rpc 'channel_fetch_listeners'
    $input.focus();
    $input.val("@");
    $input.trigger('keyup');

    fetchListenersDef;
    await testUtils.nextTick();
    assert.containsOnce(discuss, '.dropup.o_composer_mention_dropdown.show',
    "dropup menu for partner mentions should be open");

    var $mentionPropositions = discuss.$('.o_mention_proposition');
    assert.strictEqual($mentionPropositions.length, 3,
        "should display 3 partner mention propositions");

    var $mention1 = $mentionPropositions.first();
    var $mention2 = $mentionPropositions.first().next();
    var $mention3 = $mentionPropositions.first().next().next();

    // correct 1st mention proposition
    assert.hasClass($mention1,'active',
        "first partner mention should be active");
    assert.strictEqual($mention1.data('id'), 1,
        "first partner mention should link to the correct partner id");
    assert.strictEqual($mention1.find('.o_mention_name').text(), "Admin",
        "first partner mention should display the correct partner name");
    // correct 2nd mention proposition
    assert.doesNotHaveClass($mention2, 'active',
        "second partner mention should not be active");
    assert.strictEqual($mention2.data('id'), 2,
        "second partner mention should link to the correct partner id");
    assert.strictEqual($mention2.find('.o_mention_name').text(), "TestUser",
        "second partner mention should display the correct partner name");
    // correct 3rd mention proposition
    assert.doesNotHaveClass($mention3, 'active',
        "third partner mention should not be active");
    assert.strictEqual($mention3.data('id'), 3,
        "third partner mention should link to the correct partner id");
    assert.strictEqual($mention3.find('.o_mention_name').text(), "DemoUser",
        "third partner mention should display the correct partner name");

    // check DOWN event
    await testUtils.fields.triggerKey('up', $input, 'down');
    assert.doesNotHaveClass($mention1, 'active',
        "first partner mention should not be active");
    assert.hasClass($mention2,'active',
        "second partner mention should be active");
    assert.doesNotHaveClass($mention3, 'active',
        "third partner mention should not be active");

    // check UP event
    await testUtils.fields.triggerKey('up', $input, 'up');
    assert.hasClass($mention1,'active',
        "first partner mention should be active");
    assert.doesNotHaveClass($mention2, 'active',
        "second partner mention should not be active");
    assert.doesNotHaveClass($mention3, 'active',
        "third partner mention should not be active");

    // check TAB event (full cycle, hence 3 TABs)
    await testUtils.fields.triggerKey('up', $input, 'tab');
    assert.doesNotHaveClass($mention1, 'active',
        "first partner mention should not be active");
    assert.hasClass($mention2,'active',
        "second partner mention should be active");
    assert.doesNotHaveClass($mention3, 'active',
        "third partner mention should not be active");

    await testUtils.fields.triggerKey('up', $input, 'tab');
    assert.doesNotHaveClass($mention1, 'active',
        "first partner mention should not be active");
    assert.doesNotHaveClass($mention2, 'active',
        "second partner mention should not be active");
    assert.hasClass($mention3,'active',
        "third partner mention should be active");

    await testUtils.fields.triggerKey('up', $input, 'tab');
    assert.hasClass($mention1,'active',
        "first partner mention should be active");
    assert.doesNotHaveClass($mention2, 'active',
        "second partner mention should not be active");
    assert.doesNotHaveClass($mention3, 'active',
        "third partner mention should not be active");

    await testUtils.fields.triggerKey('up', $input, 'enter');
    assert.containsNone(discuss, '.o_mention_proposition',
        "should not have any partner mention proposition after ENTER");
    assert.strictEqual($input.val().trim() , "@Admin",
        "should have the correct mention link in the composer input");

    // send message
    await testUtils.fields.triggerKeydown($input, 'enter');

    await receiveMessageDef;
    await testUtils.nextTick();

    assert.containsOnce(discuss, '.o_thread_message_content',
        "should display one message with some content");
    assert.containsOnce(discuss, '.o_thread_message_content a',
        "should contain a link in the message content");
    assert.strictEqual(discuss.$('.o_thread_message_content a').text(),
        "@Admin", "should have correct mention link in the message content");

    discuss.destroy();
});

QUnit.test('@ mention with special chars', async function (assert) {
    assert.expect(11);
    var fetchListenersDef = testUtils.makeTestPromise();
    var receiveMessageDef = testUtils.makeTestPromise();
    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };
    var objectDiscuss;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return Promise.resolve([
                    {id: 1, name: '\u0405pëciãlUser<&>"`\' \u30C4'},
                ]);
            }
            if (args.method === 'message_post') {
                assert.deepEqual(args.kwargs.partner_ids, [1],
                    "mentioned partners are sent to server"
                )
                var data = {
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    channel_ids: [1],
                };
                var notification = [[false, 'mail.channel', 1], data];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                receiveMessageDef.resolve();
                return Promise.resolve(42);
            }
            return this._super.apply(this, arguments);
        },
    });
    objectDiscuss = discuss;
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    // click on general
    $general.click();
    await testUtils.nextTick();
    var $input = discuss.$('textarea.o_composer_text_field').first();
    assert.ok($input.length, "should display a composer input");
    // Note: focus is needed in order to trigger rpc 'channel_fetch_listeners'
    $input.focus();
    $input.val("@");
    $input.trigger('keyup');
    await fetchListenersDef;
    await testUtils.nextTick();
    var $mention = discuss.$('.o_mention_proposition');
    // correct mention proposition
    assert.ok($mention.hasClass('active'),
        "first partner mention should be active");
    assert.strictEqual($mention.data('id'), 1,
        "first partner mention should link to the correct partner id");
    assert.strictEqual($mention.find('.o_mention_name').text(), '\u0405pëciãlUser<&>"`\' \u30C4',
        "first partner mention should display the correct partner name");
    // equivalent to $mentionPropositions.find('active').click();
    await testUtils.fields.triggerKey('up', $input, 'enter');
    assert.strictEqual(discuss.$('.o_mention_proposition').length, 0,
        "should not have any partner mention proposition after ENTER");
    assert.strictEqual($input.val().trim() , "@\u0405pëciãlUser<&>\"`'\u00A0\u30C4",
        "should have the correct mention link in the composer input");
    // send message
    await testUtils.fields.triggerKeydown($input, 'enter');
    await receiveMessageDef;
    await testUtils.nextTick();
    assert.strictEqual(discuss.$('.o_thread_message_content').length, 1,
        "should display one message with some content");
    assert.strictEqual(discuss.$('.o_thread_message_content a').length, 1,
        "should contain a link in the message content");
    assert.strictEqual(discuss.$('.o_thread_message_content a').text(),
        "@\u0405pëciãlUser<&>\"`' \u30C4",
        "should have correct mention link in the message content");
    $input.val("@");
    $input.trigger('keyup');
    await testUtils.nextTick();
    var $mention = discuss.$('.o_mention_proposition');
    assert.strictEqual($mention.find('.o_mention_name').text(),
        '\u0405pëciãlUser<&>"`\' \u30C4',
        "first partner mention should still display the correct partner name");
    discuss.destroy();
});

QUnit.test('@ mention with removed space', async function (assert) {
    assert.expect(4);
    var fetchListenersDef = testUtils.makeTestPromise();
    var receiveMessageDef = testUtils.makeTestPromise();
    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };
    var objectDiscuss;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return Promise.resolve([
                    {id: 1, name: 'Admin'},
                ]);
            }
            if (args.method === 'message_post') {
                assert.deepEqual(args.kwargs.partner_ids, [],
                    "mentioned partners are sent to server"
                );
                var data = {
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    channel_ids: [1],
                };
                var notification = [[false, 'mail.channel', 1], data];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                receiveMessageDef.resolve();
                return Promise.resolve(42);
            }
            return this._super.apply(this, arguments);
        },
    });
    objectDiscuss = discuss;
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');
    // click on general
    $general.click();
    var $input = discuss.$('textarea.o_composer_text_field').first();
    assert.ok($input.length, "should display a composer input");
    // Note: focus is needed in order to trigger rpc 'channel_fetch_listeners'
    $input.focus();
    $input.val("@");
    $input.trigger('keyup');
    await fetchListenersDef;
    await testUtils.nextTick();
    // equivalent to $mentionPropositions.find('active').click();
    $input.trigger($.Event('keyup', {which: $.ui.keyCode.ENTER}));
    $input.val('@Admin: hi');
    // send message
    await testUtils.fields.triggerKeydown($input, 'enter');
    await receiveMessageDef;
    await testUtils.nextTick();
    assert.containsNone(discuss, '.o_thread_message_content a',
        "should not contain a link in the message content");
    assert.strictEqual(discuss.$('.o_thread_message_content').html().trim(),
        "@Admin: hi", "should not have linked mention without space");
    discuss.destroy();
});

QUnit.test('@ mention in mailing channel', async function (assert) {
    assert.expect(8);

    var fetchListenersDef = testUtils.makeTestPromise();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                mass_mailing: true,
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'channel_fetch_listeners') {
                fetchListenersDef.resolve();
                return Promise.resolve([
                    {id: 1, name: 'Admin'},
                ]);
            }
            return this._super.apply(this, arguments);
        },
    });
    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');

    // click on general
    $general.click();
    await testUtils.nextTick();
    // 1st composer: basic composer (hidden), 2nd composer: extended (shown)
    var $input = discuss.$('textarea.o_composer_text_field').eq(1);
    assert.ok($input.length, "should display a composer input");

    // Simulate '@' typed by user with mocked Window.getSelection
    // Note: focus is needed in order to trigger rpc 'channel_fetch_listeners'
    $input.focus();
    $input.val("@");
    $input.trigger('keyup');

    await fetchListenersDef;
    await testUtils.nextTick();

    assert.strictEqual(discuss.$('.dropup.o_composer_mention_dropdown.show').length, 1,
    "dropup menu for partner mentions should be open");

    var $mention = discuss.$('.o_mention_proposition');
    assert.strictEqual($mention.length, 1,
        "should display 1 partner mention proposition");

    // correct mention proposition
    assert.ok($mention.hasClass('active'),
        "partner mention should be active");
    assert.strictEqual($mention.data('id'), 1,
        "partner mention should link to the correct partner id");
    assert.strictEqual($mention.find('.o_mention_name').text(), "Admin",
        "partner mention should display the correct partner name");

    // equivalent to $mentionPropositions.find('active').click();
    await testUtils.fields.triggerKey('up', $input, 'enter');

    assert.ok($input.is(':focus'), "composer body should have focus");
    assert.notOk(discuss.$('.o_composer_subject').is(':focus'));

    discuss.destroy();
});

QUnit.test('no crash focusout emoji button', async function (assert) {
    assert.expect(3);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })

    var $general = discuss.$('.o_mail_discuss_sidebar')
        .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($general.length, 1,
        "should have the channel item with id 1");
    assert.hasAttrValue($general, 'title', 'general',
        "should have the title 'general'");

    // click on general
    await testUtils.dom.click($general);
    discuss.$('.o_composer_button_emoji').focus();
    try {
        discuss.$('.o_composer_button_emoji').focusout();
        assert.ok(true, "should not crash on focusout of emoji button");
    } finally {
        discuss.destroy();
    }
});

QUnit.test('older messages are loaded on scroll', async function (assert) {
    assert.expect(10);

    var fetchCount = 0;
    var loadMoreDef = testUtils.makeTestPromise();
    var messageData = [];
    for (var i = 0; i < 35; i++) {
        messageData.push({
            author_id: ['1', 'Me'],
            body: '<p>test ' + i + '</p>',
            channel_ids: [1],
            id: i,
        });
    }

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
                static: true,
            }],
        },
    };
    this.data['mail.message'].records = messageData;

    var discuss = await createDiscuss({
        context: {},
        data: this.data,
        params: {},
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'message_fetch') {
                assert.step(args.method);
                fetchCount++;
                // 1st fetch: inbox initial fetch
                // 2nd fetch: general initial fetch
                // 3rd fetch: general load more
                if (fetchCount === 1) {
                    assert.strictEqual(args.kwargs.limit, 30,
                        "should ask to fetch 30 messages at most");
                }
                if (fetchCount === 3) {
                    loadMoreDef.resolve();
                }
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.verifySteps(['message_fetch'],
        "should fetch messages once for needaction messages (Inbox)");

    var $general = discuss.$('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($general.length, 1,
        "should have a channel item with id 1");

    // switch to 'general'
    await testUtils.dom.click($general);

    assert.verifySteps(['message_fetch'],
        "should fetch a second time for general channel messages (30 last messages)");

    assert.containsN(discuss, '.o_thread_message', 30,
        "should display the 30 messages");

    // simulate a scroll to top to load more messages
    discuss.$('.o_mail_thread').scrollTop(0);

    await loadMoreDef;
    await testUtils.nextTick();
    assert.verifySteps(['message_fetch'],
        "should fetch a third time for general channel messages (5 remaining messages)");
    assert.containsN(discuss, '.o_thread_message', 35,
        "all messages should now be loaded");

    discuss.destroy();
});

QUnit.test('"Unstar all" button should reset the starred counter', async function (assert) {
    assert.expect(2);

    var messageData = [];
    _.each(_.range(1, 41), function (num) {
        messageData.push({
                id: num,
                body: "<p>test" + num + "</p>",
                author_id: ["1", "Me"],
                channel_ids: [1],
                starred: true,
                starred_partner_ids: [1],
            }
        );
    });

    this.data.initMessaging = {
            channel_slots: {
                channel_channel: [{
                    id: 1,
                    channel_type: "channel",
                    name: "general",
                }],
            },
            starred_counter: messageData.length,
    };
    this.data['mail.message'].records = messageData;

    var objectDiscuss;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'unstar_all') {
                var data = {
                    message_ids: _.range(1, 41),
                    starred: false,
                    type: 'toggle_star',
                };
                var notification = [[false, 'res.partner'], data];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                return Promise.resolve(42);
            }
            return this._super.apply(this, arguments);
        },
        session: {partner_id: 1},
    })

    objectDiscuss = discuss;

    var $starred = discuss.$('.o_mail_discuss_sidebar').find('.o_mail_mailbox_title_starred');
    var $starredCounter = $('.o_mail_mailbox_title_starred > .o_mail_sidebar_needaction');

    // Go to Starred channel
    await testUtils.dom.click($starred);
    // Test Initial Value
    assert.strictEqual($starredCounter.text().trim(), "40", "40 messages should be starred");

    // Unstar all and wait 'update_starred'
    await testUtils.dom.click($('.o_control_panel .o_mail_discuss_button_unstar_all'));
    $starredCounter = $('.o_mail_mailbox_title_starred > .o_mail_sidebar_needaction');
    assert.strictEqual($starredCounter.text().trim(), "0",
        "All messages should be unstarred");

    discuss.destroy();
});

QUnit.test('confirm dialog when administrator leave (not chat) channel', async function (assert) {
    assert.expect(2);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "MyChannel",
                create_uid: 3,
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: {
            uid: 3,
        },
    });

    // Unsubscribe on MyChannel as administrator
    // The unpin icon is only shown when hovering on sidebar item.
    // helpter dom.click needs the element to be visible, hence the
    // hack on display of this icon.
    discuss.$('.o_mail_partner_unpin').css('display', 'block');
    await testUtils.dom.click(discuss.$('.o_mail_partner_unpin'));

    assert.strictEqual($('.modal-dialog').length, 1,
        "should display a dialog");
    assert.strictEqual($('.modal-body').text(),
        "You are the administrator of this channel. Are you sure you want to unsubscribe?",
        "Warn user that he will be unsubscribed from channel as admin.");
    discuss.destroy();
});

QUnit.test('convert emoji sources to unicodes on message_post', async function (assert) {
    assert.expect(2);

    var receiveMessageDef = testUtils.makeTestPromise();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    var objectDiscuss;
    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                assert.strictEqual(args.kwargs.body, "😊 😂",
                    "message_post data should have all emojis in their unicode representation");

                var data = {
                    author_id: ["42", "Me"],
                    body: args.kwargs.body,
                    channel_ids: [1],
                };
                var notification = [[false, 'mail.channel', 1], data];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                receiveMessageDef.resolve();
                return Promise.resolve(42);
            }
            return this._super.apply(this, arguments);
        },
    })

    objectDiscuss= discuss;

    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');

    // click on general
    await testUtils.dom.click($general);
    var $input = discuss.$('textarea.o_composer_text_field').first();

    $input.focus();
    $input.val(":) x'D");
    await testUtils.fields.triggerKeydown($input, 'enter');

    await receiveMessageDef.then(function () {
        assert.strictEqual(discuss.$('.o_thread_message_content').text().replace(/\s/g, ""),
            "😊😂",
            "New posted message should contain all emojis in their unicode representation");
        discuss.destroy();
    });
});

QUnit.test('mark all messages as read from Inbox', async function (assert) {
    assert.expect(9);

    this.data['mail.message'].records = [{
        author_id: [5, 'Demo User'],
        body: '<p>test 1</p>',
        id: 1,
        needaction: true,
        needaction_partner_ids: [3],
    }, {
        author_id: [6, 'Test User'],
        body: '<p>test 2</p>',
        id: 2,
        needaction: true,
        needaction_partner_ids: [3],
    }];

    this.data.initMessaging = {
        needaction_inbox_counter: 2,
    };

    var markAllReadDef = testUtils.makeTestPromise();
    var objectDiscuss;

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'mark_all_as_read') {
                _.each(this.data['mail.message'].records, function (message) {
                    message.needaction = false;
                });
                var notificationData = {
                    type: 'mark_as_read',
                    message_ids: [1, 2],
                };
                var notification = [[false, 'res.partner', 3], notificationData];
                objectDiscuss.call('bus_service', 'trigger', 'notification', [notification]);
                markAllReadDef.resolve();
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        },
    })

    objectDiscuss = discuss;

    var $inbox = discuss.$('.o_mail_discuss_item[data-thread-id="mailbox_inbox"]');
    assert.strictEqual($inbox.length, 1,
        "there should be an 'Inbox' item in Discuss sidebar");
    assert.strictEqual($inbox.find('.o_mail_sidebar_needaction').text().trim(), "2",
        "the mailbox counter of 'Inbox' should be 2");
    assert.hasClass($inbox,'o_active',
        "'Inbox' should be the currently active thread");
    assert.containsN(discuss, '.o_thread_message', 2,
        "there should be 2 messages in inbox");

    var $markAllReadButton = $('.o_mail_discuss_button_mark_all_read');
    assert.strictEqual($markAllReadButton.length, 1,
        "there should be a 'Mark All As Read' button");
    assert.hasAttrValue($markAllReadButton, 'style',
        'display: inline-block;',
        "the 'Mark All As Read' button should be visible");
    assert.notOk($markAllReadButton.prop('disabled'),
        "the 'Mark All As Read' button should not be disabled");

    await testUtils.dom.click($markAllReadButton);

    markAllReadDef.then(function () {
        // immediately jump to end of the fadeout animation on messages
        $inbox = discuss.$('.o_mail_discuss_item[data-thread-id="mailbox_inbox"]');
        discuss.$('.o_thread_message').stop(false, true);
        assert.strictEqual($inbox.find('.o_mail_sidebar_needaction').text().trim(), "0",
            "the mailbox counter of 'Inbox' should have reset to 0");
        assert.containsNone(discuss, '.o_thread_message',
            "there should no message in inbox anymore");

        discuss.destroy();
    });
});

QUnit.test('drag and drop file in composer [REQUIRE NON-INCOGNITO WINDOW]', async function (assert) {
    assert.expect(8);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })

    var $general = discuss.$('.o_mail_discuss_sidebar')
                    .find('.o_mail_discuss_item[data-thread-id=1]');

    // click on general
    await testUtils.dom.click($general);

    // first composer is active (basic), 2nd is hidden (extended)
    var $composer = discuss.$('.o_thread_composer').first();
    assert.containsNone($composer, '.o_attachments_list',
        "should not display any attachment on the composer initially");
    assert.containsOnce($composer, '.o_file_drop_zone_container',
        "should have a dropzone to drag-and-drop files");

    var $dropZoneContainer = $composer.find('.o_file_drop_zone_container');
    assert.isNotVisible($dropZoneContainer,
        "dropzone should not be visible");

    var file = await testUtils.file.createFile({
        name: 'text.txt',
        content: 'hello, world',
        contentType: 'text/plain',
    });

    await testUtils.file.dragoverFile($dropZoneContainer, file);
    assert.isVisible($dropZoneContainer,
        "dropzone should be visible");

    await testUtils.file.dropFile($dropZoneContainer, file);
    assert.containsOnce($composer, '.o_attachments_list',
        "should display some attachments on the composer");
    assert.containsOnce($composer, '.o_attachment',
        "should display one attachment on the composer");

    var filename = $('.o_attachment').find('.caption').first().text().trim();
    assert.strictEqual(filename, 'text.txt',
        "should display the correct filename");
    assert.hasClass($('.o_attachment_uploaded i'), 'fa-check',
        "text file should have been uploaded");

    discuss.destroy();
});

QUnit.test('reply to message from inbox', async function (assert) {
    assert.expect(11);

    var self = this;
    this.data['mail.message'].records = [{
        author_id: [5, 'Demo User'],
        body: '<p>test 1</p>',
        id: 1,
        needaction: true,
        needaction_partner_ids: [3],
        res_id: 100,
        model: 'some.document',
        record_name: 'SomeDocument',
    }];
    this.data.initMessaging = {
        needaction_inbox_counter: 1,
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                assert.step(args.method);
                assert.strictEqual(args.model, 'some.document',
                    "should post message to correct document model");
                assert.strictEqual(args.args[0], 100,
                    "should post message to correct document ID");

                self.data['mail.message'].records.push({
                    author_id: [3, 'Me'],
                    body: args.kwargs.body,
                    id: 2,
                    res_id: 100,
                    model: 'some.document',
                    record_name: 'SomeDocument',
                });
                return Promise.resolve(2);
            }
            return this._super.apply(this, arguments);
        },
    })
    assert.strictEqual(discuss.$('.o_mail_discuss_item.o_active').data('thread-id'),
        'mailbox_inbox',
        "Inbox should be selected by default");
    assert.containsOnce(discuss, '.o_thread_message',
        "should display a single message in inbox");
    assert.strictEqual(discuss.$('.o_thread_message').data('message-id'), 1,
        "message should be linked to correct message");
    assert.containsOnce(discuss.$('.o_thread_message'), '.o_thread_message_reply',
        "should display the reply icon for message linked to a document");

    await testUtils.dom.click(discuss.$('.o_thread_message_reply'));
    var $composer = discuss.$('.o_thread_composer_extended');
    assert.isVisible($composer,
        "extended composer should become visible");
    assert.strictEqual($composer.find('.o_composer_subject input').val(),
        'Re: SomeDocument',
        "composer should have copied document name as subject of message");

    var $textarea = $composer.find('.o_composer_input textarea').first();
    await testUtils.fields.editInput($textarea, 'someContent');
    assert.containsOnce($composer, '.o_composer_button_send',
        "should have button to send reply message");
    await testUtils.dom.click($composer.find('.o_composer_button_send'));

    assert.verifySteps(['message_post']);

    discuss.destroy();
});

QUnit.test('discard replying to message from inbox', async function (assert) {
    assert.expect(4);

    var self = this;
    this.data['mail.message'].records = [{
        author_id: [5, 'Demo User'],
        body: '<p>test 1</p>',
        id: 1,
        needaction: true,
        needaction_partner_ids: [3],
        res_id: 100,
        model: 'some.document',
        record_name: 'SomeDocument',
    }];
    this.data.initMessaging = {
        needaction_inbox_counter: 1,
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                assert.step(args.method);
                assert.strictEqual(args.model, 'some.document',
                    "should post message to correct document model");
                assert.strictEqual(args.args[0], 100,
                    "should post message to correct document ID");

                self.data['mail.message'].records.push({
                    author_id: [3, 'Me'],
                    body: args.kwargs.body,
                    id: 2,
                    res_id: 100,
                    model: 'some.document',
                    record_name: 'SomeDocument',
                });
                return Promise.resolve(2);
            }
            return this._super.apply(this, arguments);
        },
    })

    await testUtils.dom.click(discuss.$('.o_thread_message_reply'));
    assert.containsOnce(discuss, '.o_thread_selected_message',
        "should have a message selected");

    var $composer = discuss.$('.o_thread_composer_extended');
    assert.containsOnce($composer, '.o_composer_button_discard',
        "should have button to discard replying to message");

    await testUtils.dom.click($composer.find('.o_composer_button_discard'));
    assert.isNotVisible($composer,
        "extended composer should become hidden on discard");
    assert.containsNone(discuss, '.o_thread_selected_message',
        "should not longer have a message selected");

    discuss.destroy();
});

QUnit.test('no quick search channels in the sidebar with less than 20 channels', async function (assert) {
    assert.expect(3);

    var channelsData = [];
    _.each(_.range(0, 19), function (num) {
        channelsData.push({
            id: num,
            channel_type: "channel",
            name: "Channel" + num,
        });
    });

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: channelsData,
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })

    var $sidebar = discuss.$('.o_mail_discuss_sidebar');

    var $channelsSidebar = $sidebar.find('.o_mail_discuss_sidebar_channels');
    assert.strictEqual($channelsSidebar.length, 1,
        "should show channels and dms in sidebar");
    assert.strictEqual($channelsSidebar.find('.o_mail_discuss_item').length, 19,
        "should show 19 channels in sidebar");
    assert.strictEqual(discuss.$('.o_discuss_sidebar_quick_search').length, 0,
        "should not display a quick search");

    discuss.destroy();
});

QUnit.test('quick search channels in the sidebar with more than 20 channels', async function (assert) {
    assert.expect(7);

    var channelsData = [];
    var channelANum = 15;
    _.each(_.range(0, channelANum), function (num) {
        var channel = {
            id: num,
            channel_type: "channel",
            name: "ChannelA" + num,
        };
        channelsData.push(channel);
    });
    var channelBNum = 5;
    _.each(_.range(0, channelBNum), function (num) {
        var channel = {
            id: channelANum + num,
            channel_type: "channel",
            name: "ChannelB" + num,
        };
        channelsData.push(channel);
    });

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: channelsData,
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    })

    var $sidebar = discuss.$('.o_mail_discuss_sidebar');

    var $channelsSidebar = $sidebar.find('.o_mail_discuss_sidebar_channels');
    assert.strictEqual($channelsSidebar.length, 1,
        "should show channels in sidebar");
    assert.strictEqual($channelsSidebar.find('.o_mail_discuss_item').length, 20,
        "should show 20 channels in sidebar");
    assert.strictEqual(discuss.$('.o_discuss_sidebar_quick_search').length, 1,
        "should display a quick search");

    discuss.$('.o_discuss_sidebar_quick_search input').val('channelA').trigger('input');
    $channelsSidebar = $sidebar.find('.o_mail_discuss_sidebar_channels');
    assert.strictEqual($channelsSidebar.find('.o_mail_discuss_item').length, 15,
        "should now show 15 channels in sidebar");

    discuss.$('.o_discuss_sidebar_quick_search input').val('channelB').trigger('input');

    $channelsSidebar = $sidebar.find('.o_mail_discuss_sidebar_channels');
    assert.strictEqual($channelsSidebar.find('.o_mail_discuss_item').length, 5,
        "should now show 5 channels in sidebar");

    discuss.$('.o_discuss_sidebar_quick_search input').val('channelB4').trigger('input');

    $channelsSidebar = $sidebar.find('.o_mail_discuss_sidebar_channels');
    assert.strictEqual($channelsSidebar.find('.o_mail_discuss_item').length, 1,
        "should now show a single channel in sidebar");
    assert.strictEqual($channelsSidebar.find('.o_thread_name').text().replace(/\s/g, ''),
        '#ChannelB4',
        "should have searched the correct channel B4");

    discuss.destroy();
});

QUnit.test('select emoji replaces cursor position', async function (assert) {
    assert.expect(5);

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
    });
    var $general = discuss.$('.o_mail_discuss_sidebar')
        .find('.o_mail_discuss_item[data-thread-id=1]');
    assert.strictEqual($general.length, 1,
        "should have the channel item with id 1");
    assert.hasAttrValue($general, 'title', 'general',
        "should have the title 'general'");

    // click on general
    await testUtils.dom.click($general);

    // general uses basic composer, so this is the 1st composer
    // (2nd composer is hidden)
    var $composer = discuss.$('.o_composer_text_field').first();

    await testUtils.fields.editInput($composer, 'abcdefgh');

    assert.strictEqual($composer.val(), "abcdefgh");

    // cursor position: ab|cd|efgh (selecting c and d)
    $composer[0].setSelectionRange(2, 4);

    await testUtils.dom.click(discuss.$('.o_composer_button_emoji'));
    await testUtils.dom.triggerMouseEvent(discuss.$('.o_mail_emoji[data-emoji=":)"]'), 'mousedown');

    assert.strictEqual($composer.val(), "ab :) efgh",
        "should have inserted emoji ");

    await testUtils.dom.click(discuss.$('.o_composer_button_emoji'));
    await testUtils.dom.triggerMouseEvent(discuss.$('.o_mail_emoji[data-emoji=":)"]'), 'mousedown');

    assert.strictEqual($composer.val(), "ab :)  :) efgh",
        "should have inserted emoji after previously inserted emoji");

    discuss.destroy();
});

QUnit.test('rename DM conversation', async function (assert) {
    assert.expect(11);

    this.data.initMessaging = {
        channel_slots: {
            channel_direct_message: [{
                id: 1,
                channel_type: "chat",
                create_uid: 3,
                direct_partner: [{
                    id: 7,
                    im_status: 'online',
                    name: 'Demo User',
                }],
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
        mockRPC: function (route, args) {
            if (args.method === 'channel_set_custom_name') {
                assert.step(args.method);
                assert.strictEqual(args.args[0], 1);
                assert.strictEqual(args.kwargs.name, "Demo");
                return Promise.resolve("Demo");
            }
            return this._super.apply(this, arguments);
        },
    });

    var $dm = discuss.$('.o_mail_discuss_item[data-thread-id=1]');
    assert.isVisible($dm, "should display DM in the discuss sidebar");
    assert.strictEqual($dm.find('.o_thread_name').text().trim(), "Demo User");

    // The settings icon is only shown when hovering on sidebar item.
    // helpter dom.click needs the element to be visible, hence the
    // hack on display of this icon.
    discuss.$('.o_mail_channel_settings').css('display', 'block');
    await testUtils.dom.click(discuss.$('.o_mail_channel_settings'));

    assert.isVisible($('.modal-dialog'));
    assert.strictEqual($('.modal-title').text(), "Rename conversation");
    assert.isVisible($('.o_mail_discuss_rename_channel_input'));
    assert.strictEqual($('.o_mail_discuss_rename_channel_input').val(), "Demo User");

    await testUtils.fields.editInput($('.o_mail_discuss_rename_channel_input'), "Demo");
    await testUtils.dom.click($('.o_mail_conversation_rename'));
    $dm = discuss.$('.o_mail_discuss_item[data-thread-id=1]');
    assert.verifySteps(['channel_set_custom_name']);
    assert.strictEqual($dm.find('.o_thread_name').text().trim(), "Demo");

    discuss.destroy();
});

QUnit.test('custom-named DM conversation', async function (assert) {
    assert.expect(2);

    this.data.initMessaging = {
        channel_slots: {
            channel_direct_message: [{
                id: 1,
                channel_type: "chat",
                create_uid: 3,
                direct_partner: [{
                    id: 7,
                    im_status: 'online',
                    name: 'Demo User',
                }],
                custom_channel_name: 'My Buddy',
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        session: { partner_id: 3 },
    })

    var $dm = discuss.$('.o_mail_discuss_item[data-thread-id=1]');
    assert.isVisible($dm, "should display DM in the discuss sidebar");
    assert.strictEqual($dm.find('.o_thread_name').text().trim(), "My Buddy");

    discuss.destroy();
});

QUnit.test('input not cleared on unresolved message_post rpc', async function (assert) {
    assert.expect(2);

    // Promise to simulate late server response on message post
    var messagePostPromise = testUtils.makeTestPromise();

    this.data.initMessaging = {
        channel_slots: {
            channel_channel: [{
                id: 1,
                channel_type: "channel",
                name: "general",
            }],
        },
    };

    var discuss = await createDiscuss({
        id: 1,
        context: {},
        params: {},
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'message_post') {
                return messagePostPromise;
            }
            return this._super.apply(this, arguments);
        },
    });

    // Click on channel 'general'
    var $general = discuss.$('.o_mail_discuss_sidebar').find('.o_mail_discuss_item[data-thread-id=1]');
    await testUtils.dom.click($general);

    // Type message
    var $input = discuss.$('textarea.o_composer_text_field').first();
    $input.focus();
    $input.val('test message');

    // Send message
    await testUtils.fields.triggerKeydown($input, 'enter');
    assert.strictEqual($input.val(), 'test message', "composer should not be cleared on send without server response");

    // Simulate server response
    messagePostPromise.resolve();
    await testUtils.nextTick();
    assert.strictEqual($input.val(), '', "composer should be cleared on send after server response");
    discuss.destroy();
});
});
});
