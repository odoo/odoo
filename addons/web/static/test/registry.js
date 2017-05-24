odoo.define_section('web.registry', ['web.Registry'], {
    beforeEach: function () {
        this.Foo = {bar: 1};
        this.Bar = {foo: 0};
        this.Foo2 = {fred: -1};
    },
}, function (test) {

    test('key set', function (assert, Registry) {
        var registry = new Registry();

        registry
            .add('foo', this.Foo)
            .add('bar', this.Bar);

        assert.strictEqual(registry.get('foo'), this.Foo);
        // make sure we're comparing actual objects instead of just undefineds
        assert.deepEqual(registry.get('foo'), {bar: 1});
    });

    test('extension', function (assert, Registry) {
        var registry = new Registry({
            foo: this.Foo,
            bar: this.Bar,
        });
        var registry2 = registry.extend({foo: this.Foo2});
        assert.strictEqual(registry.get('foo'), this.Foo);
        assert.strictEqual(registry2.get('foo'), this.Foo2);
    });

    test('remain-linked', function (assert, Registry) {
        var registry = new Registry({
            foo: this.Foo,
            bar: this.Bar,
        });
        var registry2 = registry.extend();

        registry.add('foo2', this.Foo2);

        assert.strictEqual(registry.get('foo2'), this.Foo2);
        assert.strictEqual(registry2.get('foo2'), this.Foo2);
    });

    test('multiget', function (assert, Registry) {
        var registry = new Registry({
            foo: this.Foo,
            bar: this.Bar,
        });
        assert.strictEqual(
            registry.get_any(['qux', 'grault', 'bar', 'foo']), 
            this.Bar,
            "Registry get_any should find first defined key");
    });

    test('extended-multiget', function (assert, Registry) {
        var registry = new Registry({
            foo: this.Foo,
            bar: this.Bar,
        });
        var registry2 = registry.extend();
        assert.strictEqual(registry2.get_any(['qux', 'grault', 'bar', 'foo']), this.Bar);
    });
});

