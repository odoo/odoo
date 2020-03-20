odoo.define('pad.pad_tests', function (require) {
"use strict";

var FieldPad = require('pad.pad');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('pad widget', {
    beforeEach: function () {
        this.data = {
            task: {
                fields: {
                    description: {string: "Description", type: "char"},
                    use_pad: {string: "Use pad", type: "boolean"},
                },
                records: [
                    {id: 1, description: false},
                    {id: 2, description: "https://pad.odoo.pad/p/test-03AK6RCJT"},
                ],
                pad_is_configured: function () {
                    return true;
                },
                pad_generate_url: function (route, args) {
                    return {
                        url:'https://pad.odoo.pad/p/test/' + args.context.object_id
                    };
                },
                pad_get_content: function () {
                    return "we should rewrite this server in haskell";
                },
            },
        };
    },
});

    QUnit.test('pad widget display help if server not configured', async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'pad_is_configured') {
                    return Promise.resolve(false);
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.isVisible(form.$('p.oe_unconfigured'),
            "help message should be visible");
        assert.containsNone(form, 'p.oe_pad_content',
            "content should not be displayed");
        await testUtils.form.clickEdit(form);
        assert.isVisible(form.$('p.oe_unconfigured'),
            "help message should be visible");
        assert.containsNone(form, 'p.oe_pad_content',
            "content should not be displayed");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget works, basic case', async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === 'https://pad.odoo.pad/p/test/1?showChat=false&userName=batman') {
                    assert.ok(true, "should have an iframe with correct src");
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        assert.isNotVisible(form.$('p.oe_unconfigured'),
            "help message should not be visible");
        assert.isVisible(form.$('.oe_pad_content'),
            "content should be visible");
        assert.containsOnce(form, '.oe_pad_content:contains(This pad will be)',
            "content should display a message when not initialized");

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, '.oe_pad_content iframe',
            "should have an iframe");

        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget works, with existing data', async function (assert) {
        assert.expect(3);

        var contentDef = testUtils.makeTestPromise();

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (_.str.startsWith(route, 'http')) {
                    return Promise.resolve(true);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'pad_get_content') {
                    return contentDef.then(_.constant(result));
                }
                if (args.method === 'write') {
                    assert.ok('description' in args.args[1],
                        "should always send the description value");
                }
                return result;
            },
            session: {
                userName: "batman",
            },
        });
        assert.strictEqual(form.$('.oe_pad_content').text(), "Loading",
            "should display loading message");
        contentDef.resolve();
        await testUtils.nextTick();
        assert.strictEqual(form.$('.oe_pad_content').text(), "we should rewrite this server in haskell",
            "should display proper value");

        await testUtils.form.clickEdit(form);
        await testUtils.form.clickSave(form);
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget is not considered dirty at creation', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (!args.method) {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        var def = form.canBeDiscarded();
        var defState = 'unresolved';
        def.then(function () {
            defState = 'resolved';
        });

        assert.strictEqual($('.modal').length, 0,
            "should have no confirmation modal opened");
        await testUtils.nextTick();
        assert.strictEqual(defState, 'resolved',
            "can be discarded was successfully resolved");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget is not considered dirty at edition', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (!args.method) {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        await testUtils.form.clickEdit(form);
        var def = form.canBeDiscarded();
        var defState = 'unresolved';
        def.then(function () {
            defState = 'resolved';
        });

        assert.strictEqual($('.modal').length, 0,
            "should have no confirmation modal opened");
        await testUtils.nextTick();
        assert.strictEqual(defState, 'resolved',
            "can be discarded was successfully resolved");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('record should be discarded properly even if only pad has changed', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="description" widget="pad"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (!args.method) {
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        await testUtils.form.clickEdit(form);
        await testUtils.form.clickDiscard(form);
        assert.strictEqual(form.$('.oe_pad_readonly').text(), this.data.task.pad_get_content(),
            "pad content should not have changed");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('no pad deadlock on form change modifying pad readonly modifier', async function (assert) {
        assert.expect(1);

        var form = await createView({
            View: FormView,
            model: 'task',
            data: this.data,
            arch:'<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="use_pad" widget="toggle_button"/>' +
                            '<field name="description" widget="pad" attrs="{\'readonly\': [(\'use_pad\', \'=\', False)]}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (!args.method) {
                    return Promise.resolve(true);
                }
                if (args.method === "write") {
                    assert.strictEqual(args.args[1].description,
                        "https://pad.odoo.pad/p/test-03AK6RCJT");
                }
                return this._super.apply(this, arguments);
            },
        });
        await testUtils.form.clickEdit(form);
        await testUtils.dom.click(form.$('.o_field_widget[name="use_pad"]'));
        await testUtils.form.clickSave(form);
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

});
