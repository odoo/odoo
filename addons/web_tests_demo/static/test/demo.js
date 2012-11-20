openerp.testing.section('basic section', function (test) {
    test('my first test', function () {
        ok(true, "this test has run");
    });
    test('module content', function (instance) {
        ok(instance.web_tests_demo.value_true, "should have a true value");
        var type_instance = new instance.web_tests_demo.SomeType(42);
        strictEqual(type_instance.value, 42, "should have provided value");
    });
    test('DOM content', function (instance, $scratchpad) {
        $scratchpad.html('<div><span class="foo bar">ok</span></div>');
        ok($scratchpad.find('span').hasClass('foo'),
           "should have provided class");
    });
    test('clean scratchpad', function (instance, $scratchpad) {
        ok(!$scratchpad.children().length, "should have no content");
        ok(!$scratchpad.text(), "should have no text");
    });

    test('templates', {templates: true}, function (instance) {
        var s = instance.web.qweb.render('DemoTemplate');
        var texts = $(s).find('p').map(function () {
            return $(this).text();
        }).get();

        deepEqual(texts, ['0', '1', '2', '3', '4']);
    });

    test('asynchronous', {
        asserts: 1
    }, function () {
        var d = $.Deferred();
        setTimeout(function () {
            ok(true);
            d.resolve();
        }, 100);
        return d;
    });
    test('unfail rejection', {
        asserts: 1,
        fail_on_rejection: false
    }, function () {
        var d = $.Deferred();
        setTimeout(function () {
            ok(true);
            d.reject();
        }, 100);
        return d;
    });

    test('XML-RPC', {rpc: 'mock', asserts: 3}, function (instance, $s, mock) {
        mock('people.famous:name_search', function (args, kwargs) {
            strictEqual(kwargs.name, 'bob');
            return [
                [1, "Microsoft Bob"],
                [2, "Bob the Builder"],
                [3, "Silent Bob"]
            ];
        });
        return new instance.web.Model('people.famous')
            .call('name_search', {name: 'bob'}).then(function (result) {
                strictEqual(result.length, 3, "shoud return 3 people");
                strictEqual(result[0][1], "Microsoft Bob",
                    "the most famous bob should be Microsoft Bob");
            });
    });
    test('JSON-RPC', {rpc: 'mock', asserts: 3, templates: true}, function (instance, $s, mock) {
        var fetched_dbs = false, fetched_langs = false;
        mock('/web/database/get_list', function () {
            fetched_dbs = true;
            return ['foo', 'bar', 'baz'];
        });
        mock('/web/session/get_lang_list', function () {
            fetched_langs = true;
            return [['vo_IS', 'Hopelandic / Vonlenska']];
        });

        // widget needs that or it blows up
        instance.webclient = {toggle_bars: openerp.testing.noop};
        var dbm = new instance.web.DatabaseManager({});
        return dbm.appendTo($s).then(function () {
            ok(fetched_dbs, "should have fetched databases");
            ok(fetched_langs, "should have fetched languages");
            deepEqual(dbm.db_list, ['foo', 'bar', 'baz']);
        });
    });

    test('actual RPC', {rpc: 'rpc', asserts: 4}, function (instance) {
        var Model = new instance.web.Model('web_tests_demo.model');
        return Model.call('create', [{name: "Bob"}])
            .then(function (id) {
                return Model.call('read', [[id]]);
            }).then(function (records) {
                strictEqual(records.length, 1);
                var record = records[0];
                strictEqual(record.name, "Bob");
                strictEqual(record.thing, false);
                // default value
                strictEqual(record.other, 'bob');
            });
    });
});
