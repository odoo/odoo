$(document).ready(function () {
    var openerp;
    module('Registry', {
        setup: function () {
            openerp = window.openerp.init(true);
            window.openerp.web.core(openerp);
            openerp.web.Foo = {};
            openerp.web.Bar = {};
        }
    });
    test('key fetch', function () {
        var reg = new openerp.web.Registry({
            foo: 'openerp.web.Foo',
            bar: 'openerp.web.Bar',
            quux: 'openerp.web.Quux'
        });

        strictEqual(reg.get_object('foo'), openerp.web.Foo);
        raises(function () { reg.get_object('qux'); },
               openerp.web.KeyNotFound,
               "Unknown keys should raise KeyNotFound");
        raises(function () { reg.get_object('quux'); },
               openerp.web.ObjectNotFound,
               "Incorrect file paths should raise ObjectNotFound");
    });
    test('key set', function () {
        var reg = new openerp.web.Registry();

        reg.add('foo', 'openerp.web.Foo')
           .add('bar', 'openerp.web.Bar');
        strictEqual(reg.get_object('bar'), openerp.web.Bar);
    });
});
