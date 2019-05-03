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
                    body: `<p>Pika Pika</p><p>Chu !</p>`,
                }],
            }
        });
    },
}, function () {

    QUnit.module('field html mobile');

    QUnit.test('mobile scrollbar test begin', function (assert) {

        assert.expect(3);
        var done = assert.async();

        testUtils.mock.patch(fieldHtml, {
            init: function () {
                this._super.apply(this, arguments);
                this._throttleComputeScrollBarIconPosition = this._computeScrollBarIconPosition;
                this._throttleHideDropdownMenuShow = this._hideDropdownMenuShow;
            },
        });

        testUtils.createAsyncView({
            View: FormView,
            model: 'editor.mobile_test',
            data: this.data,
            arch: `<form>
                        <div style="width: 100px">
                            <field name="body" widget="html" />
                        </div>
                    </form>`,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        }).then(function (form) {
            var $toolbarWrapper = form.$('.note-toolbar-wrapper');

            function check() {
                assert.hasClass($toolbarWrapper, 'note-toolbar-scrollable',
                    "The toolbar wrapper is flag as scrollable");

                assert.doesNotHaveClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as not the scroll start at the left");

                assert.hasClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as the scroll end at the left");
                testUtils.mock.unpatch(fieldHtml);
                form.destroy();
                done();
            }

            concurrency.delay(0).then(check);
        });
    });

    QUnit.test('mobile scrollbar test middle', function (assert) {

        assert.expect(2);
        var done = assert.async();

        testUtils.mock.patch(fieldHtml, {
            init: function () {
                this._super.apply(this, arguments);
                this._throttleComputeScrollBarIconPosition = this._computeScrollBarIconPosition;
                this._throttleHideDropdownMenuShow = this._hideDropdownMenuShow;
            },
        });

        testUtils.createAsyncView({
            View: FormView,
            model: 'editor.mobile_test',
            data: this.data,
            arch: `<form>
                        <div style="width: 100px">
                            <field name="body" widget="html" />
                        </div>
                    </form>`,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        }).then(function (form) {

            var $toolbarWrapper = form.$('.note-toolbar-wrapper');
            var $toolbar = $toolbarWrapper.find('.note-toolbar');
            var midScrollLeft = Math.round(($toolbar.get(0).scrollWidth - $toolbar.get(0).clientWidth) / 2);
            $toolbar.scrollLeft(midScrollLeft);

            function check() {
                assert.hasClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as the scroll start at the middle");
                assert.hasClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as the scroll end at the middle");
                testUtils.mock.unpatch(fieldHtml);
                form.destroy();
                done();
            }

            concurrency.delay(0).then(check);
        });
    });

    QUnit.test('mobile scrollbar test end', function (assert) {

        assert.expect(2);
        var done = assert.async();

        testUtils.mock.patch(fieldHtml, {
            init: function () {
                this._super.apply(this, arguments);
                this._throttleComputeScrollBarIconPosition = this._computeScrollBarIconPosition;
                this._throttleHideDropdownMenuShow = this._hideDropdownMenuShow;
            },
        });

        testUtils.createAsyncView({
            View: FormView,
            model: 'editor.mobile_test',
            data: this.data,
            arch: `<form>
                        <div style="width: 100px">
                            <field name="body" widget="html" />
                        </div>
                    </form>`,
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        }).then(function (form) {

            var $toolbarWrapper = form.$('.note-toolbar-wrapper');
            var $toolbar = $toolbarWrapper.find('.note-toolbar');
            var endScrollLeft = Math.round($toolbar.get(0).scrollWidth - $toolbar.get(0).clientWidth);
            $toolbar.scrollLeft(endScrollLeft);

            function check() {
                assert.hasClass($toolbarWrapper, 'scrollable-start',
                    "The toolbar wrapper is flag as the scroll end at the right");
                assert.doesNotHaveClass($toolbarWrapper, 'scrollable-end',
                    "The toolbar wrapper is flag as not the scroll end at the right");

                // clean
                testUtils.mock.unpatch(fieldHtml);
                form.destroy();
                done();
            }

            concurrency.delay(0).then(check);
        });
    });
});
});
