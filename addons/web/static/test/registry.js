$(document).ready(function () {
    var openerp;
    module('Registry', {
        setup: function () {
            openerp = window.openerp.init([]);
            window.openerp.web.corelib(openerp);
            openerp.web.Foo = {};
            openerp.web.Bar = {};
            openerp.web.Foo2 = {};
        }
    });
    test('key set', function () {
        var reg = new openerp.web.Registry();

        reg.add('foo', 'openerp.web.Foo')
           .add('bar', 'openerp.web.Bar');
        strictEqual(reg.get_object('bar'), openerp.web.Bar);
    });
    test('extension', function () {
        var reg = new openerp.web.Registry({
            foo: 'openerp.web.Foo',
            bar: 'openerp.web.Bar'
        });

        var reg2 = reg.extend({ 'foo': 'openerp.web.Foo2' });
        strictEqual(reg.get_object('foo'), openerp.web.Foo);
        strictEqual(reg2.get_object('foo'), openerp.web.Foo2);
    });
    test('remain-linked', function () {
        var reg = new openerp.web.Registry({
            foo: 'openerp.web.Foo',
            bar: 'openerp.web.Bar'
        });

        var reg2 = reg.extend();
        reg.add('foo2', 'openerp.web.Foo2');
        strictEqual(reg.get_object('foo2'), openerp.web.Foo2);
        strictEqual(reg2.get_object('foo2'), openerp.web.Foo2);
    });
    test('multiget', function () {
        var reg = new openerp.web.Registry({
            foo: 'openerp.web.Foo',
            bar: 'openerp.web.Bar'
        });

        strictEqual(reg.get_any(['qux', 'grault', 'bar', 'foo']),
                    openerp.web.Bar);
    });
    test('extended-multiget', function () {
        var reg = new openerp.web.Registry({
            foo: 'openerp.web.Foo',
            bar: 'openerp.web.Bar'
        });
        var reg2 = reg.extend();
        strictEqual(reg2.get_any(['qux', 'grault', 'bar', 'foo']),
                    openerp.web.Bar);
    });
});
