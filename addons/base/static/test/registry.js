$(document).ready(function () {
    var openerp;
    module('Registry', {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.base.core(openerp);
            openerp.base.Foo = {};
            openerp.base.Bar = {};
        }
    });
    test('key fetch', function () {
        var reg = new openerp.base.Registry({
            foo: 'openerp.base.Foo',
            bar: 'openerp.base.Bar',
            quux: 'openerp.base.Quux'
        });

        strictEqual(reg.get_object('foo'), openerp.base.Foo);
        raises(function () { reg.get_object('qux'); },
               openerp.base.KeyNotFound,
               "Unknown keys should raise KeyNotFound");
        raises(function () { reg.get_object('quux'); },
               openerp.base.ObjectNotFound,
               "Incorrect file paths should raise ObjectNotFound");
    });
    test('key set', function () {
        var reg = new openerp.base.Registry();

        reg.add('foo', 'openerp.base.Foo')
           .add('bar', 'openerp.base.Bar');
        strictEqual(reg.get_object('bar'), openerp.base.Bar);
    });
});
