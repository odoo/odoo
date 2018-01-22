odoo.define('web.FlashMessages_tests', function (require) {
"use strict";

var session = require('web.session');
var FlashMessages = require('web.FlashMessages');

QUnit.module('widgets', {}, function () {
QUnit.module('FlashMessages', {}, function () {
    QUnit.test('no messages', function (assert) {
        var done = assert.async();
        assert.expect(1);
        var $target = $('#qunit-fixture');

        session.flashes = [];
        var messages = new FlashMessages();
        messages.appendTo($target)
        .then(function () {
            // no messages in session -> no items in flash
            assert.strictEqual(messages.el.childElementCount, 0);
        })
        .always(function () {
            messages.destroy();
            done();
        });
    });

    QUnit.test('one message', function (assert) {
        var done = assert.async();
        assert.expect(2);
        var $target = $('#qunit-fixture');

        session.flashes = ['a message'];
        var messages = new FlashMessages();
        messages.appendTo($target)
        .then(function () {
            assert.strictEqual(messages.el.childElementCount, 1);
            assert.strictEqual(
                messages.$('p').text(),
                'a message'
            );
        })
        .always(function () {
            messages.destroy();
            done();
        });
    });
    QUnit.test('several messages', function (assert) {
        var done = assert.async();
        assert.expect(2);
        var $target = $('#qunit-fixture');

        session.flashes = ['1', '2', '3'];
        var messages = new FlashMessages();
        messages.appendTo($target)
        .then(function () {
            assert.strictEqual(messages.el.childElementCount, 3);
            assert.deepEqual(
                messages.$('p').map(function (_, e) {return e.textContent; }).toArray(),
                ['1', '2', '3']
            );
        })
        .always(function () {
            messages.destroy();
            done();
        });
    });

    QUnit.test('synchronized removal', function (assert) {
        var done = assert.async();
        assert.expect(5);
        var $target = $('#qunit-fixture');

        session.flashes = ['1', '2', '3'];
        var m1 = new FlashMessages();
        var m2 = new FlashMessages();
        $.when(m1.appendTo($target), m2.appendTo($target))
        .then(function () {
            assert.strictEqual(m1.el.childElementCount, 3);
            assert.strictEqual(m2.el.childElementCount, 3);

            return $.Deferred(function (d) {
                session.once('flash_remove', {}, function () {
                    d.resolve();
                });
                // click the close button on the 3rd message on the 1st flash
                m1.$el.find('button.close:eq(2)').click();
            }).promise();
        })
        .then(function () {
            assert.deepEqual(
                session.flashes, ['1', '2'],
                "the 3rd message should have been removed from the session");
            assert.strictEqual(
                m1.$el.find('p').text(), '12',
                "the 1st flash list should have been re-rendered without the removed message");
            assert.strictEqual(
                m2.$el.find('p').text(), '12',
                "the 2nd flash list should have been re-rendered without the removed message");
        })
        .always(function () {
            m1.destroy();
            m2.destroy();
            done();
        });
    });
});
});
});
