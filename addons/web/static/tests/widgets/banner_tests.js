odoo.define('web.banner_tests', function (require) {
"use strict";

var BasicView = require('web.BasicView');
var BasicRenderer = require('web.BasicRenderer');
var Banner = require('web.Banner');

var testUtils = require('web.test_utils');

var createAsyncView = testUtils.createAsyncView;

var TestRenderer = BasicRenderer.extend({
    _renderView: function () {
        this.$el.addClass('test_content');
        this.$el.append('<div class="inner"/>');
        return this._super();
    },
});
var TestView = BasicView.extend({
    type: 'test',
    config: _.extend({}, BasicView.prototype.config, {
        Renderer: TestRenderer
    }),
});

QUnit.module('Widgets', {
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
                    records: []
                }
            };
        },
    },
    function () {
        QUnit.module('Banner');

        QUnit.test("Clicking on a banner <a> should trigger the correct action",
            function (assert) {
                var done = assert.async();
                assert.expect(4);

                var html =
                    '<div>' +
                        '<a class="route" data-route="/test/route">' +
                        "test" +
                        '</a>' +
                        '<a class="method_model" data-method="test_method" data-model="test_model">' +
                        "test" +
                        '</a>' +
                        '<a class="both" data-method="test_method" data-model="test_model" data-route="/test/route2">' +
                        "test" +
                        '</a>' +
                    '</div>';

                createAsyncView({
                    View: TestView,
                    model: 'test_model',
                    data: this.data,
                    arch: '<test />',
                    mockRPC: function (route, args) {
                        if (route !== '/web/dataset/search_read') {
                            assert.step(route);
                            return $.when();
                        }
                        return this._super(route, args);
                    },
                }).then(function (view) {
                    var banner = new Banner(view, html);
                    banner.appendTo(view.$('.inner')).then(function () {
                        view.$('.route').click();
                        view.$('.method_model').click();
                        view.$('.both').click();

                        assert.verifySteps([
                            '/test/route',
                            '/web/dataset/call_kw/test_model/test_method',
                            '/test/route2',
                        ]);
                        banner.destroy();
                        done();
                    });
                });
            }
        );

        QUnit.test("Clicking on a banner <button> should trigger the correct action",
            function (assert) {
                var done = assert.async();
                assert.expect(4);

                var html =
                    '<div>' +
                        '<button class="route" data-route="/test/route">' +
                        "test" +
                        '</button>' +
                        '<button class="method_model" data-method="test_method" data-model="test_model">' +
                        "test" +
                        '</button>' +
                        '<button class="both" data-method="test_method2" data-model="test_model2" data-route="/test/route2">' +
                        "test" +
                        '</button>' +
                    '</div>';

                createAsyncView({
                    View: TestView,
                    model: 'test_model',
                    data: this.data,
                    arch: '<test />',
                    mockRPC: function (route, args) {
                        if (route !== '/web/dataset/search_read') {
                            assert.step(route);
                            return $.when();
                        }
                        return this._super(route, args);
                    },
                }).then(function (view) {
                    var banner = new Banner(view, html);
                    banner.appendTo(view.$('.inner')).then(function () {
                        view.$('.route').click();
                        view.$('.method_model').click();
                        view.$('.both').click();

                        assert.verifySteps([
                            '/test/route',
                            '/web/dataset/call_kw/test_model/test_method',
                            '/test/route2'
                        ]);
                        banner.destroy();
                        done();
                    });
                });
            }
        );

        QUnit.test("Clicking on a <a> or <button> with invalid data should do nothing",
            function (assert) {
                var done = assert.async();
                assert.expect(1);

                var html =
                    '<div>' +
                        '<a class="nothing">' +
                        "test" +
                        '</a>' +
                        '<button class="only_model" data-model="test_model">' +
                        "test" +
                        '</button>' +
                    '</div>';

                createAsyncView({
                    View: TestView,
                    model: 'test_model',
                    data: this.data,
                    arch: '<test />',
                    mockRPC: function (route, args) {
                        if (route !== '/web/dataset/search_read') {
                            assert.step(route);
                            return $.when();
                        }
                        return this._super(route, args);
                    },
                }).then(function (view) {
                    var banner = new Banner(view, html);
                    banner.appendTo(view.$('.inner')).then(function () {
                        view.$('.nothing').click();
                        view.$('.only_model').click();

                        assert.verifySteps([]);
                        banner.destroy();
                        done();
                    });
                });
            }
        );

       QUnit.test("The specified id should be passed in the request",
            function (assert) {
                var done = assert.async();
                assert.expect(2);

                var html =
                    '<div>' +
                        '<a class="with_id" data-method="test_method" data-model="test_model" data-id="666">' +
                        "test" +
                        '</a>' +
                    '</div>';

                createAsyncView({
                    View: TestView,
                    model: 'test_model',
                    data: this.data,
                    arch: '<test />',
                    mockRPC: function (route, args) {
                        if (route !== '/web/dataset/search_read') {
                            if (args && args.args && args.args[0]) {
                                var id = args.args[0];
                            } else {
                                var id = '';
                            }
                            assert.step([route, id]);
                            return $.when();
                        }
                        return this._super(route, args);
                    },
                }).then(function (view) {
                    var banner = new Banner(view, html);
                    banner.appendTo(view.$('.inner')).then(function () {
                        view.$('.with_id').click();
                        assert.verifySteps([
                            ['/web/dataset/call_kw/test_model/test_method', 666],
                        ]);
                        banner.destroy();
                        done();
                    });
                });
            }
        );
    }
);
});
