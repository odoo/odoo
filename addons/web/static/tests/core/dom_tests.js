odoo.define('web.dom_tests', function (require) {
"use strict";

var dom = require('web.dom');

/**
 * Create an autoresize text area with 'border-box' as box sizing rule.
 * The minimum height of this autoresize text are is 1px.
 *
 * @param {Object} [options={}]
 * @param {integer} [options.borderBottomWidth=0]
 * @param {integer} [options.borderTopWidth=0]
 * @param {integer} [options.padding=0]
 */
function prepareAutoresizeTextArea(options) {
    options = options || {};
    var $textarea = $('<textarea>');
    $textarea.css('box-sizing', 'border-box');
    $textarea.css({
        padding: options.padding || 0,
        borderTopWidth: options.borderTopWidth || 0,
        borderBottomWidth: options.borderBottomWidth || 0,
    });
    $textarea.appendTo($('#qunit-fixture'));
    dom.autoresize($textarea, { min_height: 1 });
    return $textarea;
}

QUnit.module('core', {}, function () {
QUnit.module('dom', {}, function () {

    QUnit.module('autoresize');

    QUnit.test('autoresize (border-box): no padding + no border', function (assert) {
        assert.expect(3);
        var $textarea = prepareAutoresizeTextArea();
        assert.strictEqual($('textarea').length, 2,
            "there should be two textareas in the DOM");

        $textarea = $('textarea:eq(0)');
        var $fixedTextarea = $('textarea:eq(1)');
        assert.strictEqual($textarea.css('height'),
            $fixedTextarea[0].scrollHeight + 'px',
            "autoresized textarea should have height of fixed textarea + padding (0 line)");

        $textarea.val('a\nb\nc\nd').trigger('input');
        assert.strictEqual($textarea.css('height'),
            $fixedTextarea[0].scrollHeight + 'px',
            "autoresized textarea should have height of fixed textarea + padding (4 lines)");
    });

    QUnit.test('autoresize (border-box): padding + no border', function (assert) {
        assert.expect(3);
        var $textarea = prepareAutoresizeTextArea({ padding: 10 });
        assert.strictEqual($('textarea').length, 2,
            "there should be two textareas in the DOM");

        $textarea = $('textarea:eq(0)');
        var $fixedTextarea = $('textarea:eq(1)');
        // twice the padding of 10px
        var expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + 2*10;
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + padding (0 line)");

        $textarea.val('a\nb\nc\nd').trigger('input');
        // twice the padding of 10px
        expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + 2*10;
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + padding (4 lines)");
    });

    QUnit.test('autoresize (border-box): no padding + border', function (assert) {
        assert.expect(3);
        var $textarea = prepareAutoresizeTextArea({
            borderTopWidth: 2,
            borderBottomWidth: 3,
        });
        assert.strictEqual($('textarea').length, 2,
            "there should be two textareas in the DOM");

        $textarea = $('textarea:eq(0)');
        var $fixedTextarea = $('textarea:eq(1)');
        // top (2px) + bottom (3px) borders
        var expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + (2 + 3);
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + border (0 line)");

        $textarea.val('a\nb\nc\nd').trigger('input');
        // top (2px) + bottom (3px) borders
        expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + (2 + 3);
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + border (4 lines)");
    });

    QUnit.test('autoresize (border-box): padding + border', function (assert) {
        assert.expect(3);
        var $textarea = prepareAutoresizeTextArea({
            padding: 10,
            borderTopWidth: 2,
            borderBottomWidth: 3,
        });
        assert.strictEqual($('textarea').length, 2,
            "there should be two textareas in the DOM");

        $textarea = $('textarea:eq(0)');
        var $fixedTextarea = $('textarea:eq(1)');
        // twice padding (10px) + top (2px) + bottom (3px) borders
        var expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + (2*10 + 2 + 3);
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + border (0 line)");

        $textarea.val('a\nb\nc\nd').trigger('input');
        // twice padding (10px) + top (2px) + bottom (3px) borders
        expectedTextAreaHeight = $fixedTextarea[0].scrollHeight + (2*10 + 2 + 3);
        assert.strictEqual($textarea.css('height'),
            expectedTextAreaHeight + 'px',
            "autoresized textarea should have height of fixed textarea + border (4 lines)");
    });

});

});
});
