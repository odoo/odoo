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

    QUnit.test('pad widget display help if server not configured', function (assert) {
        assert.expect(4);

        var form = createView({
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
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.ok(form.$('p.oe_unconfigured').is(':visible'),
            "help message should be visible");
        assert.notOk(form.$('p.oe_pad_content').is(':visible'),
            "content should not be visible");
        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('p.oe_unconfigured').is(':visible'),
            "help message should be visible");
        assert.notOk(form.$('p.oe_pad_content').is(':visible'),
            "content should not be visible");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget works, basic case', function (assert) {
        assert.expect(5);

        var form = createView({
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
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        assert.notOk(form.$('p.oe_unconfigured').is(':visible'),
            "help message should not be visible");
        assert.ok(form.$('.oe_pad_content').is(':visible'),
            "content should be visible");
        assert.strictEqual(form.$('.oe_pad_content:contains(This pad will be)').length, 1,
            "content should display a message when not initialized");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.oe_pad_content iframe').length, 1,
            "should have an iframe");

        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget works, with existing data', function (assert) {
        assert.expect(3);

        var contentDef = $.Deferred();

        var form = createView({
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
                    return $.when(true);
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
        assert.strictEqual(form.$('.oe_pad_content').text(), "we should rewrite this server in haskell",
            "should display proper value");

        form.$buttons.find('.o_form_button_edit').click();
        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget is not considered dirty at creation', function (assert) {
        assert.expect(2);

        var form = createView({
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
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        var def = form.canBeDiscarded();

        assert.strictEqual($('.modal').length, 0,
            "should have no confirmation modal opened");

        assert.strictEqual(def.state(), 'resolved',
            "can be discarded was succesfully resolved");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('pad widget is not considered dirty at edition', function (assert) {
        assert.expect(2);

        var form = createView({
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
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        var def = form.canBeDiscarded();

        assert.strictEqual($('.modal').length, 0,
            "should have no confirmation modal opened");

        assert.strictEqual(def.state(), 'resolved',
            "can be discarded was succesfully resolved");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

    QUnit.test('record should be discarded properly even if only pad has changed', function (assert) {
        assert.expect(1);

        var form = createView({
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
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
            session: {
                userName: "batman",
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual(form.$('.oe_pad_readonly').text(), this.data.task.pad_get_content(),
            "pad content should not have changed");
        form.destroy();
        delete FieldPad.prototype.isPadConfigured;
    });

});
