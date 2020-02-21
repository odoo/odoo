odoo.define('web.abstract_view_tests', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var ajax = require('web.ajax');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;
var createAsyncView = testUtils.createAsyncView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            fake_model: {
                fields: {},
                record: [],
            },
            foo: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                },
                records: [
                    {id: 1, bar: true, foo: "yop"},
                    {id: 2, bar: true, foo: "blip"},
                ]
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

    QUnit.test('groupBy attribute can be a string, instead of a list of strings', function (assert) {
        assert.expect(2);

        var list = testUtils.createView({
            View: ListView,
            model: 'foo',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            groupBy: 'bar',
            mockRPC: function (route, args) {
                assert.strictEqual(args.method, 'read_group');
                assert.deepEqual(args.kwargs.groupby, ['bar']);
                return this._super.apply(this, arguments);
            },
        });
        list.destroy();
    });

    QUnit.test('groupBy dropdown not displayed if view is not groupable', function (assert) {
        assert.expect(1);

        ListView.prototype.groupable = false;
        var actionManager = createActionManager({
            actions: [{
                id: 1,
                name: 'Foo Action 1',
                res_model: 'foo',
                type: 'ir.actions.act_window',
                views: [[false, 'list']],
                context: {
                    group_by: ['bar'],
                },
            }],
            archs: {
                'foo,false,list': '<tree><field name="foo"/><field name="bar"/></tree>',
                'foo,false,search': '<search></search>',
            },
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    throw new Error("Should not do a read_group RPC");
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction(1);

        assert.containsNone($, 'o_dropdown:not(.o_hidden) .o_group_by_menu',
            "groupby menu should not be available");

        actionManager.destroy();
        ListView.prototype.groupable = true;
    });

});
});
