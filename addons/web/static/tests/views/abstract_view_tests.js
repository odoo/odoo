odoo.define('web.abstract_view_tests', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var ajax = require('web.ajax');
var testUtils = require('web.test_utils');

var createAsyncView = testUtils.createAsyncView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            fake_model: {
                fields: {},
                record: [],
            },
        };
    },
}, function () {

    QUnit.module('AbstractView');

    QUnit.test('lazy loading of js libs (in parallel)', function (assert) {
        var done = assert.async();
        assert.expect(6);

        var defs = {
            a: $.Deferred(),
            b: $.Deferred(),
        };
        var loadJS = ajax.loadJS;
        ajax.loadJS = function (url) {
            assert.step(url);
            return defs[url].then(function () {
                assert.step(url + ' loaded');
            });
        };

        var View = AbstractView.extend({
            jsLibs: ['a', 'b'],
        });
        createAsyncView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['a', 'b', 'b loaded', 'a loaded'],
                "should wait for both libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });

        assert.verifySteps(['a', 'b'],
            "both libs should be loaded in parallel");
        defs.b.resolve();
        defs.a.resolve();
    });

    QUnit.test('lazy loading of js libs (sequentially)', function (assert) {
        var done = assert.async();
        assert.expect(12);

        var defs = {
            a: $.Deferred(),
            b: $.Deferred(),
            c: $.Deferred(),
            d: $.Deferred(),
        };
        var loadJS = ajax.loadJS;
        ajax.loadJS = function (url) {
            assert.step(url);
            return defs[url].then(function () {
                assert.step(url + ' loaded');
            });
        };

        var View = AbstractView.extend({
            jsLibs: [
                ['a', 'b'],
                'c',
                'd',
            ],
        });
        createAsyncView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['a', 'c', 'd', 'd loaded', 'c loaded', 'a loaded', 'b', 'b loaded'],
                "should for all libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });

        assert.verifySteps(['a', 'c', 'd'],
            "libs ['a', 'b'] and 'c' and 'd' should be loaded in parallel");
        defs.d.resolve();
        defs.c.resolve();
        assert.verifySteps(['a', 'c', 'd', 'd loaded', 'c loaded'],
            "libs 'a', 'c' and 'd' should be loaded in parallel");
        defs.a.resolve();
        assert.verifySteps(['a', 'c', 'd', 'd loaded', 'c loaded', 'a loaded', 'b'],
            "should wait for 'a' to be loaded before loading 'b'");
        defs.b.resolve();
    });
});
});
