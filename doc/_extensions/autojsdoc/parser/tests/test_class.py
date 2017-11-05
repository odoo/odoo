# -*- coding: utf-8 -*-
import pytest

from autojsdoc.parser import jsdoc
from support import params, parse

def test_classvar():
    [mod] = parse("""
    odoo.define('a.A', function(require) {
        var Class = require('Class');
        /**
         * This is my class-kai
         */
        var A = Class.extend({});
        return A;
    });
    """)
    cls = mod.exports
    assert type(cls) == jsdoc.ClassDoc

    assert type(cls.superclass) == jsdoc.ClassDoc
    assert cls.superclass.name == 'Class'

    assert cls.name == 'A'
    assert cls.constructor is None
    assert cls.properties == []
    assert cls['doc'] == 'This is my class-kai'

def test_classret():
    [mod] = parse("""
    odoo.define('a.A', function(require) {
        var Class = require('Class');
        /**
         * This is my class-kai
         */
        return Class.extend({});
    });
    """)
    cls = mod.exports
    assert type(cls) == jsdoc.ClassDoc

    assert cls.name == ''
    assert cls.constructor is None
    assert cls.properties == []
    assert cls['doc'] == 'This is my class-kai'

def test_methods():
    [mod] = parse("""
    odoo.define('a.A', function(require) {
        var Class = require('Class');
        return Class.extend({
            /**
             * @param {Widget} parent
             */
            init: function (parent) {},
            /**
             * @returns {Widget}
             */
            itself: function () { return this; },
            /**
             * @param {MouseEvent} e 
             */
            _onValidate: function (e) {},
        });
    });
    """)
    cls = mod.exports
    assert len(cls.properties) == 3
    assert cls.constructor
    # assume methods are in source order
    [_, init] = cls.properties[0]
    assert init == cls.constructor
    assert init.name == 'init'
    assert not init.is_private
    assert init.is_constructor
    [param] = init.params
    assert params(param) == ('parent', 'Widget', '')

    [_, itself] = cls.properties[1]
    assert itself.name == 'itself'
    assert not itself.is_private
    assert not itself.is_constructor
    assert not itself.params
    assert params(itself.return_val) == ('', 'Widget', '')

    [_, _on] = cls.properties[2]
    assert _on.name == '_onValidate'
    assert _on.is_private
    assert not _on.is_constructor
    [param] = _on.params
    assert params(param) == ('e', 'MouseEvent', '')

def test_mixin_explicit():
    [mod] = parse("""
    odoo.define('a.A', function (require) {
        var Class = require('Class');
        var mixins = require('mixins');
        /**
         * This is my class-kai
         * @mixes mixins.Bob
         */
        return Class.extend({});
    });
    """)
    cls = mod.exports
    # FIXME: ClassDoc may want to m2r(mixin, scope)?
    assert cls.mixins == ['mixins.Bob']

def test_mixin_implicit():
    [mod] = parse("""
    odoo.define('a.A', function(require) {
        var Class = require('Class');
        var Mixin = require('Mixin');
        /**
         * This is my class-kai
         */
        return Class.extend(Mixin, { foo: function() {} });
    });
    """)
    cls = mod.exports
    [mixin] = cls.mixins
    assert type(mixin) == jsdoc.MixinDoc
    assert params(mixin.properties[0][1]) == ('a', 'Function', '')
    assert params(mixin.get_property('a')) == ('a', 'Function', '')

    assert params(cls.get_property('foo')) == ('foo', 'Function', '')

def test_instanciation():
    [A, a] = parse("""
    odoo.define('A', function (r) {
        var Class = r('Class');
        /**
         * @class A
         */
        return Class.extend({
            foo: function () {}
        });
    });
    odoo.define('a', function (r) {
        var A = r('A');
        var a = new A;
        return a;
    });
    """)
    assert type(a.exports) == jsdoc.InstanceDoc
    assert a.exports.cls.name == A.exports.name

def test_non_function_properties():
    [A] = parse("""
    odoo.define('A', function (r) {
        var Class = r('Class');
        return Class.extend({
            template: 'thing',
            a_prop: [1, 2, 3],
            'other': {a: 7}
        });
    });
    """)
    t = A.exports.get_property('template')
    assert type(t) == jsdoc.PropertyDoc
    assert params(t) == ('template', 'String', '')
    assert not t.is_private

def test_non_extend_classes():
    [mod] = parse("""
    odoo.define('A', function () {
        /**
         * @class
         */
        var Class = function () {}
        return Class;
    });
    """)
    assert type(mod.exports) == jsdoc.ClassDoc

def test_extend():
    [a, _] = parse("""
    odoo.define('A', function (require) {
        var Class = require('Class');
        return Class.extend({});
    });
    odoo.define('B', function (require) {
        var A = require('A');
        A.include({
            /** A property */
            a: 3,
            /** A method */
            b: function () {}
        });
    });
    """)
    cls = a.exports
    assert type(cls) == jsdoc.ClassDoc
    a = cls.get_property('a')
    assert type(a) == jsdoc.PropertyDoc
    assert params(a) == ('a', 'Number', 'A property')
    b = cls.get_property('b')
    assert type(b) == jsdoc.FunctionDoc
    assert params(b) == ('b', 'Function', 'A method')

# TODO: also support virtual members?
# TODO: computed properties?
@pytest.mark.skip(reason="Need to implement member/var-parsing?")
def test_members():
    [mod] = parse("""
    odoo.define('A', function (r) {
        var Class = r('Class');
        return Class.extend({
            init: function () {
                /**
                 * This is bob
                 * @var {Foo}
                 */
                this.foo = 3;
                this.bar = 42;
                /**
                 * @member {Baz}
                 */
                this.baz = null;
            }
        });
    });
    """)
    cls = mod.exports
    assert params(cls.members[0]) == ('foo', 'Foo', 'This is bob')
    assert params(cls.members[1]) == ('bar', '', '')
    assert params(cls.members[2]) == ('baz', 'Baz', '')
