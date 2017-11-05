# -*- coding: utf-8 -*-
"""
Test various crap patterns found in Odoo code to ensure they don't blow up
the parser thingie
"""
from autojsdoc.parser import jsdoc
from support import parse

def test_export_external():
    [mod] = parse("""
    odoo.define('module', function () {
        return $.Deferred().reject();
    });
    """)
    assert isinstance(mod.exports, jsdoc.CommentDoc)
    assert mod.exports.doc == ''

def test_extend_jq():
    parse("""
    odoo.define('a', function (r) {
        $.extend($.expr[':'], { a: function () {} });
        $.fn.extend({ a: function () {} });
    });
    """)

def test_extend_dynamic():
    parse("""
    odoo.define('a', function () {
        foo.bar.baz[qux + '_external'] = function () {};
    });
    """)

def test_extend_deep():
    parse("""
    odoo.define('a', function () {
        var eventHandler = $.summernote.eventHandler;
        var dom = $.summernote.core.dom;
        dom.thing = function () {};

        var fn_editor_currentstyle = eventHandler.modules.editor.currentStyle;
        eventHandler.modules.editor.currentStyle = function () {}
    });
    """)

def test_arbitrary():
    parse("""
    odoo.define('bob', function () {
        var page = window.location.href.replace(/^.*\/\/[^\/]+/, '');
        var mailWidgets = ['mail_followers', 'mail_thread', 'mail_activity', 'kanban_activity'];
        var bob;
        var fldj = foo.getTemplate().baz;
    });
    """)

def test_prototype():
    [A, B] = parse("""
    odoo.define('mod1', function () {
        var exports = {};
        exports.Foo = Backbone.Model.extend({});
        exports.Bar = Backbone.Model.extend({});
        var BarCollection = Backbone.Collection.extend({
            model: exports.Bar,
        });
        exports.Baz = Backbone.Model.extend({});
        return exports;
    });
    odoo.define('mod2', function (require) {
        var models = require('mod1');
        var _super_orderline = models.Bar.prototype;
        models.Foo = models.Bar.extend({});
        var _super_order = models.Baz.prototype;
        models.Bar = models.Baz.extend({});
    });
    """)

