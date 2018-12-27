odoo.define('web.abstract_view_banner_tests', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var AbstractView = require('web.AbstractView');

var testUtils = require('web.test_utils');
var createAsyncView = testUtils.createAsyncView;

var TestRenderer = AbstractRenderer.extend({
    _renderView: function () {
        this.$el.addClass('test_content');
        return this._super();
    },
});

var TestView = AbstractView.extend({
    type: 'test',
    config: _.extend({}, AbstractView.prototype.config, {
        Renderer: TestRenderer
    }),
});

var test_css_url = '/test_assetsbundle/static/src/css/test_cssfile1.css';

QUnit.module('Views', {
        beforeEach: function () {
            this.data = {
                test_model: {
                    fields: {},
                    records: [],
                },
            };
        },
        afterEach: function () {
            $('head link[href$="' + test_css_url + '"]').remove();
        }
    }, function () {
        QUnit.module('BasicRenderer');

        QUnit.test("The banner should be fetched from the route", function (assert) {
            var done = assert.async();
            assert.expect(5);

            var banner_html =
                '<div>' +
                    '<link type="text/css" href="' + test_css_url + '" rel="stylesheet">' +
                    '<div class="hello_banner"/>' +
                '</div>';

            createAsyncView({
                View: TestView,
                model: 'test_model',
                data: this.data,
                arch: '<test banner_route="/module/hello_banner"/>',
                mockRPC: function (route, args) {
                    if (route === '/module/hello_banner') {
                        assert.step(route);
                        return $.when({html: banner_html});
                    }
                    return this._super(route, args);
                },
            }).then(function (view) {
                var $banner = view.$('.hello_banner');
                assert.strictEqual($banner.length, 1,
                    "The view should contain the response from the controller.");
                assert.verifySteps(['/module/hello_banner'], "The banner should be fetched.");

                var $head_link = $('head link[href$="' + test_css_url + '"]');
                assert.strictEqual($head_link.length, 1,
                    "The stylesheet should have been added to head.");

                var $banner_link = $('link[href$="' + test_css_url + '"]', $banner);
                assert.strictEqual($banner_link.length, 0,
                    "The stylesheet should have been removed from the banner.");
                view.destroy();
                done();
            });
        });
    }
);
});
