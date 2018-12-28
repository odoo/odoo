odoo.define('web_editor.wysiwyg_snippets_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var MediaDialog = require('wysiwyg.widgets.MediaDialog');


QUnit.module('web_editor', {}, function () {
QUnit.module('wysiwyg', {}, function () {
QUnit.module('Snippets', {}, function () {

QUnit.test('drag&drop', function (assert) {
    var done = assert.async();
    assert.expect(2);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<p>toto toto toto</p><p>tata</p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        var $hr = wysiwyg.snippets.$('.oe_snippet_thumbnail:first');
        testUtils.dom.dragAndDrop($hr, $editable.find('p'));

        assert.strictEqual($editable.html().replace(/\s+/g, ' '),
            '<p>toto toto toto</p><div class=\"s_hr pt32 pb32\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>tata</p>',
            "should drop the snippet");

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            assert.strictEqual($editable.html().replace(/\s+/g, ' '),
                '<p>toto toto toto</p><div class=\"s_hr pt32 pb32 built focus\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>tata</p>',
                "should build and focus the snippet");

            wysiwyg.destroy();
            done();
        });
    });
});

QUnit.test('begin drag&drop must hide popovers', function (assert) {
    var done = assert.async();
    assert.expect(2);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value:
                '<div class="s_hr pt32 pb32"> ' +
                    '<hr class="s_hr_1px s_hr_solid w-100 mx-auto"> ' +
                    '<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png"> ' +
                '</div>' +
                '<h1>test</h1>' +
                '<p><b>test</b></p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        $editable.find('.s_hr img').mousedown().click();
        assert.strictEqual($('.note-popover:visible').length, 1, "should display the image popover");

        var $hr = wysiwyg.snippets.$('.oe_snippet_thumbnail:first');
        testUtils.dom.dragAndDrop($hr, $editable.find('h1'), {
            disableDrop: true,
        });
        assert.strictEqual($('.note-popover:visible').length, 0, "should hide the image popover");
        testUtils.dom.dragAndDrop($hr, $editable.find('h1'), {
            continueMove: true,
        });

        wysiwyg.destroy();
        done();
    });
});

QUnit.test('change size option must hide popovers', function (assert) {
    var done = assert.async();
    assert.expect(4);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value:
                '<div class="s_hr pt32 pb32"> ' +
                    '<hr class="s_hr_1px s_hr_solid w-100 mx-auto"> ' +
                    '<img class="img-fluid o_we_custom_image" data-src="/web_editor/static/src/img/transparent.png"> ' +
                '</div>' +
                '<h1>test</h1>' +
                '<p><b>test</b></p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        $editable.find('.s_hr img').mousedown().click();
        assert.strictEqual($('.note-popover:visible').length, 1, "should display the image popover");

        var $handle = $('#oe_manipulators .o_handle.s');
        testUtils.dom.dragAndDrop($handle, $editable.find('b'), {
            disableDrop: true,
        });
        assert.ok($handle.hasClass('o_active'), "should active the handle");
        assert.notOk($handle.hasClass('pb32'), "should change the padding bottom");
        assert.strictEqual($('.note-popover:visible').length, 0, "should hide the image popover");
        testUtils.dom.dragAndDrop($handle, $editable.find('b'), {
            continueMove: true,
        });

        wysiwyg.destroy();
        done();
    });
});

QUnit.test('clean the dom before save, after drag&drop', function (assert) {
    var done = assert.async();
    assert.expect(1);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<p>toto toto toto</p><p>tata</p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        var $hr = wysiwyg.snippets.$('.oe_snippet_thumbnail:first');
        testUtils.dom.dragAndDrop($hr, $editable.find('p'));

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            wysiwyg.save().then(function (isDirty, html) {
                assert.strictEqual(html.replace(/\s+/g, ' '),
                    '<p>toto toto toto</p><div class=\"s_hr pt32 pb32 built cleanForSave\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div><p>tata</p>',
                    "should clean the snippet");

                wysiwyg.destroy();
                done();
            });
        });
    });
});

QUnit.test('clean the dom before save', function (assert) {
    var done = assert.async();
    assert.expect(1);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<div class="s_hr pt32 pb32"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            // add dirty flag to remove warning because the cleaned dom is different of the initial value and no dirty flag
            $editable.find('.s_hr').keydown();

            // trigger change to avoid warning because the DOM change on clean without trigger onchange by snippet or edition
            $editable.trigger('content_changed');

            wysiwyg.save().then(function (isDirty, html) {
                assert.strictEqual(html.replace(/\s+/g, ' '),
                    '<div class=\"s_hr pt32 pb32 cleanForSave\"> <hr class=\"s_hr_1px s_hr_solid w-100 mx-auto\"> </div>',
                    "should clean the snippet");

                wysiwyg.destroy();
                done();
            });
        });

        $editable.find('.s_hr').mousedown().click();
    });
});

QUnit.test('remove snippet', function (assert) {
    var done = assert.async();
    assert.expect(1);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<div class="s_hr pt32 pb32"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            $('#oe_manipulators .oe_overlay_options .oe_snippet_remove').click();

            wysiwyg.save().then(function (isDirty, html) {
                assert.strictEqual(html.replace(/\s+/g, ' '), '', "should remove the snippet");

                wysiwyg.destroy();
                done();
            });
        });

        $editable.find('.s_hr').mousedown().click();
    });
});

QUnit.test('move a snippet', function (assert) {
    var done = assert.async();
    assert.expect(1);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<div class="s_hr pt32 pb32"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><h1>test</h1><p><b>test</b></p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        var first = true;
        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            if (first) {
                first = false;
                var $hr = $('#oe_manipulators .oe_overlay_options .oe_snippet_move');
                testUtils.dom.dragAndDrop($hr, $editable.find('b'));
            } else {
                wysiwyg.save().then(function (isDirty, html) {
                    assert.strictEqual(html.replace(/\s+/g, ' '),
                        '<h1>test</h1><div class="s_hr pt32 pb32 move cleanForSave"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><p><b>test</b></p>',
                        "should move the snippet on the bottom");

                    wysiwyg.destroy();
                    done();
                });
            }
        });

        $editable.find('.s_hr').mousedown().click();
    });
});

QUnit.test('clone a snippet', function (assert) {
    var done = assert.async();
    assert.expect(2);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<div class="s_hr pt32 pb32"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><h1>test</h1><p><b>test</b></p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            $('#oe_manipulators .oe_overlay_options .oe_snippet_clone').click();

            assert.strictEqual($editable.html().replace(/\s+/g, ' '),
                '<div class="s_hr pt32 pb32 focus"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><div class="s_hr pt32 pb32 clone"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><h1>test</h1><p><b>test</b></p>',
                "should duplicate the snippet");

            wysiwyg.save().then(function (isDirty, html) {
                assert.strictEqual(html.replace(/\s+/g, ' '),
                    '<div class="s_hr pt32 pb32 cleanForSave"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><div class="s_hr pt32 pb32 clone cleanForSave"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><h1>test</h1><p><b>test</b></p>',
                    "should duplicate the snippet");

                wysiwyg.destroy();
                done();
            });
        });

        $editable.find('.s_hr').mousedown().click();
    });
});

QUnit.test('customize snippet', function (assert) {
    var done = assert.async();
    assert.expect(3);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<h1>test</h1><div class="s_hr pt32 pb32"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><p><b>test</b></p>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            $('#oe_manipulators .oe_overlay_options .oe_options a:first').click();
            var $option = $('#oe_manipulators .oe_overlay_options a[data-select-class="align-items-center"]');

            assert.strictEqual($option.size(), 1, "should display the snippet option");

            $option.click();

            assert.strictEqual($editable.html().replace(/\s+/g, ' '),
                '<h1>test</h1><div class="s_hr pt32 pb32 focus align-items-center"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><p><b>test</b></p>',
                "should customized the snippet");

            $('#oe_manipulators .oe_overlay_options .oe_options a:first').click();
            $('#oe_manipulators .oe_overlay_options a[data-select-class="align-items-end"]').click();

            assert.strictEqual($editable.html().replace(/\s+/g, ' '),
                '<h1>test</h1><div class="s_hr pt32 pb32 focus align-items-end"> <hr class="s_hr_1px s_hr_solid w-100 mx-auto"> </div><p><b>test</b></p>',
                "should twice customized the snippet");

            wysiwyg.destroy();
            done();
        });

        $editable.find('.s_hr').mousedown().click();
    });
});

QUnit.test('background-image', function (assert) {
    var done = assert.async();
    assert.expect(2);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value:
                '<h1>Big Title</h1>' +
                '<section class="test_option_all pt32 pb32">' +
                '    <div class="container">' +
                '        <div class="row">' +
                '            <div class="col-lg-10 offset-lg-1 pt32 pb32">' +
                '                <h2>Title</h2>' +
                '                <p class="lead o_default_snippet_text">Content</p>' +
                '            </div>' +
                '        </div>' +
                '    </div>' +
                '</section>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        var defMediaDialogInit = $.Deferred();
        var defMediaDialogSave = $.Deferred();
        testUtils.mock.patch(MediaDialog, {
            init: function () {
                this._super.apply(this, arguments);
                this.opened(defMediaDialogInit.resolve.bind(defMediaDialogInit));
            },
            save: function () {
                $.when(this._super.apply(this, arguments)).then(function () {
                    defMediaDialogSave.resolve();
                });
            },
        });

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            $('#oe_manipulators .oe_overlay_options .oe_options a:first').click();
            $('#oe_manipulators .oe_overlay_options a.snippet-option-background[data-choose-image]').click();

            defMediaDialogInit.then(function () {
                $('.modal.note-image-dialog .existing-attachments .o_image').click();
                $('.modal.note-image-dialog .modal-footer .btn-primary').click();
            });

            defMediaDialogSave.then(function () {
                var $snippet = $editable.find('.test_option_all');
                assert.ok($snippet.hasClass('oe_custom_bg'), "should use custom background");
                var background = $snippet.css('background-image') || '';
                assert.strictEqual(background.replace(/[^(\("'\/]+\/\/[^\("'\/]+/, ''),
                    'url("/web_editor/static/src/img/transparent.png")',
                    "should change the background image");

                testUtils.mock.unpatch(MediaDialog);
                wysiwyg.destroy();
                done();
            });
        });

        $editable.find('h2').mousedown().click();
    });
});

QUnit.test('update content', function (assert) {
    var done = assert.async();
    assert.expect(1);

    return weTestUtils.createWysiwyg({
        wysiwygOptions: {
            snippets: true,
            value: '<div class="s_hr pt32 pb32"> ' +
                    '<img class="img-fluid o_we_custom_image test_option_all" data-src="/web_editor/static/src/img/transparent.png"> ' +
                '</div>',
        },
    }).then(function (wysiwyg) {
        var $editable = wysiwyg.getEditable();

        testUtils.mock.intercept(wysiwyg, "snippet_focused", function () {
            var $snippetOption = $('#oe_manipulators .oe_overlay_options:visible');
            wysiwyg.$el.siblings('.note-image-popover').find('.note-media .note-icon-trash').mousedown().click();
            assert.ok($snippetOption.is(':hidden'), "should remove the snippet editor because the target are removed");

            wysiwyg.destroy();
            done();
        });

        $editable.find('img').mousedown().click();
    });
});

});
});
});
});
