
odoo.define_section('basic section', [], function (test, mock) {
    test('my first test', function (assert) {
        assert.ok(true, "this test has run");
    });

    test('module content', ['web_tests_demo.demo'], function (assert, tests_demo) {
        assert.ok(tests_demo.value_true, "should have a true value");
        var type_instance = new tests_demo.SomeType(42);
        assert.strictEqual(type_instance.value, 42, "should have provided value");
    });

    test('DOM content', function (assert) {
        var $fix = $( "#qunit-fixture");
        $fix.html('<div><span class="foo bar">ok</span></div>');
        assert.ok($fix.find('span').hasClass('foo'),
           "should have provided class");
    });

    test('clean fixture', function (assert) {
        var $fix = $( "#qunit-fixture");
        assert.ok(!$fix.children().length, "should have no content");
        assert.ok(!$fix.text(), "should have no text");
    });

    test('templates', ['web.core'], function (assert, core) {
        var s = core.qweb.render('DemoTemplate');
        var texts = $(s).find('p').map(function () {
            return $(this).text();
        }).get();

        assert.deepEqual(texts, ['0', '1', '2', '3', '4']);
    });

    test('asynchronous', function (assert) {
        assert.expect(1);

        var d = $.Deferred();
        setTimeout(function () {
            assert.ok(true);
            d.resolve();
        }, 100);
        return d;
    });


    test('XML-RPC', ['web.DataModel'], function (assert, Model) {
        assert.expect(3);

        mock.add('people.famous:name_search', function (args, kwargs) {
            assert.strictEqual(kwargs.name, 'bob');
            return [
                [1, "Microsoft Bob"],
                [2, "Bob the Builder"],
                [3, "Silent Bob"]
            ];
        });
        return new Model('people.famous')
            .call('name_search', {name: 'bob'}).then(function (result) {
                assert.strictEqual(result.length, 3, "shoud return 3 people");
                assert.strictEqual(result[0][1], "Microsoft Bob",
                    "the most famous bob should be Microsoft Bob");
            });
    });

});
