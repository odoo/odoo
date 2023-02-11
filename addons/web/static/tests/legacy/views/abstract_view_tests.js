odoo.define('web.abstract_view_tests', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var ajax = require('web.ajax');
var testUtils = require('web.test_utils');

const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
var createView = testUtils.createView;

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

    QUnit.test('lazy loading of js libs (in parallel)', async function (assert) {
        var done = assert.async();
        assert.expect(6);

        var prom = testUtils.makeTestPromise();
        var loadJS = ajax.loadJS;
        ajax.loadJS = function (url) {
            assert.step(url);
            return prom.then(function () {
                assert.step(url + ' loaded');
            });
        };

        var View = AbstractView.extend({
            jsLibs: [['a', 'b']],
        });
        createView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['a loaded', 'b loaded'],
                "should wait for both libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });

        await testUtils.nextTick();
        assert.verifySteps(['a', 'b'], "both libs should be loaded in parallel");
        prom.resolve();
    });

    QUnit.test('lazy loading of js libs (sequentially)', async function (assert) {
        var done = assert.async();
        assert.expect(10);

        var proms = {
            a:  testUtils.makeTestPromise(),
            b:  testUtils.makeTestPromise(),
            c:  testUtils.makeTestPromise(),
        };
        var loadJS = ajax.loadJS;
        ajax.loadJS = function (url) {
            assert.step(url);
            return proms[url].then(function () {
                assert.step(url + ' loaded');
            });
        };

        var View = AbstractView.extend({
            jsLibs: [
                ['a', 'b'],
                'c',
            ],
        });
        createView({
            View: View,
            arch: '<fake/>',
            data: this.data,
            model: 'fake_model',
        }).then(function (view) {
            assert.verifySteps(['c loaded'], "should wait for all libs to be loaded");
            ajax.loadJS = loadJS;
            view.destroy();
            done();
        });
        await testUtils.nextTick();
        assert.verifySteps(['a', 'b'], "libs 'a' and 'b' should be loaded in parallel");
        await proms.b.resolve();
        await testUtils.nextTick();
        assert.verifySteps(['b loaded'], "should wait for 'a' and 'b' to be loaded before loading 'c'");
        await proms.a.resolve();
        await testUtils.nextTick();
        assert.verifySteps(['a loaded', 'c'], "should load 'c' when 'a' and 'b' are loaded");
        await proms.c.resolve();
    });

    QUnit.test('group_by from context can be a string, instead of a list of strings', async function (assert) {
        assert.expect(1);

        const serverData = {
            actions: {
                1: {
                    id: 1,
                    name: 'Foo',
                    res_model: 'foo',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list']],
                    context: {
                        group_by: 'bar',
                    },
                }
            },
            views: {
                'foo,false,list': '<tree><field name="foo"/><field name="bar"/></tree>',
                'foo,false,search': '<search></search>',
            },
            models: this.data
        };

        const mockRPC = (route, args) => {
            if (args.method === 'web_read_group') {
                assert.deepEqual(args.kwargs.groupby, ['bar']);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
    });

});
});
