odoo.define('web.basic_view_banner_tests', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var BasicRenderer = require('web.BasicRenderer');

var testUtils = require('web.test_utils');
var createAsyncView = testUtils.createAsyncView;

var TestRenderer = BasicRenderer.extend({
    _renderView: function () {
        this.$el.addClass('test_content');
        return this._super();
    }
});
var TestView = BasicView.extend({
    type: 'test',
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: TestRenderer
    }),
});

QUnit.module('Views', {
        before: function () {
            this._ajax = $.ajax;
        },
        after: function () {
            $.ajax = this._ajax;
        },
        beforeEach: function () {
            this.data = {
                test_model: {
                    fields: {},
                    records: [],
                },
            };
        },
    },
    function () {
        QUnit.module('BasicRenderer');

        QUnit.test("The banner should be fetched from the route", function (assert) {
            var done = assert.async();
            assert.expect(1);
            // mock jQuery ajax
            $.ajax = function (options) {
                if (
                    options.url === '/module/hello_banner' &&
                    options.type === 'get'
                ) {
                    return $.when('<div class="hello_banner"/>');
                }
            };
            createAsyncView({
                View: TestView,
                model: "test_model",
                data: this.data,
                arch: '<test banner_route="/module/hello_banner"/>'
            }).then(function (view) {
                var $banner = view.$('.hello_banner');
                assert.strictEqual($banner.length, 1,
                    "the view should contain the response from the controller");
                done();
            });
        });
    }
);
});
