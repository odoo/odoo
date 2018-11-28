odoo.define('web_editor.field.html.mobile.tests', function (require) {
'use strict';

var config = require('web.config');
if (!config.device.isMobile) {
    return;
}

var concurrency = require('web.concurrency');
var fieldHtml = require('web_editor.field.html');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var weTestUtils = require('web_editor.test_utils');
var _t = require('web.core')._t;

QUnit.module('field html mobile', {
    beforeEach: function () {
        this.data = weTestUtils.wysiwygData({
            'editor.mobile_test': {
                fields: {
                    display_name: {
                        string: "Displayed name",
                        type: "char"
                    },
                    body: {
                        string: "Message",
                        type: "html"
                    },
                },
                records: [{
                    id: 1,
                    display_name: "body",
                    body: "<p>Pika Pika</p><p>Chu !</p>",
                }],
            }
        });
    },
}, function () {

    QUnit.module('field html mobile');

    QUnit.test('mobile scrollbar test', function (assert) {
        var done = assert.async();
        assert.expect(7);

        testUtils.mock.patch(fieldHtml, {
            init: function () {
                this._super.apply(this, arguments);
                this._computeScrollBarIconPosition = Object.getPrototypeOf(this)._computeScrollBarIconPosition;
            },
        });

        testUtils.createAsyncView({
            View: FormView,
            model: 'editor.mobile_test',
            data: this.data,
            arch: '<form><div style="width: 100px"><field name="body" widget="html" /></div></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        }).then(function (form) {
            var end = function () {
                testUtils.mock.unpatch(fieldHtml);
                form.destroy();
                done();
            };

            var checkEndScroll = function () {
                var $toolbarWrapper = form.$('.note-toolbar-wrapper');

                assert.hasClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as the scroll end at the right");
                assert.doesNotHaveClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as not the scroll end at the right");
            };

            var checkMiddleScroll = function () {
                var $toolbarWrapper = form.$('.note-toolbar-wrapper');

                assert.hasClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as the scroll start at the middle");
                assert.hasClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as the scroll end at the middle");

                var $toolbar = $toolbarWrapper.find('.note-toolbar');
                $toolbar.scrollLeft($toolbar.get(0).scrollWidth);
            };

            var checkBeginScroll = function () {
                var $toolbarWrapper = form.$('.note-toolbar-wrapper');

                assert.hasClass($toolbarWrapper, 'note-toolbar-scrollable',
                    "The toolbar wrapper is flag as scrollable");

                assert.doesNotHaveClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as not the scroll start at the left");

                assert.hasClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as the scroll end at the left");

                $toolbarWrapper.find('.note-toolbar').scrollLeft(30);
            };

            concurrency.delay(0)
                .then(function () {
                    checkBeginScroll();
                    return concurrency.delay(0);
                })
                .then(function () {
                    checkMiddleScroll();
                    return concurrency.delay(0);
                })
                .then(checkEndScroll)
                .then(end);
        });
    });

    QUnit.test('mobile dropdown', function (assert) {
        var done = assert.async();
        assert.expect(6);

        testUtils.createAsyncView({
            View: FormView,
            model: 'editor.mobile_test',
            data: this.data,
            arch: '<form><field name="body" widget="html" /></form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        }).then(function (form) {
            concurrency.delay(0)
                .then(function () {
                    // focus
                    form.$('.note-editable *').first().mousedown().mouseup();
                    // check dropdowns
                    assert.strictEqual(form.$('.note-toolbar-wrapper .note-toolbar .note-btn-group > .dropdown-menu')
                        .first().attr('cancel'), _t('Discard'), "should have the attribute cancel with discard value");
                    // click on dropdown and check the full screen and value
                    testUtils.dom.click(form.$('.note-style .note-btn'));
                    var $dropdown = form.$('.note-toolbar-wrapper .note-toolbar .note-btn-group > .dropdown-menu').first();
                    assert.hasClass($dropdown, 'show', 'dropdown is displayed on screen');
                    assert.strictEqual(getComputedStyle($dropdown.get(0), ':before').getPropertyValue('content'),
                        '"' + _t('Discard') + '"', "should have the node cancel define by the before item");
                    assert.strictEqual(getComputedStyle($dropdown.get(0)).getPropertyValue('top'), '0px',
                        "should have the top 0 item");
                    assert.strictEqual(getComputedStyle($dropdown.get(0)).getPropertyValue('left'), '0px',
                        "should have the left 0 item");
                    assert.strictEqual(getComputedStyle($dropdown.get(0)).getPropertyValue('position'), 'fixed',
                        "should have a fixed position item");
                    form.destroy();
                    done();
                });
        });
    });
});
});
