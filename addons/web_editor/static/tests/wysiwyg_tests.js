odoo.define('web_editor.wysiwyg_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var Wysiwyg = require('web_editor.wysiwyg');
var AltDialog = require('wysiwyg.widgets.AltDialog');
var CropDialog = require('wysiwyg.widgets.CropImageDialog');

var testName = "";
var carretTestSuffix = " (carret position)";

QUnit.module('web_editor', {
    afterEach: function () {
        $('body').removeClass('modal-open');
        $('.note-popover, .modal, .modal-backdrop').remove();
    },
}, function () {
QUnit.module('wysiwyg', {}, function () {
QUnit.module('toolbar', {}, function () {

QUnit.test('Magic wand', async function (assert) {
    assert.expect(8);

    var wysiwyg = await weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    });
    var $editable = wysiwyg.$('.note-editable');

    var $dropdownStyle = wysiwyg.$('.note-style .dropdown-toggle');
    var $btnsStyle = wysiwyg.$('.note-style .dropdown-menu .dropdown-item');

    var wandTests = [{
        name: "Click H1: p -> h1",
        content: '<p>dom not to edit</p><p>dom to edit</p>',
        start: 'p:eq(1):contents()[0]->1',
        do: async function () {
            await testUtils.dom.triggerEvents($dropdownStyle, ['mousedown', 'click']);
            await testUtils.dom.triggerEvents($btnsStyle.find('h1'), ['mousedown', 'click']);
        },
        test: {
            content: '<p>dom not to edit</p><h1>dom to edit</h1>',
            start: 'h1:contents()[0]->0',
            end: 'h1:contents()[0]->11',
        },
    },
    {
        name: "Click CODE: h1 -> pre",
        content: '<p>dom not to edit</p><h1>dom to edit</h1>',
        start: 'h1:contents()[0]->1',
        do: async function () {
            await testUtils.dom.triggerEvents($dropdownStyle, ['mousedown', 'click']);
            await testUtils.dom.triggerEvents($btnsStyle.find('pre'), ['mousedown', 'click']);
        },
        test: {
            content: '<p>dom not to edit</p><pre>dom to edit</pre>',
            start: 'pre:contents()[0]->0',
            end: 'pre:contents()[0]->11',
        },
    },
    {
        name: "Click NORMAL: pre -> p",
        content: '<p>dom not to edit</p><pre>dom to edit</pre>',
        start: 'pre:contents()[0]->1',
        do: async function () {
            await testUtils.dom.triggerEvents($dropdownStyle, ['mousedown', 'click']);
            await testUtils.dom.triggerEvents($btnsStyle.find('p'), ['mousedown', 'click']);
        },
        test: {
            content: '<p>dom not to edit</p><p>dom to edit</p>',
            start: 'p:eq(1):contents()[0]->0',
            end: 'p:eq(1):contents()[0]->11',
        },
    },
    {
        name: "Click H1 in empty p: empty p -> empty h1",
        content: '<p><br></p>',
        start: 'p->1',
        do: async function () {
            await testUtils.dom.triggerEvents($dropdownStyle, ['mousedown', 'click']);
            await testUtils.dom.triggerEvents($btnsStyle.find('h1'), ['mousedown', 'click']);
        },
        test: {
            content: '<h1><br></h1>',
            start: 'h1:contents()[0]->0',
        },
    },
    ];

    var def = Promise.resolve();
    wandTests.forEach(function (test) {
        def = def.then(async function() {
            testName = test.name;
            wysiwyg.setValue(test.content);
            var range = weTestUtils.select(test.start, test.end, $editable);
            Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
            await testUtils.nextTick();
            await test.do();
            assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
            assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
        });
    });

    return def.then(function() {
        wysiwyg.destroy();
    });
});

QUnit.test('Font style', function (assert) {
    assert.expect(58);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            generateOptions: function (options) {
                options.toolbar[1][1] = ['bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript', 'clear'];
            },
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $btnBold = wysiwyg.$('.note-font .note-btn-bold');
        var $btnItalic = wysiwyg.$('.note-font .note-btn-italic');
        var $btnUnderline = wysiwyg.$('.note-font .note-btn-underline');
        var $strikethrough = wysiwyg.$('.note-font .note-icon-strikethrough');
        var $superscript = wysiwyg.$('.note-font .note-icon-superscript');
        var $subscript = wysiwyg.$('.note-font .note-icon-subscript');
        var $btnRemoveStyles = wysiwyg.$('.note-font .btn-sm .note-icon-eraser');

        var styleTests = [
            /* BOLD */
            {
                name: "Click BOLD: normal -> bold",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<b>om t</b>o edit</p>',
                    start: 'b:contents()[0]->0',
                    end: 'b:contents()[0]->4',
                },
            },
            {
                name: "Click BOLD then 'a': normal -> bold (empty p)",
                content: '<p><br></p>',
                start: 'p->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable);
                },
                test: {
                    content: '<p><b>a</b></p>',
                    start: 'b:contents()[0]->1',
                },
            },
            {
                name: "Click BOLD: normal -> bold (across paragraphs)",
                content: '<p>dom to edit</p><p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<b>om to edit</b></p><p><b>dom t</b>o edit</p>',
                    start: 'b:contents()[0]->0',
                    end: 'b:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click BOLD then 'a': normal -> bold (no selection)",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->4',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom <b>a</b>to edit</p>',
                    start: 'b:contents()[0]->1',
                },
            },
            {
                name: "Click BOLD: bold -> normal",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->0',
                end: 'b:contents()[0]->11',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->0',
                    end: 'p:eq(1):contents()[0]->11',
                },
            },
            {
                name: "Click BOLD: bold -> normal (partial selection)",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->4',
                end: 'b:contents()[0]->6',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>dom </b>to<b>&nbsp;edit</b></p>',
                    start: 'p:eq(1):contents()[1]->0',
                    end: 'p:eq(1):contents()[1]->2',
                },
            },
            {
                name: "Click BOLD: bold -> normal (no selection)",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->4',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>dom </b>\u200B<b>to edit</b></p>',
                    start: 'p:eq(1):contents()[1]->1',
                },
            },
            {
                name: "Click BOLD: bold + normal -> normal",
                content: '<p><b>dom </b>to edit</p>',
                start: 'b:contents()[0]->1',
                end: 'p:contents()[1]->4',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p><b>dom to e</b>dit</p>',
                    start: 'b:contents()[0]->1',
                    end: 'b:contents()[0]->8',
                },
            },
            {
                name: "Click BOLD: normal -> bold (with fontawesome)",
                content: '<p>aaa<span class="fa fa-heart"></span>bbb</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[2]->2',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>a<b>aa<span class="fa fa-heart"></span>bb</b>b</p>',
                    start: 'b:contents()[0]->0',
                    end: 'b:contents()[2]->2',
                },
            },
            {
                name: "Click BOLD + click BOLD: normal -> bold -> normal (with fontawesome)",
                content: '<p>aaa<span class="fa fa-heart"></span>bbb</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[2]->2',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>aaa<span class="fa fa-heart"></span>bbb</p>',
                    start: 'p:contents()[0]->1',
                    end: 'p:contents()[2]->2',
                },
            },
            {
                name: "Click BOLD: bold -> normal (with fontawesome)",
                content: '<p><b>aaa<span class="fa fa-heart"></span>bbb</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[2]->2',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p><b>a</b>aa<span class="fa fa-heart"></span>bb<b>b</b></p>',
                    start: 'p:contents()[1]->0',
                    end: 'p:contents()[3]->2',
                },
            },
            {
                name: "Click BOLD: bold -> normal (at start of dom)",
                content: '<p><b>abc</b></p>',
                start: 'b:contents()[0]->0',
                do: function () {
                    $btnBold.mousedown().click();
                },
                test: {
                    content: '<p>\u200B<b>abc</b></p>',
                    start: 'p:contents()[0]->1',
                    end: 'p:contents()[0]->1',
                },
            },
            /* ITALIC */
            {
                name: "Click ITALIC: bold -> bold + italic",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnItalic, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d<i>om t</i>o edit</b></p>',
                    start: 'i:contents()[0]->0',
                    end: 'i:contents()[0]->4',
                },
            },
            {
                name: "Click ITALIC: bold & normal -> italic & bold + italic (across paragraphs)",
                content: '<p>dom <b>to</b> edit</p><p><b>dom to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnItalic, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<i>om <b>to</b> edit</i></p><p><b><i>dom t</i>o edit</b></p>',
                    start: 'i:contents()[0]->0',
                    end: 'i:eq(1):contents()[0]->5',
                },
            },
            /* UNDERLINE */
            {
                name: "Click UNDERLINE: bold -> bold + underlined",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUnderline, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d<u>om t</u>o edit</b></p>',
                    start: 'u:contents()[0]->0',
                    end: 'u:contents()[0]->4',
                },
            },
            {
                name: "Click UNDERLINE: bold & normal -> underlined & bold + underlined (across paragraphs)",
                content: '<p>dom <b>to</b> edit</p><p><b>dom to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUnderline, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<u>om <b>to</b> edit</u></p><p><b><u>dom t</u>o edit</b></p>',
                    start: 'u:contents()[0]->0',
                    end: 'u:eq(1):contents()[0]->5',
                },
            },
            /* strikethrough */
            {
                name: "Click strikethrough: bold -> bold + strikethrough",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($strikethrough, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d<s>om t</s>o edit</b></p>',
                    start: 's:contents()[0]->0',
                    end: 's:contents()[0]->4',
                },
            },
            {
                name: "Click strikethrough: bold & normal -> strikethrough & bold + strikethrough (across paragraphs)",
                content: '<p>dom <b>to</b> edit</p><p><b>dom to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($strikethrough, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<s>om <b>to</b> edit</s></p><p><b><s>dom t</s>o edit</b></p>',
                    start: 's:contents()[0]->0',
                    end: 's:eq(1):contents()[0]->5',
                },
            },
            /* superscript */
            {
                name: "Click superscript: bold -> bold + superscript",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($superscript, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d<sup>om t</sup>o edit</b></p>',
                    start: 'sup:contents()[0]->0',
                    end: 'sup:contents()[0]->4',
                },
            },
            {
                name: "Click superscript: bold & normal -> superscript & bold + superscript (across paragraphs)",
                content: '<p>dom <b>to</b> edit</p><p><b>dom to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($superscript, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<sup>om <b>to</b> edit</sup></p><p><b><sup>dom t</sup>o edit</b></p>',
                    start: 'sup:contents()[0]->0',
                    end: 'sup:eq(1):contents()[0]->5',
                },
            },
            /* subscript */
            {
                name: "Click subscript: bold -> bold + subscript",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($subscript, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d<sub>om t</sub>o edit</b></p>',
                    start: 'sub:contents()[0]->0',
                    end: 'sub:contents()[0]->4',
                },
            },
            {
                name: "Click subscript: bold & normal -> subscript & bold + subscript (across paragraphs)",
                content: '<p>dom <b>to</b> edit</p><p><b>dom to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($subscript, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<sub>om <b>to</b> edit</sub></p><p><b><sub>dom t</sub>o edit</b></p>',
                    start: 'sub:contents()[0]->0',
                    end: 'sub:eq(1):contents()[0]->5',
                },
            },
            /* REMOVE FONT STYLE */
            {
                name: "Click REMOVE FONT STYLE: bold -> normal",
                content: '<p>dom not to edit</p><p><b>dom to edit</b></p>',
                start: 'b:contents()[0]->1',
                end: 'b:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnRemoveStyles, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><b>d</b>om t<b>o edit</b></p>',
                    start: 'p:eq(1):contents()[1]->0',
                    end: 'p:eq(1):contents()[1]->4',
                },
            },
            {
                name: "Click REMOVE FONT STYLE: bold, italic, underlined & normal -> normal (across paragraphs)",
                content: '<p>dom <b>t<i>o</i></b> e<u>dit</u></p><p><b><u>dom</u> to edit</b></p>',
                start: 'p:contents()[0]->1',
                end: 'u:eq(1):contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnRemoveStyles, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom to edit</p><p>dom<b>&nbsp;to edit</b></p>',
                    start: 'p:contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->3',
                },
            },
            {
                name: "Click REMOVE FONT STYLE: complex -> normal",
                content: '<p>aaa<font style="background-color: rgb(255, 255, 0);">bbb</font></p><p><font style="color: rgb(255, 0, 0);">ccc</font></p>',
                start: 'p:contents()[0]->1',
                end: 'font:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnRemoveStyles, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>aaabbb</p><p>c<font style="color: rgb(255, 0, 0);">cc</font></p>',
                    start: 'p:contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click REMOVE FONT STYLE: complex -> normal (with icon)",
                content: '<p>a<b>a</b>a<span class="bg-alpha text-alpha fa fa-heart" style="font-size: 10px;"></span>b<b><i>b</i>b</b></p>',
                start: 'p:contents()[0]->0',
                end: 'i:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnRemoveStyles, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>aaa<span class="fa fa-heart"></span>bb<b>b</b></p>',
                    start: 'p:contents()[0]->0',
                    end: 'p:contents()[2]->2',
                },
            },
            /* COMPLEX */
            {
                name: "COMPLEX Click BOLD: italic -> italic bold (partial selection)",
                content: '<p>dom not to edit</p><p><i>dom to edit</i></p>',
                start: 'i:contents()[0]->1',
                end: 'i:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><i>d<b>om t</b>o edit</i></p>',
                    start: 'b:contents()[0]->0',
                    end: 'b:contents()[0]->4',
                },
            },
            {
                name: "COMPLEX Click BOLD then 'a': italic bold -> italic (across paragraphs)",
                content: '<p><b><i>dom to edit</i></b></p><p><i><b>dom to edit</b></i></p>',
                start: 'i:contents()[0]->1',
                end: 'b:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p><b><i>d</i></b><i>om to edit</i></p><p><i>dom ta<b>o edit</b></i></p>',
                },
            },
            {
                name: "COMPLEX Click BOLD then 'a': bold italic -> italic (no selection)",
                content: '<p><b><i>dom to edit</i></b></p>',
                start: 'i:contents()[0]->4',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p><b><i>dom </i></b><i>a</i><b><i>to edit</i></b></p>',
                },
            },
            {
                name: "COMPLEX Click BOLD then 'a': underlined italic -> underlined italic bold (across paragraphs)",
                content: '<p><u><i>dom to edit</i></u></p><p><i><u>dom to edit</u></i></p>',
                start: 'i:contents()[0]->1',
                end: 'u:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p><u><i>d<b>om to edit</b></i></u></p><p><i><u><b>dom ta</b>o edit</u></i></p>',
                },
            },
            {
                name: "COMPLEX Click BOLD then 'a': underlined italic -> underlined italic bold (no selection)",
                content: '<p><u><i>dom to edit</i></u></p>',
                start: 'i:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnBold, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p><u><i>d<b>a</b>om to edit</i></u></p>',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(styleTests, function (test) {
            def = def.then(async function() {
                testName = test.name;
                wysiwyg.setValue(test.content);
                test.end = test.end || test.start;
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                $editable[0].normalize();
                if (test.test.start) {
                    test.test.end = test.test.end || test.test.start;
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
                }
            });
        });

        return def.then(function() {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Font size', function (assert) {
    assert.expect(10);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $dropdownFontSize = wysiwyg.$('.note-fontsize .dropdown-toggle');
        var $linksFontSize = wysiwyg.$('.note-fontsize .dropdown-menu .dropdown-item');

        var sizeTests = [{
                name: "Click 18: default -> 18px",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownFontSize, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($linksFontSize.filter(':contains("18")'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font style="font-size: 18px;">om t</font>o edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
            {
                name: "Click DEFAULT: 18px -> default",
                content: '<p>dom not to edit</p><p><font style="font-size: 18px;">dom to edit</font></p>',
                start: 'font:contents()[0]->1',
                end: 'font:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownFontSize, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($linksFontSize.filter(':contains("Default")'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p><font style="font-size: 18px;">d</font>om t<font style="font-size: 18px;">o edit</font></p>',
                    start: 'p:eq(1):contents()[1]->0',
                    end: 'p:eq(1):contents()[1]->4',
                },
            },
            {
                name: "Click 18: 26px -> 18px",
                content: '<p><font style="font-size: 26px;">dom to edit</font></p>',
                start: 'font:contents()[0]->1',
                end: 'font:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownFontSize, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($linksFontSize.filter(':contains("18")'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>' +
                        '<font style="font-size: 26px;">d</font>' +
                        '<font style="font-size: 18px;">om t</font>' +
                        '<font style="font-size: 26px;">o edit</font></p>',
                    start: 'font:eq(1):contents()[0]->0',
                    end: 'font:eq(1):contents()[0]->4',
                },
            },
            {
                name: "Click 18 then 'a' (no selection): default -> 18px",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownFontSize, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($linksFontSize.filter(':contains("18")'), ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font style="font-size: 18px;">a</font>om to edit</p>',
                    start: 'font:contents()[0]->1',
                },
            },
            {
                name: "Click 18 then 'a' (no selection): 26px -> 18px",
                content: '<p><font style="font-size: 26px;">dom to edit</font></p>',
                start: 'font:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownFontSize, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($linksFontSize.filter(':contains("18")'), ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p>' +
                        '<font style="font-size: 26px;">d</font>' +
                        '<font style="font-size: 18px;">a</font>' +
                        '<font style="font-size: 26px;">om to edit</font></p>',
                    start: 'font:eq(1):contents()[0]->1',
                },
            },
            ];

            var def = Promise.resolve();
            _.each(sizeTests, function (test) {
                def = def.then(async function() {
                    testName = test.name;
                    wysiwyg.setValue(test.content);
                    var range = weTestUtils.select(test.start, test.end, $editable);
                    Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                    await test.do();
                    assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
                });
            });

            return def.then(function() {
                wysiwyg.destroy();
            });
        });
});

QUnit.test('Text forecolor', function (assert) {
        assert.expect(40);

        return weTestUtils.createWysiwyg({
            debug: false,
            wysiwygOptions: {
                tooltip: false,
            },
        }).then(function (wysiwyg) {
            var $editable = wysiwyg.$('.note-editable');

            var $dropdownForeColor = wysiwyg.$('.note-color .note-fore-color .dropdown-toggle');
            var $btnsForeColor = wysiwyg.$('.note-color .note-fore-color .dropdown-menu .note-palette .note-color-btn');
            var forecolorTests = [{
                name: "Click THEME COLORS - ALPHA: default -> alpha theme color",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('.bg-alpha'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font class="text-alpha">om t</font>o edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
            {
                name: "Click THEME COLORS - BLACK 25: alpha theme color & default -> black 25",
                content: '<p>dom not to edit</p><p>do<font class="text-alpha">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('.bg-black-25'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font class="text-black-25">om t</font><font class="text-alpha">o </font>edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
            {
                name: "Click COMMON COLORS - BLUE #0000FF: black 25 & default -> blue #0000FF",
                content: '<p>dom not to edit</p><p>do<font class="text-black-25">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font style="color: rgb(0, 0, 255);">om t</font><font class="text-black-25">o </font>edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
            {
                name: "Click RESET TO DEFAULT: black 25 & default -> default",
                content: '<p>dom not to edit</p><p>do<font class="text-black-25">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('.note-color-reset'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom t<font class="text-black-25">o </font>edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click CUSTOM COLORS then CUSTOM COLOR: blue #0000FF & default -> #875A7B",
                async: true,
                content: '<p>dom not to edit</p><p>do<font style="color: rgb(0, 0, 255);">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    var self = this;

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color'), ['mousedown', 'click']);

                    $('.modal-dialog .o_hex_input').val('#875A7B').change();
                    await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color-btn:last'), ['mousedown', 'click']);

                    assert.deepEqual(wysiwyg.getValue(),
                        '<p>dom not to edit</p><p>d<font style="color: rgb(135, 90, 123);">om t</font><font style="color: rgb(0, 0, 255);">o </font>edit</p>',
                        self.name);
                    var range = weTestUtils.select('font:contents()[0]->0', 'font:contents()[0]->4', $editable);
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), range, self.name + carretTestSuffix);
                },
            },
            {
                name: "Click CUSTOM COLORS then CUSTOM COLOR: change blue input",
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->6',
                do: async function () {
                    var self = this;

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color'), ['mousedown', 'click']);

                    $('.modal-dialog .o_blue_input').val('100').change();

                    assert.deepEqual($('.modal-dialog .o_hex_input').val(), '#ff0064', self.name + ' (hex)');
                    assert.deepEqual($('.modal-dialog .o_hue_input').val(), '337', self.name + ' (hue)');

                    await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color-btn:last'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgb(255, 0, 100);">om to</font> edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->5',
                },
            },
            {
                name: "CUSTOM COLOR: change hue, saturation and lightness inputs",
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->6',
                do: async function () {
                    var self = this;

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color'), ['mousedown', 'click']);

                        $('.modal-dialog .o_hue_input').val('337').change();
                        $('.modal-dialog .o_saturation_input').val('50').change();
                        $('.modal-dialog .o_lightness_input').val('40').change();

                        assert.deepEqual($('.modal-dialog .o_hex_input').val(), '#99335a', self.name + ' (hex)');
                        assert.deepEqual($('.modal-dialog .o_green_input').val(), '51', self.name + ' (green)');

                        await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color-btn:last'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgb(153, 51, 90);">om to</font> edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->5',
                },
            },
            {
                name: "CUSTOM COLOR: mousedown on area",
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->6',
                do: async function () {
                    var self = this;

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color'), ['mousedown', 'click']);

                        var $area = $('.modal-dialog .o_color_pick_area');
                        var pos = $area.offset();
                        $area.trigger($.Event("mousedown", {
                            which: 1,
                            pageX: pos.left + 50,
                            pageY: pos.top + 50
                        }));
                        $area.trigger('mouseup');

                        assert.deepEqual($('.modal-dialog .o_hex_input').val(), '#cfafaf', self.name + ' (hex)');
                        assert.deepEqual($('.modal-dialog .o_red_input').val(), '207', self.name + ' (red)');
                        assert.deepEqual($('.modal-dialog .o_green_input').val(), '175', self.name + ' (green)');
                        assert.deepEqual($('.modal-dialog .o_blue_input').val(), '175', self.name + ' (blue)');
                        assert.deepEqual($('.modal-dialog .o_hue_input').val(), '0', self.name + ' (hue)');
                        assert.deepEqual($('.modal-dialog .o_saturation_input').val(), '25', self.name + ' (saturation)');
                        assert.deepEqual($('.modal-dialog .o_lightness_input').val(), '75', self.name + ' (lightness)');

                        await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color-btn:last'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgb(207, 175, 175);">om to</font> edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->5',
                },
            },
            {
                name: "CUSTOM COLOR: mousedow on sliders",
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->6',
                do: async function () {
                    var self = this;

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color'), ['mousedown', 'click']);

                        var $slider1 = $('.modal-dialog .o_slider_pointer');
                        var pos1 = $slider1.offset();
                        $slider1.trigger($.Event("mousedown", {
                            which: 1,
                            pageX: pos1.left,
                            pageY: pos1.top + 50
                        }));
                        $slider1.trigger('mouseup');

                        assert.deepEqual($('.modal-dialog .o_hex_input').val(), '#83ff00', self.name + ' (hex)');

                        var $slider2 = $('.modal-dialog .o_opacity_slider');
                        var pos2 = $slider2.offset();
                        $slider2.trigger($.Event("mousedown", {
                            which: 1,
                            pageX: pos2.left,
                            pageY: pos2.top + 80
                        }));
                        $slider2.trigger('mouseup');

                        assert.deepEqual($('.modal-dialog .o_hue_input').val(), '89', self.name + ' (hue)');
                        assert.deepEqual($('.modal-dialog .o_opacity_input').val(), '60', self.name + ' (opacity)');

                        await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-fore-color .note-custom-color-btn:last'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgba(131, 255, 0, 0.6);">om to</font> edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->5',
                },
            },
            {
                name: "Apply a color on a fontawesome",
                content: '<p>dom <i class="fa fa-glass"/>not to edit</p>',
                start: 'i->0',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom <i class="fa fa-glass" style="color: rgb(0, 0, 255);"></i>not to edit</p>',
                    start: 'p->2',
                },
            },
            {
                name: "Apply a color on a font with text",
                content: '<p>dom <i class="fa fa-glass"/>not to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[2]->6',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgb(0, 0, 255);">om&nbsp;</font><i class="fa fa-glass" style="color: rgb(0, 0, 255);"></i><font style="color: rgb(0, 0, 255);">not to</font> edit</p>',
                    start: 'font:eq(0):contents()[0]->0',
                    end: 'font:eq(1):contents()[0]->6',
                },
            },
            {
                name: "Apply color, then 'a' (no selection)",
                content: '<p>dom not to edit</p>',
                start: 'p:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable, {
                        firstDeselect: true,
                    });
                },
                test: {
                    content: '<p>d<font style="color: rgb(0, 0, 255);">a</font>om not to edit</p>',
                    start: 'font:contents()[0]->1',
                },
            },
            {
                name: "Apply color on two ranges with the same color",
                content: '<p>do<br><span class="toto">       </span>m not to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[3]->4',
                do: async function ($editable) {
                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);

                    var range = weTestUtils.select('p:contents()[5]->3', 'p:contents()[5]->6', $editable);
                    Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

                    await testUtils.dom.triggerEvents($dropdownForeColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsForeColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>d<font style="color: rgb(0, 0, 255);">o</font><br><span class="toto">       </span><font style="color: rgb(0, 0, 255);">m no</font>t t<font style=\"color: rgb(0, 0, 255);\">o e</font>dit</p>',
                    start: 'font:eq(2):contents()[0]->0',
                    end: 'font:eq(2):contents()[0]->3',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(forecolorTests, function (test) {
            def = def.then(function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                return Promise.resolve(test.do($editable)).then(function () {
                    if (!test.async) {
                        assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                        assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
                    }
                });
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Text bgcolor', function (assert) {
    assert.expect(10);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');
        var testName = "";
        var carretTestSuffix = " (carret position)";

        var $dropdownBgColor = wysiwyg.$('.note-color .note-bg-color .dropdown-toggle');
        var $btnsBgColor = wysiwyg.$('.note-color .note-bg-color .dropdown-menu .note-palette .note-color-btn');

        var bgcolorTests = [{
                name: "Click THEME COLORS - ALPHA: default -> alpha theme color",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownBgColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsBgColor.filter('.bg-alpha'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font class="bg-alpha">om t</font>o edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
           {
                name: "Click THEME COLORS - BLACK 25: alpha theme color & default -> black 25",
                content: '<p>dom not to edit</p><p>do<font class="bg-alpha">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownBgColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsBgColor.filter('.bg-black-25'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font class="bg-black-25">om t</font><font class="bg-alpha">o </font>edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
            {
                name: "Click COMMON COLORS - BLUE #0000FF: black 25 & default -> blue #0000FF",
                content: '<p>dom not to edit</p><p>do<font class="bg-black-25">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownBgColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsBgColor.filter('[style="background-color:#0000FF"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>d<font style="background-color: rgb(0, 0, 255);">om t</font><font class="bg-black-25">o </font>edit</p>',
                    start: 'font:contents()[0]->0',
                    end: 'font:contents()[0]->4',
                },
            },
             {
                name: "Click RESET TO DEFAULT: black 25 & default -> default",
                content: '<p>dom not to edit</p><p>do<font class="bg-black-25">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownBgColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnsBgColor.filter('.note-color-reset'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom t<font class="bg-black-25">o </font>edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click CUSTOM COLORS then CUSTOM COLOR: blue #0000FF & default -> #875A7B",
                content: '<p>dom not to edit</p><p>do<font style="background-color: rgb(0, 0, 255);">m to </font>edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'font:contents()[0]->3',
                async: true,
                do: async function () {
                    testName = "Click CUSTOM COLORS then CUSTOM COLOR: blue #0000FF & default -> #875A7B";

                    await testUtils.dom.triggerEvents($dropdownBgColor, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-bg-color .note-custom-color'), ['mousedown', 'click']);
                    await testUtils.fields.editAndTrigger($('.modal-dialog .o_hex_input'), '#875A7B', 'change');
                    await testUtils.dom.triggerEvents($('.o_technical_modal .modal-footer .btn-primary:contains("Choose")'), ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents(wysiwyg.$('.note-color .note-bg-color .note-custom-color-btn:last'), ['mousedown', 'click']);

                    assert.deepEqual(wysiwyg.getValue(),
                        '<p>dom not to edit</p><p>d<font style="background-color: rgb(135, 90, 123);">om t</font><font style="background-color: rgb(0, 0, 255);">o </font>edit</p>',
                        testName);
                    var range = weTestUtils.select('font:contents()[0]->0',
                        'font:contents()[0]->4',
                        $editable);
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), range, testName + carretTestSuffix);
                },
            },
        ];

        var def = Promise.resolve();
        _.each(bgcolorTests, function (test) {
            def = def.then(async function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                if (!test.async) {
                    assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
                }
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Unordered list', function (assert) {
    assert.expect(34);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $btnUL = wysiwyg.$('.note-para .note-icon-unorderedlist');

        var ulTests = [{
                name: "Click UL: p -> ul",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click UL: p -> ul (across paragraphs)",
                content: '<p>dom not to edit</p><p>dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul -> p",
                content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click UL: p -> ul (across li's)",
                content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul -> p (from second li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><li><p>dom to edit</p></li></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnUL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li></ul><p>dom to edit</p>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            // Conversion from OL
            {
                name: "Click UL: ol -> ul",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li></ol>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ol -> ul (across li's)",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ol -> ul (from second li)",
                content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><li><p>dom to edit</p></li></ol>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>xxx</p></li></ol><ul><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ol -> ul ul (from indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ol><li><p>dom to edit</p></li></ol></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul><li><p>dom to edit</p></li></ul></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ol -> ul ul (across several indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ol><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ol></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ul></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ol -> ul ul (from second indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ol><li><p>dom not to edit</p></li><li><p>dom to edit</p></li><li><p>dom not to edit</p></li></ol></ul>',
                start: 'li:eq(2) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ol><li><p>dom not to edit</p></li></ol><ul><li><p>dom to edit</p></li></ul><ol><li><p>dom not to edit</p></li></ol></ul>',
                    start: 'p:eq(3):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            // Conversion from Checklist
            {
                name: "Click UL: ul.o_checklist -> ul",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul.o_checklist -> ul (across li's)",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul.o_checklist -> ul (from second li)",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>xxx</p></li><li><p>dom to edit</p></li></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>xxx</p></li></ul><ul><li><p>dom to edit</p></li></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ul.o_checklist -> ul ul (from indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom to edit</p></li></ul></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul><li><p>dom to edit</p></li></ul></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ul.o_checklist -> ul ul (across several indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ul></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ul></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            {
                name: "Click UL: ul ul.o_checklist -> ul ul (from second indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom not to edit</p></li><li><p>dom to edit</p></li><li><p>dom not to edit</p></li></ul></ul>',
                start: 'li:eq(2) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnUL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom not to edit</p></li></ul><ul><li><p>dom to edit</p></li></ul><ul class="o_checklist"><li><p>dom not to edit</p></li></ul></ul>',
                    start: 'p:eq(3):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(ulTests, function (test) {
            def = def.then(async function() {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
            });
        });
        return def.then(function() {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Ordered list', function (assert) {
    assert.expect(56);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $btnOL = wysiwyg.$('.note-para .note-icon-orderedlist');

        var olTests = [{
                name: "Click OL: p -> ol",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click OL: p -> ol (across paragraphs)",
                content: '<p>dom not to edit</p><p>dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol -> p",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li></ol>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click OL: p -> ol (across li's)",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol -> p (from second li) (2)",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                start: 'li:eq(0) p:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click OL: ol -> p (from second li)",
                content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                start: 'li:eq(0) p:contents()[0]->1',
                end: 'li:eq(0) p:contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click OL + Click OL: ul ul -> ul ol -> ul",
                content: '<p>a</p>' +
                    '<ul>' +
                    '<li><p>b</p></li>' +
                    '<ul>' +
                    '<li><p>c</p></li>' +
                    '<li><p>d</p></li>' +
                    '</ul>' +
                    '<li><p>e</p></li>' +
                    '</ul>',
                start: 'ul ul li:first:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>a</p>' +
                        '<ul>' +
                        '<li><p>b</p></li>' +
                        '<li><p>c</p></li>' +
                        '<ul>' +
                        '<li><p>d</p></li>' +
                        '</ul>' +
                        '<li><p>e</p></li>' +
                        '</ul>',
                    start: 'ul li:eq(1) p:contents()[0]->1',
                },
            },
            {
                name: "Click OL in empty table cell in div",
                content: '<div>' +
                    '<p>a</p>' +
                    '<table>' +
                    '<tbody>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '</tbody>' +
                    '</table>' +
                    '</div>',
                start: 'tr:eq(0) td:eq(1)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div>' +
                        '<p>a</p>' +
                        '<table>' +
                        '<tbody>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><ol><li><p><br></p></li></ol></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '</tbody>' +
                        '</table>' +
                        '</div>',
                    start: 'tr:eq(0) td:eq(1) br->0',
                },
            },
            {
                name: "Click OL in empty table cell in div (2)",
                content: '<div>' +
                    '<p>a</p>' +
                    '<table>' +
                    '<tbody>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '</tbody>' +
                    '</table>' +
                    '</div>',
                start: 'tr:eq(0) td:eq(1) br->0',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div>' +
                        '<p>a</p>' +
                        '<table>' +
                        '<tbody>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><ol><li><p><br></p></li></ol></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '</tbody>' +
                        '</table>' +
                        '</div>',
                    start: 'tr:eq(0) td:eq(1) br->0',
                },
            },
            {
                name: "Click OL in empty table cell in div (3)",
                content: '<div>' +
                    '<p>a</p>' +
                    '<table>' +
                    '<tbody>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '</tbody>' +
                    '</table>' +
                    '</div>',
                start: 'tr:eq(0) td:eq(1)->0',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div>' +
                        '<p>a</p>' +
                        '<table>' +
                        '<tbody>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><ol><li><p><br></p></li></ol></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '</tbody>' +
                        '</table>' +
                        '</div>',
                    start: 'tr:eq(0) td:eq(1) br->0',
                },
            },
            {
                name: "Click OL in table cell in div",
                content: '<div>' +
                    '<p>a</p>' +
                    '<table>' +
                    '<tbody>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td>aaa</td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '</tbody>' +
                    '</table>' +
                    '</div>',
                start: 'tr:eq(0) td:eq(1):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div>' +
                        '<p>a</p>' +
                        '<table>' +
                        '<tbody>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><ol><li><p>aaa</p></li></ol></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '</tbody>' +
                        '</table>' +
                        '</div>',
                    start: 'td li p:contents(0)->1',
                },
            },
            {
                name: "Click OL on image in table cell in div",
                content: '<div>' +
                    '<p>a</p>' +
                    '<table>' +
                    '<tbody>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><img data-src="/web_editor/static/src/img/transparent.png"></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '<tr>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '<td><br></td>' +
                    '</tr>' +
                    '</tbody>' +
                    '</table>' +
                    '</div>',
                start: 'img->0',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div>' +
                        '<p>a</p>' +
                        '<table>' +
                        '<tbody>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><ol><li><img data-src="/web_editor/static/src/img/transparent.png"></li></ol></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '<tr>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '<td><br></td>' +
                        '</tr>' +
                        '</tbody>' +
                        '</table>' +
                        '</div>',
                    start: 'td li->1',
                },
            },
            {
                name: "Click OL with selected LI in OL",
                content: '<p>x</p>' +
                    '<ol>' +
                    '<li><p>aaa</p></li>' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ol>' +
                    '<p>y</p>',
                start: 'p:eq(2):contents(0)->1',
                end: 'p:eq(3):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>x</p>' +
                        '<ol>' +
                        '<li><p>aaa</p></li>' +
                        '</ol>' +
                        '<p>bbb</p>' +
                        '<p>ccc</p>' +
                        '<ol>' +
                        '<li><p>ddd</p></li>' +
                        '</ol>' +
                        '<p>y</p>',
                    start: 'p:eq(2):contents(0)->1',
                    end: 'p:eq(3):contents(0)->1',
                },
            },
            {
                name: "Click OL with selected LI in UL",
                content: '<p>x</p>' +
                    '<ul>' +
                    '<li><p>aaa</p></li>' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                start: 'p:eq(2):contents(0)->1',
                end: 'p:eq(3):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul>' +
                        '<li><p>aaa</p></li>' +
                        '</ul>' +
                        '<ol>' +
                        '<li><p>bbb</p></li>' +
                        '<li><p>ccc</p></li>' +
                        '</ol>' +
                        '<ul>' +
                        '<li><p>ddd</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                    start: 'p:eq(2):contents(0)->1',
                    end: 'p:eq(3):contents(0)->1',
                },
            },
            {
                name: "Click OL after ENTER in p > b",
                content: "<p><b>dom to edit</b></p>",
                start: 'b:contents(0)->11',
                do: async function () {
                    weTestUtils.keydown(13, $editable); // ENTER
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                    weTestUtils.keydown('a', $editable); // ENTER
                },
                test: {
                    content: "<p><b>dom to edit</b></p><ol><li><p><b>a</b></p></li></ol>",
                    start: 'b:eq(1):contents(0)->1',
                },
            },
            {
                name: "Click OL in font in H1 (with link) in div",
                content: '<div><h1><font style="font-size: 62px;">table of contents <a href="p23">p23</a> (cfr: 34)</font></h1></div>',
                start: 'font:contents(0)->11',
                do: async function () {
                    await testUtils.dom.triggerEvents($btnOL, ['mousedown', 'click']);
                },
                test: {
                    content: '<div><ol><li><h1><font style="font-size: 62px;">table of contents <a href="p23">p23</a> (cfr: 34)</font></h1></li></ol></div>',
                    start: 'font:contents(0)->11',
                },
            },
            // Conversion from UL
            {
                name: "Click OL: ul -> ol",
                content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul -> ol (across li's)",
                content: '<p>dom not to edit</p><ul><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul -> ol (from second li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><li><p>dom to edit</p></li></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li></ul><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol ul -> ol ol (from indented li)",
                content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ul><li><p>dom to edit</p></li></ul></ol>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ol><li><p>dom to edit</p></li></ol></ol>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol ul -> ol ol (across several indented li)",
                content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ul><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ul></ol>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ol><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ol></ol>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol ul -> ol ol (from second indented li)",
                content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ul><li><p>dom not to edit</p></li><li><p>dom to edit</p></li><li><p>dom not to edit</p></li></ul></ol>',
                start: 'li:eq(2) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ul><li><p>dom not to edit</p></li></ul><ol><li><p>dom to edit</p></li></ol><ul><li><p>dom not to edit</p></li></ul></ol>',
                    start: 'p:eq(3):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            // Conversion from Checklist
            {
                name: "Click OL: ul.o_checklist -> ol",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul.o_checklist -> ol (across li's)",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>dom to edit</p></li><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul.o_checklist -> ol (from second li)",
                content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>xxx</p></li><li><p>dom to edit</p></li></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul class="o_checklist"><li><p>xxx</p></li></ul><ol><li><p>dom to edit</p></li></ol>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ol ul.o_checklist -> ol ol (from indented li)",
                content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom to edit</p></li></ul></ol>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(1) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ol><li><p>xxx</p></li><ol><li><p>dom to edit</p></li></ol></ol>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul ul.o_checklist -> ul ol (across several indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ul></ul>',
                start: 'li:eq(1) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ol><li><p>dom to edit 1</p></li><li><p>dom to edit 2</p></li></ol></ul>',
                    start: 'p:eq(2):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
            {
                name: "Click OL: ul ul.o_checklist -> ul ol (from second indented li)",
                content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom not to edit</p></li><li><p>dom to edit</p></li><li><p>dom not to edit</p></li></ul></ul>',
                start: 'li:eq(2) p:contents()[0]->1',
                end: 'li:eq(2) p:contents()[0]->5',
                do: function () {
                    $btnOL.mousedown().click();
                },
                test: {
                    content: '<p>dom not to edit</p><ul><li><p>xxx</p></li><ul class="o_checklist"><li><p>dom not to edit</p></li></ul><ol><li><p>dom to edit</p></li></ol><ul class="o_checklist"><li><p>dom not to edit</p></li></ul></ul>',
                    start: 'p:eq(3):contents()[0]->1',
                    end: 'p:eq(3):contents()[0]->5',
                },
            },
        ];


        var def = Promise.resolve();
        _.each(olTests, function (test) {
            def = def.then(async function() {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                $(range.sc).mousedown();
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                if (wysiwyg.getValue() === test.test.content) {
                    assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
                } else {
                    assert.notOk(true, testName + ' (Wrong DOM)');
                }
            });
        });

        return def.then(function(){
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Align', function (assert) {
    assert.expect(20);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $dropdownPara = wysiwyg.$('.note-para .dropdown-toggle');
        var $btnAlignLeft = wysiwyg.$('.note-align .note-icon-align-left');
        var $btnAlignCenter = wysiwyg.$('.note-align .note-icon-align-center');
        var $btnAlignRight = wysiwyg.$('.note-align .note-icon-align-right');
        var $btnAlignJustify = wysiwyg.$('.note-align .note-icon-align-justify');

        var alignTests = [
            /* ALIGN LEFT */
            {
                name: "Click ALIGN LEFT: p -> p align left (does nothing)",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignLeft, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p>dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click ALIGN LEFT: p (parent align right) -> p align left (does nothing)",
                content: '<div style="text-align: right;"><p>dom not to edit</p><p>dom to edit</p></div>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignLeft, ['mousedown', 'click']);
                },
                test: {
                    content: '<div style="text-align: right;"><p>dom not to edit</p><p style="text-align: left;">dom to edit</p></div>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click ALIGN LEFT: p (parent align left) -> p align left (does nothing)",
                content: '<div style="text-align: left;"><p>dom not to edit</p><p>dom to edit</p></div>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(1):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignLeft, ['mousedown', 'click']);
                },
                test: {
                    content: '<div style="text-align: left;"><p>dom not to edit</p><p>dom to edit</p></div>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(1):contents()[0]->5',
                },
            },
            {
                name: "Click ALIGN LEFT: p align justify & default -> p align right (across paragraphs)",
                content: '<p>dom not to edit</p><p style="text-align: justify;">dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignRight, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: right;">dom to edit</p><p style="text-align: right;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            /* ALIGN CENTER */
            {
                name: "Click ALIGN CENTER: p -> p align center",
                content: '<p>dom not to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignCenter, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: center;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click ALIGN CENTER: p align left & default -> p align center (across paragraphs)",
                content: '<p>dom not to edit</p><p style="text-align: left;">dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignCenter, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: center;">dom to edit</p><p style="text-align: center;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            /* ALIGN RIGHT */
            {
                name: "Click ALIGN RIGHT: p align center -> p align right",
                content: '<p>dom not to edit</p><p style="text-align: center;">dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignRight, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: right;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click ALIGN RIGHT: p align center & default -> p align right (across paragraphs)",
                content: '<p>dom not to edit</p><p style="text-align: center;">dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignRight, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: right;">dom to edit</p><p style="text-align: right;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
            /* ALIGN JUSTIFY */
            {
                name: "Click ALIGN JUSTIFY: p align right -> p align justify",
                content: '<p>dom not to edit</p><p style="text-align: right;">dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignJustify, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: justify;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click ALIGN JUSTIFY: p align right & default -> p align justify (across paragraphs)",
                content: '<p>dom not to edit</p><p style="text-align: right;">dom to edit</p><p>dom to edit</p>',
                start: 'p:eq(1):contents()[0]->1',
                end: 'p:eq(2):contents()[0]->5',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnAlignJustify, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom not to edit</p><p style="text-align: justify;">dom to edit</p><p style="text-align: justify;">dom to edit</p>',
                    start: 'p:eq(1):contents()[0]->1',
                    end: 'p:eq(2):contents()[0]->5',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(alignTests, function (test) {
            def = def.then(async function() {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
            });
        });
        return def.then(function() {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Indent/outdent', function (assert) {
    assert.expect(20);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $dropdownPara = wysiwyg.$('.note-para .dropdown-toggle');
        var $btnIndent = wysiwyg.$('.note-list .note-btn:eq(1)');
        var $btnOutdent = wysiwyg.$('.note-list .note-btn:first');

        var indentTests = [
            /* INDENT */
            {
                name: "Click INDENT: p -> indented p",
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnIndent, ['mousedown', 'click']);
                },
                test: {
                    content: '<p style="margin-left: 1.5em;">dom to edit</p>',
                    start: 'p:contents()[0]->1',
                },
            },
            {
                name: "Click INDENT: li -> indented li",
                content: '<ul><li><p>dom</p></li><li><p>to edit</p></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnIndent, ['mousedown', 'click']);
                },
                test: {
                    content: '<ul><li><p>dom</p></li><li class="o_indent"><ul><li><p>to edit</p></li></ul></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click INDENT: li -> indented li",
                content: '<p>aaa</p><p>bbb</p><p>ccc</p><p>ddd</p>',
                start: 'p:eq(1):contents()[0]->0',
                end: 'p:eq(3):contents()[0]->3',
                do: function () {
                    $dropdownPara.mousedown().click();
                    $btnIndent.mousedown().click();
                },
                test: {
                    content: '<p>aaa</p><p style="margin-left: 1.5em;">bbb</p><p style="margin-left: 1.5em;">ccc</p><p style="margin-left: 1.5em;">ddd</p>',
                    start: 'p:eq(1):contents()[0]->0',
                    end: 'p:eq(3):contents()[0]->3',
                },
            },
            /* OUTDENT */
            {
                name: "Click OUTDENT: indented p -> p",
                content: '<p style="margin-left: 1.5em;">dom to edit</p>',
                start: 'p:contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>dom to edit</p>',
                    start: 'p:contents()[0]->1',
                },
            },
            {
                name: "Click OUTDENT: indented li -> li",
                content: '<ul><li><p>dom</p></li><li><ul><li><p>to edit</p></li></ul></li></ul>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content: '<ul><li><p>dom</p></li><li><p>to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click OUTDENT: indented li -> li (2)",
                content: '<ul><li><p>dom</p></li><ul><li><p>to edit</p></li></ul></ul>',
                start: 'p:eq(1):contents()[0]->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content: '<ul><li><p>dom</p></li><li><p>to edit</p></li></ul>',
                    start: 'p:eq(1):contents()[0]->1',
                },
            },
            {
                name: "Click OUTDENT on LI in OL in OL",
                content: '<p>x</p>' +
                    '<ol>' +
                    '<li><p>aaa</p></li>' +
                    '<li><ol>' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ol></li>' +
                    '<li><p>eee</p></li>' +
                    '</ol>' +
                    '<p>y</p>',
                start: 'ol ol p:eq(1):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>x</p>' +
                        '<ol>' +
                        '<li><p>aaa</p></li>' +
                        '<li><ol>' +
                        '<li><p>bbb</p></li>' +
                        '</ol></li>' +
                        '<li><p>ccc</p></li>' +
                        '<li><ol>' +
                        '<li><p>ddd</p></li>' +
                        '</ol></li>' +
                        '<li><p>eee</p></li>' +
                        '</ol>' +
                        '<p>y</p>',
                    start: 'ol:first > li:eq(2) p:contents(0)->1',
                },
            },
            {
                name: "Click OUTDENT on LI in OL in OL (2)",
                content: '<p>x</p>' +
                    '<ol>' +
                    '<li><p>aaa</p></li>' +
                    '<ol>' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ol>' +
                    '<li><p>eee</p></li>' +
                    '</ol>' +
                    '<p>y</p>',
                start: 'ol ol p:eq(1):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content: '<p>x</p>' +
                        '<ol>' +
                        '<li><p>aaa</p></li>' +
                        '<ol>' +
                        '<li><p>bbb</p></li>' +
                        '</ol>' +
                        '<li><p>ccc</p></li>' +
                        '<ol>' +
                        '<li><p>ddd</p></li>' +
                        '</ol>' +
                        '<li><p>eee</p></li>' +
                        '</ol>' +
                        '<p>y</p>',
                    start: 'li:eq(2) p:contents(0)->1',
                },
            },
            {
                name: "Click OUTDENT on LI in OL",
                content:
                    '<ol>' +
                    '<li><p>aaa</p></li>' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '</ol>',
                start: 'p:eq(1):contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content:
                        '<ol>' +
                        '<li><p>aaa</p></li>' +
                        '</ol>' +
                        '<p>bbb</p>' +
                        '<ol>' +
                        '<li><p>ccc</p></li>' +
                        '</ol>',
                    start: 'p:eq(1):contents(0)->1',
                },
            },
            {
                name: "Click OUTDENT on P with indent in a LI (must outdent the p)",
                content:
                    '<ul>' +
                    '<li>' +
                    '<ul>' +
                    '<li>' +
                    '<p style="margin-left: 1.5em;">dom</p>' +
                    '</li>' +
                    '</ul>' +
                    '</li>' +
                    '</ul>',
                start: 'p:contents(0)->1',
                do: async function () {
                    await testUtils.dom.triggerEvents($dropdownPara, ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($btnOutdent, ['mousedown', 'click']);
                },
                test: {
                    content:
                        '<ul>' +
                        '<li>' +
                        '<ul>' +
                        '<li>' +
                        '<p>dom</p>' +
                        '</li>' +
                        '</ul>' +
                        '</li>' +
                        '</ul>',
                    start: 'p:contents(0)->1',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(indentTests, function (test) {
            def = def.then(async function() {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
                assert.deepEqual(Wysiwyg.getRange($editable[0]), weTestUtils.select(test.test.start, test.test.end, $editable), testName + carretTestSuffix);
            });
        });
        return def.then(function() {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('checklist', function (assert) {
    assert.expect(11);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            generateOptions: function (options) {
                options.toolbar[4][1] = ['ul', 'ol', 'checklist', 'paragraph'];
            },
            tooltip: false,
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $btnChecklist = wysiwyg.$('.note-para .fa-check-square');

        var checklistTests = [
            {
                name: "check checkbox in checklist with children",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<li>' +
                    '<ul class="o_checklist">' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ul>' +
                    '</li>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('li:first');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>aaa</p></li>' +
                        '<li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '</li>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "check checkbox in checklist with children (2)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<ul class="o_checklist">' +
                    '<li><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ul>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('li:first');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>aaa</p></li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "uncheck checkbox in checklist with children",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>aaa</p></li>' +
                    '<li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li class="o_checked"><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '</li>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('li:first');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<li>' +
                        '<ul class="o_checklist">' +
                        '<li><p>bbb</p></li>' +
                        '<li><p>ccc</p></li>' +
                        '<li><p>ddd</p></li>' +
                        '</ul>' +
                        '</li>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "uncheck checkbox in checklist with children (2)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>aaa</p></li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li class="o_checked"><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('li:first');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<ul class="o_checklist">' +
                        '<li><p>bbb</p></li>' +
                        '<li><p>ccc</p></li>' +
                        '<li><p>ddd</p></li>' +
                        '</ul>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "uncheck checkbox in checklist in checklist",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>aaa</p></li>' +
                    '<li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li class="o_checked"><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '</li>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '</li>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "uncheck checkbox in checklist in checklist (2)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>aaa</p></li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li class="o_checked"><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "check checkbox in checklist in checklist",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ul>' +
                    '</li>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li><p>ddd</p></li>' +
                        '</ul>' +
                        '</li>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "check checkbox in checklist in checklist (2)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li><p>ddd</p></li>' +
                    '</ul>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li><p>aaa</p></li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li><p>ddd</p></li>' +
                        '</ul>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "check checkbox in checklist in checklist (full)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '</li>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>aaa</p></li>' +
                        '<li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '</li>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "check checkbox in checklist in checklist (full) (2)",
                content: '<p>x</p>' +
                    '<ul class="o_checklist">' +
                    '<li><p>aaa</p></li>' +
                    '<ul class="o_checklist">' +
                    '<li class="o_checked"><p>bbb</p></li>' +
                    '<li><p>ccc</p></li>' +
                    '<li class="o_checked"><p>ddd</p></li>' +
                    '</ul>' +
                    '<li><p>eee</p></li>' +
                    '</ul>' +
                    '<p>y</p>',
                do: async function () {
                    var $li = $editable.find('ul ul li:eq(1)');
                    $li.trigger($.Event('mousedown', {
                        offsetX: -10,
                    }));
                },
                test: {
                    content: '<p>x</p>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>aaa</p></li>' +
                        '<ul class="o_checklist">' +
                        '<li class="o_checked"><p>bbb</p></li>' +
                        '<li class="o_checked"><p>ccc</p></li>' +
                        '<li class="o_checked"><p>ddd</p></li>' +
                        '</ul>' +
                        '<li><p>eee</p></li>' +
                        '</ul>' +
                        '<p>y</p>',
                },
            },
            {
                name: "convert 2 ul li ul li into two ul li ul.o_checklist li",
                content: '<ul>' +
                            '<li>' +
                                '<p>1</p>' +
                            '</li>' +
                            '<li class="o_indent">' +
                                '<ul>' +
                                    '<li>' +
                                        '<p>2</p>' +
                                    '</li>' +
                                    '<li>' +
                                        '<p>3</p>' +
                                    '</li>' +
                                    '<li>' +
                                        '<p>4</p>' +
                                    '</li>' +
                                '</ul>' +
                            '</li>' +
                            '<li>' +
                                '<p>5</p>' +
                            '</li>' +
                        '</ul>',
                start: 'p:eq(2):contents()[0]->0',
                end: 'p:eq(3):contents()[0]->1',
                do: function () {
                    $btnChecklist.mousedown().click();
                },
                test: {
                    content: '<ul>' +
                                '<li>' +
                                    '<p>1</p>' +
                                '</li>' +
                                '<li class="o_indent">' +
                                    '<ul>' +
                                        '<li>' +
                                            '<p>2</p>' +
                                        '</li>' +
                                    '</ul>' +
                                    '<ul class="o_checklist">' +
                                        '<li>' +
                                            '<p>3</p>' +
                                        '</li>' +
                                        '<li>' +
                                            '<p>4</p>' +
                                        '</li>' +
                                    '</ul>' +
                                '</li>' +
                                '<li>' +
                                    '<p>5</p>' +
                                '</li>' +
                            '</ul>',
                },
            },
        ];

        var def = Promise.resolve();

        _.each(checklistTests, function (test) {
            def = def.then(async function(){
                testName = test.name;
                wysiwyg.setValue(test.content);
                if (test.start) {
                    var range = weTestUtils.select(test.start, test.end || test.start, $editable);
                    $(range.sc).mousedown();
                    Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                }
                await test.do();
                assert.deepEqual(wysiwyg.getValue(), test.test.content, testName);
            });
        });

        return def.then(function() {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Link', function (assert) {
    assert.expect(19);

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(async function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var $btnLink = wysiwyg.$('.note-insert .note-icon-link');

        var _clickLink = async function (callbackInit, test) {
            await testUtils.dom.triggerEvents($btnLink, ['mousedown', 'click']);
            await callbackInit();
            await testUtils.dom.triggerEvents($('.modal-dialog:visible .btn-primary:contains("Save")'), ['mousedown', 'click']);

            if (test.check) {
                await test.check();
            }
            if (test.content) {
                assert.deepEqual(wysiwyg.getValue(), test.content, testName);
            }
            if (test.start) {
                var range = weTestUtils.select(test.start, test.end, $editable);
                assert.deepEqual(Wysiwyg.getRange($editable[0]), range, testName + carretTestSuffix);
            }
        };

        var linkTests = [{
                name: "Click LINK: p -> a in p (w/ URL)",
                async: true,
                content: '<p>dom to edit</p>',
                start: "p:contents()[0]->1",
                end: "p:contents()[0]->5",
                do: async function () {
                    assert.strictEqual($('.modal-dialog:visible #o_link_dialog_label_input').val(), 'om t', testName + ' (label)');
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'),'#');
                },
                test: {
                    content: '<p>d<a href="#">om t</a>o edit</p>',
                    start: 'a:contents()[0]->0',
                    end: 'a:contents()[0]->4',
                },
            },
            {
                name: "Click LINK: p -> a in p (w/ URL) (no selection)",
                async: true,
                content: '<p>do edit</p>',
                start: 'p:contents()[0]->1',
                do: async function () {
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_label_input'),'om t');
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'),'#');
                },
                test: {
                    content: '<p>d<a href="#">om t</a>o edit</p>',
                    start: 'p->2', // link not selected, the user can continue to write
                    end: 'p->2',
                },
            },
            {
                name: "Click LINK: a.btn in div -> a.btn.btn-outline-alpha in div (edit) (no selection)",
                content: '<div><a href="#" class="btn btn-outline-alpha btn-lg">dom to edit</a></div>',
                start: 'a:contents()[0]->5',
                do: async function () {
                    assert.strictEqual($('.modal-dialog:visible #o_link_dialog_label_input').val(), 'dom to edit', testName + ' (label)');
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'),'#newlink');
                },
                test: {
                    content: '<div><a href="#newlink" class="btn btn-outline-alpha btn-lg">dom to edit</a></div>',
                    start: 'a->0',
                    end: 'a->1',
                },
            },
            {
                name: "Click LINK: p -> a in p (w/ Email)",
                async: true,
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->5',
                do: async function () {
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'),'john.coltrane@example.com');
                },
                test: {
                    content: '<p>d<a href="mailto:john.coltrane@example.com">om t</a>o edit</p>',
                    start: 'a:contents()[0]->0',
                    end: 'a:contents()[0]->4',
                },
            },
            {
                name: "Click LINK: p -> a in p (w/ URL & Size Large)",
                async: true,
                content: '<p>dom to edit</p>',
                start: 'p:contents()[0]->1',
                end: 'p:contents()[0]->5',
                do: async function () {
                    await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'),'#');
                    await testUtils.fields.editInput($('.modal-dialog:visible [name="link_style_size"]'),"lg");
                },
                test: {
                    content: '<p>d<a href="#" class="btn-lg">om t</a>o edit</p>',
                    start: 'a:contents()[0]->0',
                    end: 'a:contents()[0]->4',
                },
            },
            {
                name: "Click LINK: a in p -> a.btn-outline-alpha in p with alpha color and target=\"_blank\"",
                async: true,
                content: '<p><a href="#">dom to edit</a></p>',
                start: 'a:contents()[0]->1',
                do: async function () {
                    await testUtils.fields.editInput( $('.modal-dialog:visible #o_link_dialog_url_input'), '#');
                    await testUtils.fields.editInput($('.modal-dialog:visible [name="link_style_shape"]'), "outline");
                    await testUtils.dom.triggerEvents($('.modal-dialog:visible .o_link_dialog_color .o_link_dialog_color_item.btn-alpha'), ['mousedown', 'click']);
                    await testUtils.dom.triggerEvents($('.modal-dialog:visible .o_switch [name="is_new_window"]'), ['mousedown', 'click']);
                },
                test: {
                    content: '<p><a href="#" target="_blank" class="btn btn-outline-alpha">dom to edit</a></p>',
                    start: 'a->0',
                    end: 'a->1',
                },
            },
            // POPOVER
            {
                name: "Click LINK in popover after adding link in p",
                async: true,
                content: '<p>dom to edit</p>',
                start: "p:contents()[0]->1",
                end: "p:contents()[0]->5",
                do: async function () {
                    $('.modal-dialog:visible #o_link_dialog_url_input').val('/link');
                },
                test: {
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-link-popover .note-btn .note-icon-link'), ['mousedown', 'click']);

                        assert.strictEqual($('.modal-dialog:visible #o_link_dialog_label_input').val(), 'om t', testName + ' (label)');
                        assert.strictEqual($('.modal-dialog:visible #o_link_dialog_url_input').val(), '/link', testName + ' (url)');
                        await testUtils.fields.editInput($('.modal-dialog:visible #o_link_dialog_url_input'), '/newlink');
                        await testUtils.dom.triggerEvents($('.modal-dialog:visible .modal-footer .btn.btn-primary:contains("Save")'), ['mousedown', 'click']);
                        assert.deepEqual(wysiwyg.getValue(), '<p>d<a href="/newlink">om t</a>o edit</p>', testName);
                    },
                },
            },
            {
                name: "Click UNLINK in popover after adding link in p",
                async: true,
                content: '<p>dom to edit</p>',
                start: "p:contents()[0]->1",
                end: "p:contents()[0]->5",
                do: async function () {
                    $('.modal-dialog:visible #o_link_dialog_url_input').val('/link');
                },
                test: {
                    content: '<p>dom to edit</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-link-popover .note-btn .note-icon-chain-broken'), ['mousedown', 'click']);

                        var range = weTestUtils.select('p:contents()[0]->1', 'p:contents()[0]->5', $editable);
                        assert.deepEqual(Wysiwyg.getRange($editable[0]), range, testName + carretTestSuffix);
                    },
                },
            },
        ];

        var def = Promise.resolve();
        _.each(linkTests, function (test) {
            def = def.then(async function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                await _clickLink(test.do, test.test);
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Table', function (assert) {
    assert.expect(13);

    async function createTable(wysiwyg) {
        await testUtils.dom.triggerEvents(wysiwyg.$('.note-table button:first'), ['mousedown', 'click']);

        var $grid = wysiwyg.$('.note-table .note-dimension-picker-mousecatcher');
        var pos = $grid.offset();
        $grid.trigger($.Event('mousemove', {
            pageX: pos.left + 40,
            pageY: pos.top + 40,
        }));
        await testUtils.dom.triggerEvents($grid, ['mousedown', 'click']);
    }

    return weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            tooltip: false,
        },
    }).then(async function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        // create a table in an empty dom

        wysiwyg.setValue('<p><br></p>');
        var range = weTestUtils.select('p->1', 'p->1', $editable);
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        await createTable(wysiwyg);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p><br></p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p><br></p>',
            "should create a table in an empty dom (p > br)");

        // create a table at start of p with content

        wysiwyg.setValue('<p>dom to edit</p>');
        range = weTestUtils.select('p:contents()[0]->0', 'p:contents()[0]->0', $editable);
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        await createTable(wysiwyg);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p><br></p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>dom to edit</p>',
            "should create a table at start of single p with content");

        // create a table at end of p with content

        wysiwyg.setValue('<p>dom to edit</p>');
        range = weTestUtils.select('p:contents()[0]->11', 'p:contents()[0]->11', $editable);
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        await createTable(wysiwyg);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom to edit</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p><br></p>',
            "should create a table at end of single p with content");

        // create a table within p

        wysiwyg.setValue('<p>dom to edit</p>');
        range = weTestUtils.select('p:contents()[0]->5', 'p:contents()[0]->5', $editable);
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        await createTable(wysiwyg);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should create a table");

        // remove a table

        range = weTestUtils.select('td:first->0', 'td:first->0', $editable);
        $(range.sc).mousedown();
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        var $trash = $('.note-table-popover:visible button:has(.note-icon-trash)');

        await testUtils.dom.triggerEvents($trash, ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom to edit</p>',
            "should remove the table");

        // re create a table and table in table

        await createTable(wysiwyg);
        await createTable(wysiwyg);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should create a table inside the table");

        // remove inner table

        range = weTestUtils.select('td td:eq(1)->0', 'td td:eq(1)->0', $editable);
        $(range.sc).mousedown();
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);

        $trash = $('.note-table-popover:visible button:has(.note-icon-trash)');
        await testUtils.dom.triggerEvents($trash, ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should remove the inner table");

        // use popover to change row and line

        wysiwyg.setValue('<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p>0-0</p></td><td><p>0-1</p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p>1-0</p></td><td><p>1-1</p></td><td><p>1-2</p></td></tr>' +
            '<tr><td><p>2-0</p></td><td><p>2-1</p></td><td><p>2-2</p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>');

        // remove a row

        range = weTestUtils.select('td:eq(1)->0', 'td:eq(1)->0', $editable);
        $(range.sc).mousedown();
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-col-remove)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p>0-0</p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p>1-0</p></td><td><p>1-2</p></td></tr>' +
            '<tr><td><p>2-0</p></td><td><p>2-2</p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should remove a row");

        // remove a line

        range = weTestUtils.select('tr:eq(1) td:eq(1)->0', 'tr:eq(1) td:eq(1)->0', $editable);
        $(range.sc).mousedown();
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-row-remove)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p>0-0</p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p>2-0</p></td><td><p>2-2</p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should remove a line");

        // add a row after

        range = weTestUtils.select('tr:eq(1) td:first->0', 'tr:eq(1) td:first->0', $editable);
        $(range.sc).mousedown();
        Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-col-after)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p>0-0</p></td><td><p><br></p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p>2-0</p></td><td><p><br></p></td><td><p>2-2</p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should add a row after");

        // add a row before

        $(range.sc).mousedown();
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-col-before)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p>0-0</p></td><td><p><br></p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p><br></p></td><td><p>2-0</p></td><td><p><br></p></td><td><p>2-2</p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should add a row before");

        // add a line after

        $(range.sc).mousedown();
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-row-below)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p>0-0</p></td><td><p><br></p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p><br></p></td><td><p>2-0</p></td><td><p><br></p></td><td><p>2-2</p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should add a line after");

        // add a line before

        $(range.sc).mousedown();
        await testUtils.dom.triggerEvents($('.note-table-popover:visible button:has(.note-icon-row-above)'), ['mousedown', 'click']);

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>dom t</p>' +
            '<table class=\"table table-bordered\"><tbody>' +
            '<tr><td><p><br></p></td><td><p>0-0</p></td><td><p><br></p></td><td><p>0-2</p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '<tr><td><p><br></p></td><td><p>2-0</p></td><td><p><br></p></td><td><p>2-2</p></td></tr>' +
            '<tr><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td><td><p><br></p></td></tr>' +
            '</tbody></table>' +
            '<p>o edit</p>',
            "should add a line before");

        wysiwyg.destroy();
    });
});

QUnit.test('CodeView', async function (assert) {
    assert.expect(8);

    var wysiwyg = await weTestUtils.createWysiwyg({
        debug: false,
        wysiwygOptions: {
            codeview: true,
            tooltip: false,
        },
    });
        wysiwyg.setValue('<p>dom to edit <img src="/web_editor/static/src/img/transparent.png"></p>');

        var $buttonCodeView = wysiwyg.$('button:has(.note-icon-code)');

        // hide popover in CodeView mode and no range error when edit the content
        var $editable = wysiwyg.getEditable();
        await testUtils.dom.triggerEvents($editable.find('img'), ['mousedown', 'click']);
        assert.strictEqual($('.note-popover.note-image-popover:visible').length, 1, "should display the image popover");
        await testUtils.dom.triggerEvents($buttonCodeView, ['mousedown', 'click']);
        assert.strictEqual($('textarea.note-codable:visible').length, 1, "should show the CodeView textarea");
        assert.strictEqual($editable.is(':visible'), false, "should hide the editable area");
        assert.strictEqual($('.note-popover:visible').length, 0, "should hide all popovers");
        assert.strictEqual($('.note-toolbar button:not(.disabled)').length, 1, "should disabled all buttons expect the codeview button");
        wysiwyg.$('textarea.note-codable').val('<p>dom to edit a <img src="/web_editor/static/src/img/transparent.png"></p>');
        await testUtils.dom.triggerEvents($buttonCodeView, ['mousedown', 'click']);
        assert.strictEqual($('textarea.note-codable:visible').length, 0, "should hide the CodeView textarea");
        assert.strictEqual($editable.is(':visible'), true, "should show the editable area");
        assert.strictEqual($editable[0].style.height, '', "should reset the height (not auto or sizing)");
        // end

        wysiwyg.destroy();
});

});

var imgWidth = 10;
var imgHeight = 10;

var altDialogOpened;
var altDialogSaved;
var cropDialogOpened;
QUnit.module('Media', {
    beforeEach: function () {
        $('body').on('submit.WysiwygTests', function (ev) {
            ev.preventDefault();
            var $from = $(ev.target);
            var iframe = $from.find('iframe[name="' + $from.attr('target') + '"]')[0];
            if (iframe) {
                iframe.contentWindow.attachments = [{
                    id: 1,
                    public: true,
                    name: 'image',
                    datas_fname: 'image.png',
                    mimetype: 'image/png',
                    checksum: false,
                    url: '/web_editor/static/src/img/transparent.png',
                    type: 'url',
                    res_id: 0,
                    res_model: false,
                    access_token: false
                }];
                $(iframe).trigger('load');
            }
        });

        this.data = {
            debug: false,
            wysiwygOptions: {
                tooltip: false,
            },
            mockRPC: function (route, args) {
                if (args.model === 'ir.attachment' || !args.length) {
                    if (!args.length && route.indexOf('data:image/png;base64') === 0 ||
                        args.method === "search_read" &&
                        args.kwargs.domain[7][2].join(',') === "image/gif,image/jpe,image/jpeg,image/jpg,image/gif,image/png") {
                        return Promise.resolve(this.data.records || []);
                    }
                }
                if (route.indexOf('youtube') !== -1) {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        };

        testUtils.mock.patch(AltDialog, {
            init: function () {
                this._super.apply(this, arguments);
                altDialogOpened = this._opened;
            },
            save: function () {
                altDialogSaved = this._super.apply(this, arguments);
                return altDialogSaved;
            },
        });

        testUtils.mock.patch(CropDialog, {
            init: function () {
                var self = this;
                this._super.apply(this, arguments);
                cropDialogOpened = new Promise (function (resolve) {
                    self.opened(function () {
                        var cropper = self.$cropperImage.data('cropper');
                        cropper.clone();
                        $.extend(cropper.image, {
                            naturalWidth: imgWidth,
                            naturalHeight: imgHeight,
                            aspectRatio: imgWidth / imgHeight,
                        });
                        cropper.loaded = true;
                        cropper.build();
                        cropper.render();
                        resolve();
                    });
                });
            },
        });
    },
    afterEach: function () {
        testUtils.mock.unpatch(AltDialog);
        testUtils.mock.unpatch(CropDialog);
        $('body').off('submit.WysiwygTests');
    },
}, function () {


var _clickMedia = async function (wysiwyg, assert, callbackInit, test) {
    await testUtils.dom.triggerEvents(wysiwyg.$('.note-insert .fa-file-image-o'), ['mousedown', 'click']);
    await callbackInit();

    if (test.check) {
        await test.check();
    }
    if (test.content) {
        assert.deepEqual(wysiwyg.getValue(), test.content, testName);
    }
    if (test.start) {
        var range = weTestUtils.select(test.start, test.end, $editable);
        assert.deepEqual(Wysiwyg.getRange($editable[0]), range, testName + carretTestSuffix);
    }
};

var _uploadAndInsertImg = async function (url) {
    $('.modal-dialog input[name="url"]:first').val(url).trigger('input');
    await testUtils.nextTick();
    await testUtils.dom.triggerEvents($('.modal-dialog .o_upload_media_url_button:first'), ['mousedown', 'click']);
};
var _insertVideo = async function (wysiwyg, assert, url, checkOptions) {
    await testUtils.dom.triggerEvents($('.modal-dialog .nav-link:contains("Video")'), ['mousedown', 'click']);
    $('.modal-dialog #o_video_text').val(url).trigger('change');
    if (checkOptions) {
        assert.strictEqual($('.modal-dialog .o_yt_option').parent().css('display'), 'block', testName + ' (options)');
    }
    await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:visible'), ['mousedown', 'click']);
};
var _insertPictogram = async function (className) {
    await testUtils.dom.triggerEvents($('.modal-dialog .nav-link:contains("Pictogram")'), ['mousedown', 'click']);
    await testUtils.dom.triggerEvents($('.modal-dialog .font-icons-icons .font-icons-icon.fa.' + className), ['mousedown', 'click']);
    await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:visible'), ['mousedown', 'click']);
};
var _valueToRatio = function (value) {
    return value < 0 ? 1 / (1 - value) : 1 + value;
};


QUnit.test('Image', function (assert) {
    assert.expect(22);

    return weTestUtils.createWysiwyg(this.data).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var mediaTests = [{
                name: "Click ADD AN IMAGE URL in empty p: p -> img in p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png">\u200B</p>',
                    check: async function () {
                        assert.strictEqual($('.note-image-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            {
                name: "add an image in a table",
                async: true,
                content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                    '<table class="table table-bordered">' +
                    '    <tbody>' +
                    '        <tr>' +
                    '            <td>' +
                    '                aaa' +
                    '            </td>' +
                    '            <td>' +
                    '                bbb' +
                    '            </td>' +
                    '            <td>' +
                    '                ccc' +
                    '            </td>' +
                    '        </tr>' +
                    '    </tbody>' +
                    '</table>' +
                    '</div></div></div></section>',
                start: "td:eq(1):contents()[0]->18",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                        '<table class="table table-bordered">' +
                        '    <tbody>' +
                        '        <tr>' +
                        '            <td>' +
                        '                aaa' +
                        '            </td>' +
                        '            <td>' +
                        '                bb<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png">b' +
                        '            </td>' +
                        '            <td>' +
                        '                ccc' +
                        '            </td>' +
                        '        </tr>' +
                        '    </tbody>' +
                        '</table>' +
                        '</div></div></div></section>',
                    check: async function () {
                        assert.strictEqual($('.note-image-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            {
                name: "add an image in an empty table",
                async: true,
                content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                    '<table class="table table-bordered">' +
                    '    <tbody>' +
                    '        <tr>' +
                    '            <td>' +
                    '                <br>' +
                    '            </td>' +
                    '            <td>' +
                    '                <br>' +
                    '            </td>' +
                    '            <td>' +
                    '                <br>' +
                    '            </td>' +
                    '        </tr>' +
                    '    </tbody>' +
                    '</table>' +
                    '</div></div></div></section>',
                start: "br:eq(1)->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<section><div class="container"><div class="row"><div class="col-lg-6">' +
                        '<table class="table table-bordered">' +
                        '    <tbody>' +
                        '        <tr>' +
                        '            <td>' +
                        '                <br>' +
                        '            </td>' +
                        '            <td>' +
                        '                <img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png"><br>' +
                        '            </td>' +
                        '            <td>' +
                        '                <br>' +
                        '            </td>' +
                        '        </tr>' +
                        '    </tbody>' +
                        '</table>' +
                        '</div></div></div></section>',
                    check: async function () {
                        assert.strictEqual($('.note-image-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            /* IMAGE POPOVER */
            {
                name: "Click PADDING XL in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image padding-xl" data-src="/web_editor/static/src/img/transparent.png">\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-padding .dropdown-toggle'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-padding .dropdown-item:contains("Xl")'), ['mousedown', 'click']);
                    },
                },
            },
            {
                name: "Click IMAGE SIZE 25% in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png" style="width: 25%;">\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-imagesize .note-btn:contains(25%)'), ['mousedown', 'click']);
                    },
                },
            },
            {
                name: "Click FLOAT RIGHT in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image pull-right" data-src="/web_editor/static/src/img/transparent.png">\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-float .note-icon-align-right'), ['mousedown', 'click']);
                    },
                },
            },
            {
                name: "Click FLOAT CENTER then FLOAT LEFT in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image pull-left" data-src="/web_editor/static/src/img/transparent.png">\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-float .note-icon-align-center'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-float .note-icon-align-left'), ['mousedown', 'click']);
                    },
                },
            },
            {
                name: "Click SHAPE ROUNDED in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p>\u200B<img class="img-fluid o_we_custom_image rounded" data-src="/web_editor/static/src/img/transparent.png">\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-imageShape .note-btn:has(.fa-square)'), ['mousedown', 'click']);
                    },
                },
            },
            // Remove picture
            {
                name: "Click REMOVE in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    content: '<p><br></p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn .note-icon-trash'), ['mousedown', 'click']);
                    },
                },
            },
            // Describe picture
            {
                name: "Click DESCRIPTION in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    check: async function () {
                        await altDialogOpened;
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn:contains("Description")'), ['mousedown', 'click']);
                        $('.modal-dialog input#alt').val('Description');
                        await testUtils.nextTick();
                        $('.modal-dialog input#title').val('Title');
                        await testUtils.nextTick();
                        await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:contains("Save")'), ['mousedown', 'click']);
                        await altDialogSaved;
                        var value = $(wysiwyg.getValue());
                        // We can't simply compare the string result of getValue
                        // here, as the img tag has multiple attributes and the
                        // output order of the attributes is non-deterministic !
                        assert.strictEqual(value.prop('tagName'), 'P', "should be a p");
                        var contents = value.contents();
                        assert.strictEqual(contents.length, 3, "should contain a text node, then an img, then another text node");
                        var firstText = contents.eq(0);
                        assert.notOk(firstText.prop('tagName'), 'should not have a tag name since it is a pure text node');
                        assert.strictEqual(firstText.text(), "\u200b");
                        var img = contents.eq(1);
                        assert.strictEqual(img.prop('tagName'), "IMG", "second content should be an img");
                        assert.strictEqual(img.prop('className'), "img-fluid o_we_custom_image", "img should have correct class");
                        assert.strictEqual(img.data('src'), "/web_editor/static/src/img/transparent.png", "img should have correct data-src");
                        assert.strictEqual(img.attr('alt'), "Description", "img should have correct alt");
                        // FIXME The following assert fails about once every 100-120 builds.
                        // Given that the code is currently being refactored and given
                        // the fact that this assert only tests the title attribute, commenting
                        // the assert is the easiest "fix"
                        // assert.strictEqual(img.attr('title'), "Title", "img should have correct title");
                        var secondText = contents.eq(2);
                        assert.notOk(secondText.prop('tagName'), 'should not have a tag name since it is a pure text node');
                        assert.strictEqual(secondText.text(), "\u200b");
                    },
                },
            },
        ];

        var def = Promise.resolve();
        _.each(mediaTests, function (test) {
            def = def.then(function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                return _clickMedia(wysiwyg, assert, test.do, test.test);
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Image crop', function (assert) {
    assert.expect(5);

    return weTestUtils.createWysiwyg(this.data).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var mediaTests = [{
                name: "Click CROP 16:9 + ZOOM IN in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    check: async function () {
                        var zoomRatio;
                        var $img = $editable.find('img');
                        $img.attr('src', $img.data('src'));
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn:has(.fa-crop)'), ['mousedown', 'click']);
                        await cropDialogOpened;
                        await testUtils.dom.triggerEvents($('.o_crop_image_dialog .o_crop_options .btn:contains("16:9")'), ['mousedown', 'click']);
                        var $zoomBtn = $('.o_crop_image_dialog .o_crop_options .btn:has(.fa-search-plus)');
                        zoomRatio = _valueToRatio(Number($zoomBtn.data('value')));
                        await testUtils.dom.triggerEvents($zoomBtn, ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:contains("Save")'), ['mousedown', 'click']);

                        var $img = $(wysiwyg.getValue()).find('img.o_cropped_img_to_save');
                        assert.strictEqual($img.data('aspect-ratio'), '16/9', testName + " (aspect-ratio)");
                        assert.strictEqual($img.data('width'), imgWidth / zoomRatio, testName + " (zoom)");
                    },
                },
            },
            {
                name: "Click CROP ROTATE LEFT + FLIP HORIZONTAL in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    check: async function () {
                        var $img = $editable.find('img');
                        $img.attr('src', $img.data('src'));
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn:has(.fa-crop)'), ['mousedown', 'click']);
                        await cropDialogOpened;
                        await testUtils.dom.triggerEvents($('.o_crop_image_dialog .o_crop_options .btn:contains("16:9")'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.o_crop_image_dialog .o_crop_options .btn:has(.fa-rotate-left)'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.o_crop_image_dialog .o_crop_options .btn:has(.fa-arrows-h)'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:contains("Save")'), ['mousedown', 'click']);

                        var $img = $(wysiwyg.getValue()).find('img.o_cropped_img_to_save');
                        assert.strictEqual($img.data('rotate'), -45, testName + " (rotate)");
                        assert.strictEqual($img.data('scale-x'), -1, testName + " (flip)");
                    },
                },
            },
            {
                name: "Click CROP FREE in popover after adding image in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _uploadAndInsertImg('https://www.odoo.com/logo.png');
                },
                test: {
                    check: async function () {
                        var cropFactor = 10;
                        var $img = $editable.find('img');
                        $img.attr('src', $img.data('src'));
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn:has(.fa-crop)'), ['mousedown', 'click']);
                        await cropDialogOpened;
                        var $cropperPoints = $('.modal-dialog .cropper-crop-box .cropper-point');
                        var $pointW = $cropperPoints.filter('.point-w');
                        var pos1 = $pointW.offset();
                        var cropperWidth = $cropperPoints.filter('.point-e').offset().left - pos1.left;
                        $pointW.trigger($.Event("pointerdown", {
                            pageX: pos1.left,
                            pageY: pos1.top,
                        }));
                        $pointW.trigger($.Event("pointermove", {
                            pageX: pos1.left + (cropperWidth / cropFactor),
                            pageY: pos1.top,
                        }));
                        $pointW.trigger('pointerup');
                        await testUtils.dom.triggerEvents($('.modal-dialog .modal-footer .btn.btn-primary:contains("Save")'), ['mousedown', 'click']);

                        var $img = $(wysiwyg.getValue()).find('img.o_cropped_img_to_save');
                        assert.strictEqual(Math.round($img.data('width')), Math.round(imgWidth - (imgWidth / cropFactor)), testName + " (rotate)");
                    },
                },
            },
        ];

        var def = Promise.resolve();
        _.each(mediaTests, function (test) {
            def = def.then(function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                return _clickMedia(wysiwyg, assert, test.do, test.test);
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Pictogram (fontawesome)', function (assert) {
    assert.expect(8);

    return weTestUtils.createWysiwyg(this.data).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var mediaTests = [{
                name: "Add PICTOGRAM in empty p: p -> span.fa in p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    content: '<p>\u200B<span class="fa fa-glass"></span>\u200B</p>',
                    check: async function () {
                        assert.strictEqual($('.note-icon-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            // Remove font
            {
                name: "Click REMOVE in popover after adding font in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    content: '<p><br></p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn .note-icon-trash'), ['mousedown', 'click']);
                    },
                },
            },
            // Icon size
            {
                name: "Click ICON SIZE then 5X in popover after adding pictogram in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    content: '<p>\u200B<span class="fa fa-glass fa-5x"></span>\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-icon-popover .note-faSize .dropdown-toggle'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.note-icon-popover .note-faSize .dropdown-item:contains("5x")'), ['mousedown', 'click']);
                        assert.ok($('.note-icon-popover .note-faSize .dropdown-item:contains("5x")').hasClass('active'), testName + ' (popover)');
                    },
                },
            },
            // Spin
            {
                name: "Click SPIN in popover after adding pictogram in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    content: '<p>\u200B<span class="fa fa-glass fa-spin"></span>\u200B</p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-icon-popover .note-faSpin .note-btn'), ['mousedown', 'click']);
                    },
                },
            },
            // Replace pictogram
            {
                name: "Add PICTOGRAM in empty p then replace it",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    check: async function () {
                        return _clickMedia(wysiwyg, assert, async function () {
                            await _insertPictogram('fa-heart');
                        }, {
                                content: '<p>\u200B<span class="fa fa-heart"></span>\u200B</p>',
                            });
                    },
                },
            },
            {
                name: "Replace PICTOGRAM",
                async: true,
                content: '<div class="row">\n' +
                    '   <div class="col-lg-12">\n' +
                    '       <i class="fa fa-heart rounded-circle"></i>\n' +
                    '       <div>Other content</div>\n' +
                    '   </div>\n' +
                    '</div>',
                start: "i->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    content: '<div class="row">\n' +
                        '   <div class="col-lg-12">\n' +
                        '       <i class="rounded-circle fa fa-glass"></i>\n' +
                        '       <div>Other content</div>\n' +
                        '   </div>\n' +
                        '</div>',
                },
            },
        ];

        var def = Promise.resolve();
        _.each(mediaTests, function (test) {
            def = def.then(async function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                await testUtils.dom.triggerEvents($(range.sc), ['mousedown', 'click']);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                return _clickMedia(wysiwyg, assert, test.do, test.test);
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});

QUnit.test('Video', function (assert) {
    assert.expect(10);

    return weTestUtils.createWysiwyg(this.data).then(function (wysiwyg) {
        var $editable = wysiwyg.$('.note-editable');

        var mediaTests = [{
                name: "Add VIDEO (youtube) in empty p: p -> div.media_iframe_video after p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertVideo(wysiwyg, assert, 'https://www.youtube.com/watch?v=xxxxxxxxxxx', true);
                },
                test: {
                    content: '<p><br></p><div class="media_iframe_video" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div><p><br></p>',
                    check: async function () {
                        assert.strictEqual($('.note-video-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            {
                name: "Add VIDEO (youtube) in p in breakable in unbreakable in breakable: p -> div.media_iframe_video after p",
                async: true,
                content: '<breakable><unbreakable><breakable><p>tata yoyo</p></breakable></unbreakable></breakable>',
                start: "p:contents()[0]->4",
                do: async function () {
                    await _insertVideo(wysiwyg, assert, 'https://www.youtube.com/watch?v=xxxxxxxxxxx');
                },
                test: {
                    content: '<breakable><unbreakable><breakable><p>tata</p></breakable>' +
                        '<div class="media_iframe_video" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div>' +
                        '<breakable><p> yoyo</p></breakable></unbreakable></breakable>',
                    check: async function () {
                        assert.strictEqual($('.note-video-popover').css('display'), 'block', testName + ' (popover)');
                    },
                },
            },
            // Remove video
            {
                name: "Click REMOVE in popover after adding video in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertVideo(wysiwyg, assert, 'https://www.youtube.com/watch?v=xxxxxxxxxxx');
                },
                test: {
                    content: '<p><br></p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-btn .note-icon-trash'), ['mousedown', 'click']);
                    },
                },
            },
            /* VIDEO POPOVER */
            // Multiple clicks
            {
                name: "Click FLOAT CENTER then FLOAT LEFT in popover after adding youtube video in empty p",
                async: true,
                content: '<p><br></p>',
                start: "p->0",
                do: async function () {
                    await _insertVideo(wysiwyg, assert, 'https://www.youtube.com/watch?v=xxxxxxxxxxx');
                },
                test: {
                    content: '<p><br></p><div class="media_iframe_video pull-left" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div><p><br></p>',
                    check: async function () {
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-float .note-icon-align-center'), ['mousedown', 'click']);
                        await testUtils.dom.triggerEvents($('.note-image-popover .note-float .note-icon-align-left'), ['mousedown', 'click']);
                    },
                },
            },
            // Replace picture
            {
                name: "replace picture with video",
                async: true,
                content: '<p><img src="https://www.odoo.com/logo.png"></p>',
                start: "img->0",
                do: async function () {
                    await _insertVideo(wysiwyg, assert, 'https://www.youtube.com/watch?v=xxxxxxxxxxx');
                },
                test: {
                    check: async function () {
                        assert.deepEqual(wysiwyg.getValue(),
                            '<p><br></p><div class="media_iframe_video" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div><p><br></p>',
                            testName);
                    },
                },
            },
            // Replace video
            {
                name: "replace video by pictogram",
                async: true,
                content: '<p><br></p><div class="media_iframe_video" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div><p><br></p>',
                start: "div->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    check: async function () {
                        assert.deepEqual(wysiwyg.getValue(),
                            '<p>\u200B<span class="fa fa-glass"></span>\u200B</p>',
                            testName);
                    },
                },
            },
            {
                name: "replace video by pictogram (2)",
                async: true,
                content: '<p>aaa</p><div class="media_iframe_video" data-oe-expression="about:blank"><div class="css_editable_mode_display">&nbsp;</div><div class="media_iframe_video_size">&nbsp;</div><iframe src="about:blank" frameborder="0" allowfullscreen="allowfullscreen"></iframe></div><p>bbb</p>',
                start: "div->0",
                do: async function () {
                    await _insertPictogram('fa-glass');
                },
                test: {
                    check: async function () {
                        assert.deepEqual(wysiwyg.getValue(),
                            '<p>aaa<span class="fa fa-glass"></span>bbb</p>',
                            testName);
                    },
                },
            },
        ];

        var def = Promise.resolve();
        _.each(mediaTests, function (test) {
            def = def.then(async function () {
                testName = test.name;
                wysiwyg.setValue(test.content);
                var range = weTestUtils.select(test.start, test.end, $editable);
                await testUtils.dom.triggerEvents($(range.sc), ['mousedown', 'click']);
                Wysiwyg.setRange(range.sc, range.so, range.ec, range.eo);
                return _clickMedia(wysiwyg, assert, test.do, test.test);
            });
        });
        return def.then(function () {
            wysiwyg.destroy();
        });
    });
});


});
});
});
});
