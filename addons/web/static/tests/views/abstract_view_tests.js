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

        var def = $.Deferred();
        var loadJS = ajax.loadJS;
        ajax.loadJS = function (url) {
            assert.step(url);
            return def.then(function () {
                assert.step(url + ' loaded');
            });
        };

        var View = AbstractView.extend({
            jsLibs: [['a', 'b']],
        });
        createAsyncView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['a', 'b', 'a loaded', 'b loaded'],
                "should wait for both libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });

        assert.verifySteps(['a', 'b'],
            "both libs should be loaded in parallel");
        def.resolve();
    });

    QUnit.test('lazy loading of js libs (sequentially)', function (assert) {
        var done = assert.async();
        assert.expect(10);

        var defs = {
            a: $.Deferred(),
            b: $.Deferred(),
            c: $.Deferred(),
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
            ],
        });
        createAsyncView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['a', 'b', 'b loaded', 'a loaded', 'c', 'c loaded'],
                "should for all libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });

        assert.verifySteps(['a', 'b'],
            "libs 'a' and 'b' should be loaded in parallel");
        defs.b.resolve();
        assert.verifySteps(['a', 'b', 'b loaded'],
            "should wait for 'a' and 'b' to be loaded before loading 'c'");
        defs.a.resolve();
        assert.verifySteps(['a', 'b', 'b loaded', 'a loaded', 'c'],
            "should load 'c' when 'a' and 'b' are loaded");
        defs.c.resolve();
    });
});
});
