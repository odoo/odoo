# -*- coding: utf-8 -*-
from autojsdoc.parser import jsdoc
from support import parse, params


def test_empty():
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        return {};
    });
    """)
    assert type(mod.exports) == jsdoc.NSDoc
    assert mod.exports.properties == []

def test_inline():
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        return {
            /**
             * a thing
             * @type {Boolean} 
             */
            a: true
        }
    });
    """)
    assert isinstance(mod.exports, jsdoc.NSDoc)
    [(n, p)] = mod.exports.properties
    assert n == 'a'
    assert params(p) == ('a', 'Boolean', 'a thing')

def test_header():
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        /**
         * @property {Boolean} a a thing
         */
        return { a: true }
    });
    """)
    assert isinstance(mod.exports, jsdoc.NSDoc)
    [(_, p)] = mod.exports.properties
    assert params(p) == ('a', 'Boolean', 'a thing')

def test_header_conflict():
    """ should the header or the inline comment take precedence? """
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        /**
         * @property {Boolean} a a thing
         */
        return {
            /** @type {String} */
            a: true
        }
    });
    """)
    assert isinstance(mod.exports, jsdoc.NSDoc)
    [(_, p)] = mod.exports.properties
    assert params(p) == ('a', 'Boolean', 'a thing')

def test_mixin():
    [mod] = parse("""
    odoo.define('a.mixin', function (r) {
        /**
         * @mixin
         */
        return {
            /**
             * @returns {Number} a number
             */
            do_thing: function other() { return 42; }
        }
    });
    """)
    assert isinstance(mod.exports, jsdoc.MixinDoc)
    [(n, p)] = mod.exports.properties
    assert n == 'do_thing'
    assert params(p) == ('other', 'Function', '')
    assert params(p.return_val) == ('', 'Number', 'a number')

def test_literal():
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        /** whop whop */
        return {
            'a': 1,
            /** wheee */
            'b': 2,
        };
    });
    """)
    assert mod.exports.doc == 'whop whop'
    [(_1, a), (_2, b)] = mod.exports.properties
    assert params(a) == ('a', 'Number', '')
    assert params(b) == ('b', 'Number', 'wheee')

def test_fill_ns():
    [mod] = parse("""
    odoo.define('a.ns', function (r) {
        var Class = r('Class');
        var ns = {};
        /** ok */
        ns.a = 1;
        /** @type {String} */
        ns['b'] = 2;
        /** Ike */
        ns.c = Class.extend({});
        ns.d = function () {}
        return ns;
    });
    """)
    ns = mod.exports
    assert type(ns) == jsdoc.NSDoc
    [(_a, a), (_b, b), (_c, c), (_d, d)] = ns.properties
    assert params(a) == ('a', 'Number', 'ok')
    assert params(b) == ('b', 'String', '')
    assert type(c) == jsdoc.ClassDoc
    assert type(d) == jsdoc.FunctionDoc

def test_extend_other():
    [o, b] = parse("""
    odoo.define('a.ns', function () {
        /** @name outer */
        return {
            /** @name inner */
            a: {}
        };
    });
    odoo.define('b', function (r) {
        var o = r('a.ns');
        var Class = r('Class');
        /** Class 1 */
        o.a.b = Class.extend({m_b: 1});
        /** Class 2 */
        o.a['c'] = Class.extend({m_c: 1});
    });
    """)
    [(_, m)] = o.exports.properties
    assert type(m) == jsdoc.NSDoc

    b = m.get_property('b')
    assert type(b) == jsdoc.ClassDoc
    assert b.get_property('m_b')
    assert b.doc == 'Class 1'

    c = m.get_property('c')
    assert type(c) == jsdoc.ClassDoc
    assert c.get_property('m_c')
    assert c.doc == 'Class 2'

def test_ns_variables():
    [mod] = parse("""
    odoo.define('A', function (r) {
        var Class = r('Class');
        var Thing = Class.extend({});
        return {
            Thing: Thing
        };
    });
    """)
    p = mod.exports.get_property('Thing')
    assert type(p) == jsdoc.ClassDoc

def test_diff():
    """ Have the NS key and the underlying object differ
    """
    [mod] = parse("""
    odoo.define('mod', function (r) {
        var Class = r('Class');
        var Foo = Class.extend({});
        return { Class: Foo };
    });
    """)
    c = mod.exports.get_property('Class')
    assert type(c) == jsdoc.ClassDoc
    assert c.name == 'Foo'
