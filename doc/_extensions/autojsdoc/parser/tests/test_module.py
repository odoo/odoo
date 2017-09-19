# -*- coding: utf-8 -*-

from autojsdoc.parser import jsdoc
from support import params, parse, BASE_MODULES


def test_single():
    [mod] = parse("""
    /**
     * This is a super module!
     */
    odoo.define('supermodule', function (req) {
        var other = req('other');
    });
    """)
    assert mod.name == 'supermodule'
    assert mod.dependencies == {'other'}
    assert mod.exports is None
    assert mod.doc == "This is a super module!"
    m = mod.get_property('other')
    assert m.name == 'value', "property is exported value not imported module"

def test_multiple():
    [mod1, mod2, mod3] = parse("""
    odoo.define('module1', function (req) {
        return 1;
    });
    odoo.define('module2', function (req) {
        return req('dep2');
    });
    odoo.define('module3', function (req) {
        var r = req('dep3');
        return r;
    });
    """)
    assert mod1.name == 'module1'
    assert mod1.dependencies == set()
    assert isinstance(mod1.exports, jsdoc.LiteralDoc)
    assert mod1.exports.value == 1.0
    assert mod1.exports['sourcemodule'] is mod1
    assert mod1.doc == ""

    assert mod2.name == 'module2'
    assert mod2.dependencies == {'dep2'}
    assert isinstance(mod2.exports, jsdoc.LiteralDoc)
    assert mod2.exports.value == 42.0
    assert mod2.doc == ""

    assert mod3.name == 'module3'
    assert mod3.dependencies == {'dep3'}
    assert isinstance(mod3.exports, jsdoc.LiteralDoc)
    assert mod3.exports.value == 56.0
    assert mod3.doc == ''

def test_func():
    [mod] = parse("""
    odoo.define('module', function (d) {
        /**
         * @param {Foo} bar this is a bar
         * @param {Baz} qux this is a qux
         */
        return function (bar, qux) {
            return 42;
        }
    });
    """)
    exports = mod.exports
    assert type(exports) == jsdoc.FunctionDoc
    assert exports['sourcemodule'] is mod

    assert exports.name == ''
    assert exports.is_constructor == False
    assert exports.is_private == False

    assert params(exports.params[0]) == ('bar', 'Foo', 'this is a bar')
    assert params(exports.params[1]) == ('qux', 'Baz', 'this is a qux')
    assert params(exports.return_val) == ('', '', '')

def test_hoist():
    [mod] = parse("""
    odoo.define('module', function() {
        return foo;
        /**
         * @param a_thing
         */
        function foo(a_thing) {
            return 42;
        }
    });
    """)
    actual = mod.exports
    assert type(actual) == jsdoc.FunctionDoc
    [param] = actual.params
    assert params(param) == ('a_thing', '', '')

def test_export_instance():
    [mod] = parse("""
    odoo.define('module', function (require) {
        var Class = require('Class');
        /**
         * Provides an instance of Class
         */
        return new Class();
    });
    """)
    assert type(mod.exports) == jsdoc.InstanceDoc
    assert mod.exports.doc == 'Provides an instance of Class'
    assert mod.exports['sourcemodule'] is mod

def test_bounce():
    [m2, m1] = parse("""
    odoo.define('m2', function (require) {
        var Item = require('m1');
        return {
            Item: Item
        };
    });
    odoo.define('m1', function (require) {
        var Class = require('Class');
        var Item = Class.extend({});
        return Item;
    });
    """)
    assert type(m2.exports) == jsdoc.NSDoc
    it = m2.exports.get_property('Item')
    assert type(it) == jsdoc.ClassDoc
    assert it['sourcemodule'] is m1
    assert sorted([n for n, _ in m1.properties]) == ['<exports>', 'Class', 'Item']

def test_reassign():
    [m] = parse("""
    odoo.define('m', function (require) {
        var Class = require('Class');
        /** local class */
        var Class = Class.extend({});
        return Class
    });
    """)
    assert m.exports.doc == 'local class'
    # can't use equality or identity so use class comment...
    assert m.exports.superclass.doc == 'Base Class'

def test_attr():
    [m1, m2] = parse("""
    odoo.define('m1', function (require) {
        var Class = require('Class');
        var Item = Class.extend({});
        return {Item: Item};
    });
    odoo.define('m2', function (require) {
        var Item = require('m1').Item;
        Item.include({});
        return Item.extend({});
    });
    """)
    assert type(m2.exports) == jsdoc.ClassDoc
    # that these two are resolved separately may be an issue at one point (?)
    assert m2.exports.superclass.to_dict() == m1.exports.get_property('Item').to_dict()

def test_nothing_implicit():
    [m] = parse("""
    odoo.define('m', function () {
    });
    """)
    assert m.exports is None

def test_nothing_explicit():
    [m] = parse("""
    odoo.define('m', function () {
        return;
    });
    """)
    assert m.exports is None
