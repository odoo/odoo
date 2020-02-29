odoo.define('mail.blankThreadWindowTests', function (require) {
"use strict";

var AbstractThreadWindow = require('mail.AbstractThreadWindow');
var mailTestUtils = require('mail.testUtils');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('mail', {}, function () {
QUnit.module('Thread Window', {}, function () {
QUnit.module('Blank', {
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

        /**
         * Patch autocomplete so that we can detect when 'source' or 'select'
         * functions end.
         *
         * @param {Object} params
         * @param {Promise} params.selectDef
         * @param {Promise} params.sourceDef
         */
        this.patchAutocomplete = function (params) {
            var selectDef = params.selectDef;
            var sourceDef = params.sourceDef;
            self.ORIGINAL_AUTOCOMPLETE = $.fn.autocomplete;
            $.fn.autocomplete = function (params) {
                var select = params.select;
                var source = params.source;
                params.select = function () {
                    select.apply(this, arguments);
                    selectDef.resolve();
                };
                params.source = function () {
                    source.apply(this, arguments);
                    sourceDef.resolve();
                };
                return self.ORIGINAL_AUTOCOMPLETE.apply(this, arguments);
            };
        };
        /**
         * Unpatch autocomplete
         */
        this.unpatchAutocomplete = function () {
            $.fn.autocomplete = self.ORIGINAL_AUTOCOMPLETE;
        };
    },
    afterEach: function () {
        // reset thread window append to body
        this.services.mail_service.prototype.THREAD_WINDOW_APPENDTO = 'body';
    },
});

QUnit.test('basic rendering blank thread window', async function (assert) {
    assert.expect(5);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    // open blank thread window
    parent.call('mail_service', 'openBlankThreadWindow');
    await testUtils.nextMicrotaskTick();
    assert.strictEqual($('.o_thread_window').length, 1,
        "should have a thread window open");
    assert.strictEqual($('.o_thread_window_title').text().trim(),
        "New message",
        "the blank window should have the correct title");
    assert.strictEqual($('.o_composer_text_field').length, 0,
        "should have no composer in the blank window");
    assert.strictEqual($('.o_thread_search_input input').length, 1,
        "the blank window should have an input");
    assert.strictEqual($('.o_thread_search_input span').text().trim(),
        "To:",
        "the blank window should propose to type a partner next to the input");

    parent.destroy();
});

QUnit.test('close blank thread window', async function (assert) {
    assert.expect(1);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    // open blank thread window
    parent.call('mail_service', 'openBlankThreadWindow');
    await testUtils.nextMicrotaskTick();

    await testUtils.dom.click($('.o_thread_window_close'));

    assert.strictEqual($('.o_thread_window').length, 0,
        "blank thread window should be closed");

    parent.destroy();
});

QUnit.test('fold blank thread window', async function (assert) {
    // This test requires full height of thread windows when they are open.
    // (e.g. 400px)
    assert.expect(3);

    var parent = this.createParent({
        data: this.data,
        services: this.services,
    });

    var HEIGHT_FOLDED = AbstractThreadWindow.prototype.HEIGHT_FOLDED;
    var HEIGHT_OPEN = AbstractThreadWindow.prototype.HEIGHT_OPEN;

    // Make fold animation instantaneous
    testUtils.mock.patch(AbstractThreadWindow, {
        FOLD_ANIMATION_DURATION: 0,
    });

    // Open blank thread window
    parent.call('mail_service', 'openBlankThreadWindow');
    await testUtils.nextTick();

    assert.containsOnce(document.body, '.o_thread_window');
    assert.strictEqual($('.o_thread_window').css('height'), HEIGHT_OPEN,
        "blank thread window should be open");
    if ($('.o_thread_window').css('height') !== HEIGHT_OPEN) {
        console.warn('Assertion above may fail due to too narrow height of browser');
    }

    await testUtils.dom.click($('.o_thread_window_title'));
    assert.strictEqual($('.o_thread_window').css('height'), HEIGHT_FOLDED,
        "blank thread window should be folded");

    parent.destroy();
    testUtils.mock.unpatch(AbstractThreadWindow);
});

QUnit.test('open new DM chat from blank thread window', async function (assert) {
    assert.expect(6);
    var done = assert.async();

    var self = this;
    var selectDef = testUtils.makeTestPromise();
    var sourceDef = testUtils.makeTestPromise();

    this.patchAutocomplete({
        selectDef: selectDef,
        sourceDef: sourceDef,
    });

    var def = testUtils.makeTestPromise();

    this.data['res.partner'] = {
        fields: {},
        records: [],
    };

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'im_search') {
                def.resolve();
                return Promise.resolve([
                    { id: 1, name: 'DemoUser1' },
                    { id: 2, name: 'DemoUser2', }
                ]);
            }
            if (args.method === 'channel_get_and_minimize') {
                return Promise.resolve({
                    channel_type: 'chat',
                    direct_partner: [{ id: args.args[0][0], name: 'DemoUser1', im_status: '' }],
                    id: 50,
                    is_minimized: true,
                    name: 'DemoUser1',
                });
            }
            return this._super.apply(this, arguments);
        },
    });

    // open blank thread window
    parent.call('mail_service', 'openBlankThreadWindow');
    await testUtils.nextMicrotaskTick();
    await testUtils.fields.editAndTrigger($('.o_thread_search_input input'), 'D', 'keydown');
    await testUtils.nextTick();
    await Promise.all([sourceDef, def]);
    await testUtils.nextTick();
    assert.strictEqual($('.ui-menu-item a').length, 2,
        "should suggest 2 partners for DM");
    assert.strictEqual($('.ui-menu-item a').eq(0).text(), "DemoUser1",
        "first suggestion should be 'DemoUser1'");
    assert.strictEqual($('.ui-menu-item a').eq(1).text(), "DemoUser2",
        "second suggestion should be 'DemoUser2'");

    await testUtils.dom.clickFirst($('.ui-menu-item a'),{allowInvisible:true});
    await testUtils.nextTick();
    selectDef.then(function () {
        assert.strictEqual($('.o_thread_window').length, 1,
            "should be a single window");
        assert.strictEqual($('.o_thread_window_title').text().trim(), "DemoUser1",
            "should have thread window of the DM chat with 'DemoUser1'");
        assert.strictEqual($('.o_composer_text_field').length, 1,
            "should have a composer in the DM chat window");

        self.unpatchAutocomplete();
        parent.destroy();
        done();
    });
});

QUnit.test('open already detached DM chat from blank thread window', async function (assert) {
    // when opening an already detach DM chat from the blank thread window,
    // the blank thread window should disappear
    assert.expect(6);
    var done = assert.async();

    var self = this;
    var selectDef = testUtils.makeTestPromise();
    var sourceDef = testUtils.makeTestPromise();

    this.patchAutocomplete({
        selectDef: selectDef,
        sourceDef: sourceDef,
    });

    var def = testUtils.makeTestPromise();

    this.data['res.partner'] = {
        fields: {},
        records: [],
    };
    this.data.initMessaging.channel_slots.channel_dm = [{
        channel_type: 'chat',
        direct_partner: [{ id: 1, name: 'DemoUser1', im_status: '' }],
        id: 50,
        is_minimized: true,
        name: 'DemoUser1',
    }];

    var parent = this.createParent({
        data: this.data,
        services: this.services,
        mockRPC: function (route, args) {
            if (args.method === 'im_search') {
                def.resolve();
                return Promise.resolve([
                    { id: 1, name: 'DemoUser1' },
                ]);
            }
            return this._super.apply(this, arguments);
        },
    });

    await testUtils.nextTick();
    assert.strictEqual($('.o_thread_window').length, 1,
        "should be a single window");
    assert.strictEqual($('.o_thread_window_title').text().trim(), "DemoUser1",
        "should have thread window of the DM chat with 'DemoUser1'");
    assert.strictEqual($('.o_composer_text_field').length, 1,
        "should have a composer in the DM chat window");

    // open blank thread window
    parent.call('mail_service', 'openBlankThreadWindow');
    await testUtils.nextMicrotaskTick();
    assert.strictEqual($('.o_thread_window').length, 2,
        "should have two thread windows open");
    await testUtils.fields.editAndTrigger($('.o_thread_search_input input'), 'D', 'keydown');


    await Promise.all([sourceDef, def]);
    await testUtils.nextTick();
    await testUtils.dom.click($('.ui-menu-item a'),{allowInvisible:true});
    await testUtils.nextTick();
    selectDef.then(function () {
        assert.strictEqual($('.o_thread_window').length, 1,
            "should now have a single thread window open");
        assert.strictEqual($('.o_thread_window_title').text().trim(), "DemoUser1",
            "the remaining thread window should be the DM chat with 'DemoUser1'");

        self.unpatchAutocomplete();
        parent.destroy();
        done();
    });
});

});
});
});
