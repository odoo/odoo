openerp.testing.section('registry', {
    dependencies: ['web.corelib'],
    setup: function (instance) {
        instance.web.Foo = {};
        instance.web.Bar = {};
        instance.web.Foo2 = {};
    }
}, function (test) {
    test('key set', function (instance) {
        var reg = new instance.web.Registry();

        reg.add('foo', 'instance.web.Foo')
           .add('bar', 'instance.web.Bar');
        strictEqual(reg.get_object('bar'), instance.web.Bar);
    });
    test('extension', function (instance) {
        var reg = new instance.web.Registry({
            foo: 'instance.web.Foo',
            bar: 'instance.web.Bar'
        });

        var reg2 = reg.extend({ 'foo': 'instance.web.Foo2' });
        strictEqual(reg.get_object('foo'), instance.web.Foo);
        strictEqual(reg2.get_object('foo'), instance.web.Foo2);
    });
    test('remain-linked', function (instance) {
        var reg = new instance.web.Registry({
            foo: 'instance.web.Foo',
            bar: 'instance.web.Bar'
        });

        var reg2 = reg.extend();
        reg.add('foo2', 'instance.web.Foo2');
        strictEqual(reg.get_object('foo2'), instance.web.Foo2);
        strictEqual(reg2.get_object('foo2'), instance.web.Foo2);
    });
    test('multiget', function (instance) {
        var reg = new instance.web.Registry({
            foo: 'instance.web.Foo',
            bar: 'instance.web.Bar'
        });

        strictEqual(reg.get_any(['qux', 'grault', 'bar', 'foo']),
                    instance.web.Bar);
    });
    test('extended-multiget', function (instance) {
        var reg = new instance.web.Registry({
            foo: 'instance.web.Foo',
            bar: 'instance.web.Bar'
        });
        var reg2 = reg.extend();
        strictEqual(reg2.get_any(['qux', 'grault', 'bar', 'foo']),
                    instance.web.Bar);
    });
});
