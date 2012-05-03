$(document).ready(function () {
    var xhr = QWeb2.Engine.prototype.get_xhr();
    xhr.open('GET', '/web/static/src/xml/base.xml', false);
    xhr.send(null);
    var doc = xhr.responseXML;

    var noop = function () {};
    /**
     * Make connection RPC responses mockable by setting keys on the
     * Connection#responses object (key is the URL, value is the function to
     * call with the RPC request payload)
     *
     * @param {openerp.web.Connection} connection connection instance to mockify
     * @param {Object} [responses] url:function mapping to seed the mock connection
     */
    var mockifyRPC = function (connection, responses) {
        connection.responses = responses || {};
        connection.rpc_function = function (url, payload) {
            if (!(url.url in this.responses)) {
                return $.Deferred().reject({}, 'failed', _.str.sprintf("Url %s not found in mock responses", url.url)).promise();
            }
            return $.when(this.responses[url.url](payload));
        };
    };

    var instance;
    module('query', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            window.openerp.web.search(instance);
        }
    });
    test('Adding a facet to the query creates a facet and a value', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {};
        query.add({
            category: 'Foo',
            field: field,
            values: [{label: 'Value', value: 3}]
        });

        var facet = query.at(0);
        equal(facet.get('category'), 'Foo');
        equal(facet.get('field'), field);
        deepEqual(facet.get('values'), [{label: 'Value', value: 3}]);
    });
    test('Adding two facets', function () {
        var query = new instance.web.search.SearchQuery;
        query.add([
            { category: 'Foo', field: {}, values: [{label: 'Value', value: 3}] },
            { category: 'Bar', field: {}, values: [{label: 'Value 2', value: 4}] }
        ]);

        equal(query.length, 2);
        equal(query.at(0).values.length, 1);
        equal(query.at(1).values.length, 1);
    });
    test('If a facet already exists, add values to it', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {};
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        equal(query.length, 1, "adding an existing facet should merge new values into old facet");
        var facet = query.at(0);
        deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });
    test('Facet being implicitly changed should trigger change, not add', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {}, added = false, changed = false;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.on('add', function () { added = true; })
             .on('change', function () { changed = true });
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        ok(!added, "query.add adding values to a facet should not trigger an add");
        ok(changed, "query.add adding values to a facet should not trigger a change");
    });
    test('Toggling a facet, value which does not exist should add it', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {};
        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        equal(query.length, 1, "Should have created a single facet");
        var facet = query.at(0);
        equal(facet.values.length, 1, "Facet should have a single value");
        deepEqual(facet.get('values'), [{label: 'V1', value: 0}],
                  "Facet's value should match input");
    });
    test('Toggling a facet which exists with a value which does not should add the value to the facet', function () {
        var field = {};
        var query = new instance.web.search.SearchQuery;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        equal(query.length, 1, "Should have edited the existing facet");
        var facet = query.at(0);
        equal(facet.values.length, 2, "Should have added the value to the existing facet");
        deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });
    test('Toggling a facet which exists with a value which does as well should remove the value from the facet', function () {
        var field = {};
        var query = new instance.web.search.SearchQuery;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        equal(query.length, 1, 'Should have the same single facet');
        var facet = query.at(0);
        equal(facet.values.length, 1, "Should only have one value left in the facet");
        deepEqual(facet.get('values'), [
            {label: 'V1', value: 0}
        ]);
    });
    test('Toggling off the last value of a facet should remove the facet', function () {
        var field = {};
        var query = new instance.web.search.SearchQuery;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        equal(query.length, 0, 'Should have removed the facet');
    });
    test('Intermediate emptiness should not remove the facet', function () {
        var field = {};
        var query = new instance.web.search.SearchQuery;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]});

        equal(query.length, 1, 'Should not have removed the facet');
        var facet = query.at(0);
        equal(facet.values.length, 1, "Should have one value");
        deepEqual(facet.get('values'), [
            {label: 'V2', value: 1}
        ]);
    });

    test('Reseting with multiple facets should still work to load defaults', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {};
        query.reset([
            {category: 'A', field: field, values: [{label: 'V1', value: 0}]},
            {category: 'A', field: field, values: [{label: 'V2', value: 1}]}]);

        equal(query.length, 1, 'Should have created a single facet');
        equal(query.at(0).values.length, 2, 'the facet should have merged two values');
        deepEqual(query.at(0).get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ])
    });

    module('defaults', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            window.openerp.web.search(instance);

            instance.web.qweb.add_template(doc);

            mockifyRPC(instance.connection);
        }
    });

    /**
     * Builds a basic search view with a single "dummy" field. The dummy
     * extends `instance.web.search.Field`, it does not add any (class)
     * attributes beyond what is provided through ``dummy_widget_attributes``.
     *
     * The view is returned un-started, it is the caller's role to start it
     * (or use DOM-insertion methods to start it indirectly).
     *
     * @param [dummy_widget_attributes={}]
     * @param [defaults={}]
     * @return {instance.web.SearchView}
     */
    function makeSearchView(dummy_widget_attributes, defaults) {
        instance.web.search.fields.add(
            'dummy', 'instance.dummy.DummyWidget');
        instance.dummy = {};
        instance.dummy.DummyWidget = instance.web.search.Field.extend(
            dummy_widget_attributes || {});
        if (!('/web/searchview/load' in instance.connection.responses)) {
            instance.connection.responses['/web/searchview/load'] = function () {
                return {result: {fields_view: {
                    type: 'search',
                    fields: {
                        dummy: {type: 'char'}
                    },
                    arch: {
                        tag: 'search',
                        attrs: {},
                        children: [{
                            tag: 'field',
                            attrs: {
                                name: 'dummy',
                                widget: 'dummy'
                            },
                            children: []
                        }]
                    }
                }}};
            };
        }
        instance.connection.responses['/web/searchview/get_filters'] = function () {
            return {result: []};
        };
        instance.connection.responses['/web/searchview/fields_get'] = function () {
            return {result: {fields: {
                dummy: {type: 'char'}
            }}};
        };

        var dataset = {model: 'dummy.model', get_context: function () { return {}; }};
        var view = new instance.web.SearchView(null, dataset, false, defaults);
        view.on_invalid.add(function () {
            ok(false, JSON.stringify([].slice(arguments)));
        });
        return view;
    }
    asyncTest('calling', 2, function () {
        var defaults_called = false;

        var view = makeSearchView({
            facet_for_defaults: function (defaults) {
                defaults_called = true;
                return $.when({
                    field: this,
                    category: 'Dummy',
                    values: [{label: 'dummy', value: defaults.dummy}]
                });
            }
        }, {dummy: 42});
        view.appendTo($('#qunit-fixture'))
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                ok(defaults_called, "should have called defaults");
                deepEqual(
                    view.query.toJSON(),
                    [{category: 'Dummy', values: [{label: 'dummy', value: 42}]}],
                    "should have generated a facet with the default value");
            });
    });
    asyncTest('FilterGroup', 3, function () {
        var view = {inputs: []};
        var filter_a = new instance.web.search.Filter(
            {attrs: {name: 'a'}}, view);
        var filter_b = new instance.web.search.Filter(
            {attrs: {name: 'b'}}, view);
        var group = new instance.web.search.FilterGroup(
            [filter_a, filter_b], view);
        group.facet_for_defaults({a: true, b: true})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof instance.web.search.Facet)) {
                    model = new instance.web.search.Facet(facet);
                }
                var values = model.values;
                equal(values.length, 2, 'facet should have two values');
                strictEqual(values.at(0).get('value'), filter_a);
                strictEqual(values.at(1).get('value'), filter_b);
            });
    });
    asyncTest('Field', 4, function () {
        var view = {inputs: []};
        var f = new instance.web.search.Field(
            {attrs: {string: 'Dummy', name: 'dummy'}}, {}, view);
        f.facet_for_defaults({dummy: 42})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof instance.web.search.Facet)) {
                    model = new instance.web.search.Facet(facet);
                }
                strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                equal(model.values.length, 1, "facet should have a single value");
                deepEqual(
                    model.values.toJSON(),
                    [{label: '42', value: 42}],
                    "facet value should match provided default");
                });
    });
    asyncTest('Selection: valid value', 4, function () {
        var view = {inputs: []};
        var f = new instance.web.search.SelectionField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Qux"]]},
            view);
        f.facet_for_defaults({dummy: 3})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof instance.web.search.Facet)) {
                    model = new instance.web.search.Facet(facet);
                }
                strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                equal(model.values.length, 1, "facet should have a single value");
                deepEqual(
                    model.values.toJSON(),
                    [{label: 'Baz', value: 3}],
                    "facet value should match provided default's selection");
            });
    });
    asyncTest('Selection: invalid value', 1, function () {
        var view = {inputs: []};
        var f = new instance.web.search.SelectionField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Qux"]]},
            view);
        f.facet_for_defaults({dummy: 42})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                ok(!facet, "an invalid value should result in a not-facet");
            });
    });
    asyncTest("M2O default: value", 7, function () {
        var view = {inputs: []}, id = 4;
        var f = new instance.web.search.ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        instance.connection.responses['/web/dataset/call_kw'] = function (req) {
            equal(req.params.method, 'name_get',
                  "m2o should resolve default id");
            equal(req.params.model, f.attrs.relation,
                  "query model should match m2o relation");
            equal(req.params.args[0], id);
            return {result: [[id, "DumDumDum"]]};
        };
        f.facet_for_defaults({dummy: id})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof instance.web.search.Facet)) {
                    model = new instance.web.search.Facet(facet);
                }
                strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                equal(model.values.length, 1, "facet should have a single value");
                deepEqual(
                    model.values.toJSON(),
                    [{label: 'DumDumDum', value: id}],
                    "facet value should match provided default's selection");
            });
    });
    asyncTest("M2O default: value", 1, function () {
        var view = {inputs: []}, id = 4;
        var f = new instance.web.search.ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        instance.connection.responses['/web/dataset/call_kw'] = function (req) {
           return {result: []};
        };
        f.facet_for_defaults({dummy: id})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                ok(!facet, "an invalid m2o default should yield a non-facet");
            });
    });

    module('completions', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            // date complete
            window.openerp.web.formats(instance);
            window.openerp.web.search(instance);

            instance.web.qweb.add_template(doc);

            mockifyRPC(instance.connection);
        }
    });
    asyncTest('calling', 4, function () {
        var view = makeSearchView({
            complete: function () {
                return $.when({
                    label: "Dummy",
                    facet: {
                        field: this,
                        category: 'Dummy',
                        values: [{label: 'dummy', value: 42}]
                    }
                });
            }
        });
        view.appendTo($('#qunit-fixture'))
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                stop();
                view.complete_global_search({term: "dum"}, function (completions) {
                    start();
                    equal(completions.length, 1, "should have a single completion");
                    var completion = completions[0];
                    equal(completion.label, "Dummy",
                          "should have provided label");
                    equal(completion.facet.category, "Dummy",
                          "should have provided category");
                    deepEqual(completion.facet.values,
                              [{label: 'dummy', value: 42}],
                              "should have provided values");
                });
            });
    });
    asyncTest('facet selection', 2, function () {
        var completion = {
            label: "Dummy",
            facet: {
                field: {get_domain: noop, get_context: noop, get_groupby: noop},
                category: 'Dummy',
                values: [{label: 'dummy', value: 42}]
            }
        };

        var view = makeSearchView({});
        view.appendTo($('#qunit-fixture'))
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                view.select_completion(
                    {preventDefault: function () {}},
                    {item: completion});
                equal(view.query.length, 1, "should have one facet in the query");
                deepEqual(
                    view.query.at(0).toJSON(),
                    {category: 'Dummy', values: [{label: 'dummy', value: 42}]},
                    "should have the right facet in the query");
            });
    });
    asyncTest('facet selection: new value existing facet', 3, function () {
        var field = {get_domain: noop, get_context: noop, get_groupby: noop};
        var completion = {
            label: "Dummy",
            facet: {
                field: field,
                category: 'Dummy',
                values: [{label: 'dummy', value: 42}]
            }
        };

        var view = makeSearchView({});
        view.appendTo($('#qunit-fixture'))
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                view.query.add({field: field, category: 'Dummy',
                                values: [{label: 'previous', value: 41}]});
                equal(view.query.length, 1, 'should have newly added facet');
                view.select_completion(
                    {preventDefault: function () {}},
                    {item: completion});
                equal(view.query.length, 1, "should still have only one facet");
                var facet = view.query.at(0);
                deepEqual(
                    facet.get('values'),
                    [{label: 'previous', value: 41}, {label: 'dummy', value: 42}],
                    "should have added selected value to old one");
            });
    });
    asyncTest('Field', 1, function () {
        var view = {inputs: []};
        var f = new instance.web.search.Field({attrs: {}}, {}, view);
        f.complete('foo')
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (completions) {
                ok(_(completions).isEmpty(), "field should not provide any completion");
            });
    });
    asyncTest('CharField', 6, function () {
        var view = {inputs: []};
        var f = new instance.web.search.CharField(
            {attrs: {string: "Dummy"}}, {}, view);
        f.complete('foo<')
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (completions) {
                equal(completions.length, 1, "should provide a single completion");
                var c = completions[0];
                equal(c.label, "Search <em>Dummy</em> for: <strong>foo&lt;</strong>",
                      "should propose a fuzzy matching/searching, with the" +
                      " value escaped");
                ok(c.facet, "completion should contain a facet proposition");
                var facet = new instance.web.search.Facet(c.facet);
                equal(facet.get('category'), f.attrs.string,
                      "completion facet should bear the field's name");
                strictEqual(facet.get('field'), f,
                            "completion facet should yield the field");
                deepEqual(facet.values.toJSON(), [{label: 'foo<', value: 'foo<'}],
                          "facet should have single value using completion item");
            });
    });
    asyncTest('Selection: match found', 14, function () {
        var view = {inputs: []};
        var f = new instance.web.search.SelectionField(
            {attrs: {string: "Dummy"}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Bazador"]]},
            view);
        f.complete("ba")
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (completions) {
                equal(completions.length, 4,
                    "should provide two completions and a section title");
                deepEqual(completions[0], {label: "Dummy"});

                var c1 = completions[1];
                equal(c1.label, "Bar");
                equal(c1.facet.category, f.attrs.string);
                strictEqual(c1.facet.field, f);
                deepEqual(c1.facet.values, [{label: "Bar", value: 2}]);

                var c2 = completions[2];
                equal(c2.label, "Baz");
                equal(c2.facet.category, f.attrs.string);
                strictEqual(c2.facet.field, f);
                deepEqual(c2.facet.values, [{label: "Baz", value: 3}]);

                var c3 = completions[3];
                equal(c3.label, "Bazador");
                equal(c3.facet.category, f.attrs.string);
                strictEqual(c3.facet.field, f);
                deepEqual(c3.facet.values, [{label: "Bazador", value: 4}]);
            });
    });
    asyncTest('Selection: no match', 1, function () {
        var view = {inputs: []};
        var f = new instance.web.search.SelectionField(
            {attrs: {string: "Dummy"}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Bazador"]]},
            view);
        f.complete("qux")
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (completions) {
                ok(!completions, "if no value matches the needle, no completion shall be provided");
            });
    });
    asyncTest('Date', 6, function () {
        instance.web._t.database.parameters = {
            date_format: '%Y-%m-%d',
            time_format: '%H:%M:%S'
        };
        var view = {inputs: []};
        var f = new instance.web.search.DateField(
            {attrs: {string: "Dummy"}}, {type: 'datetime'}, view);
        f.complete('2012-05-21T21:21:21')
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (completions) {
                equal(completions.length, 1, "should provide a single completion");
                var c = completions[0];
                equal(c.label, "Search <em>Dummy</em> at: <strong>2012-05-21 21:21:21</strong>");
                var facet = new instance.web.search.Facet(c.facet);
                equal(facet.get('category'), f.attrs.string);
                equal(facet.get('field'), f);
                var value = facet.values.at(0);
                equal(value.get('label'), "2012-05-21 21:21:21");
                equal(value.get('value').getTime(),
                      new Date(2012, 4, 21, 21, 21, 21).getTime());
            });
    });
    asyncTest("M2O", 15, function () {
        instance.connection.responses['/web/dataset/call_kw'] = function (req) {
            equal(req.params.method, "name_search");
            equal(req.params.model, "dummy.model");
            deepEqual(req.params.args, []);
            deepEqual(req.params.kwargs.name, 'bob');
            return {result: [[42, "choice 1"], [43, "choice @"]]}
        };

        var view = {inputs: []};
        var f = new instance.web.search.ManyToOneField(
            {attrs: {string: 'Dummy'}}, {relation: 'dummy.model'}, view);
        f.complete("bob")
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (c) {
                equal(c.length, 3, "should return results + title");
                var title = c[0];
                equal(title.label, f.attrs.string, "title should match field name");
                ok(!title.facet, "title should not have a facet");

                var f1 = new instance.web.search.Facet(c[1].facet);
                equal(c[1].label, "choice 1");
                equal(f1.get('category'), f.attrs.string);
                equal(f1.get('field'), f);
                deepEqual(f1.values.toJSON(), [{label: 'choice 1', value: 42}]);

                var f2 = new instance.web.search.Facet(c[2].facet);
                equal(c[2].label, "choice @");
                equal(f2.get('category'), f.attrs.string);
                equal(f2.get('field'), f);
                deepEqual(f2.values.toJSON(), [{label: 'choice @', value: 43}]);
            });
    });
    asyncTest("M2O no match", 5, function () {
        instance.connection.responses['/web/dataset/call_kw'] = function (req) {
            equal(req.params.method, "name_search");
            equal(req.params.model, "dummy.model");
            deepEqual(req.params.args, []);
            deepEqual(req.params.kwargs.name, 'bob');
            return {result: []}
        };
        var view = {inputs: []};
        var f = new instance.web.search.ManyToOneField(
            {attrs: {string: 'Dummy'}}, {relation: 'dummy.model'}, view);
        f.complete("bob")
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function (c) {
                ok(!c, "no match should yield no completion");
            });
    });

    module('search-serialization', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            window.openerp.web.search(instance);

            instance.web.qweb.add_template(doc);

            mockifyRPC(instance.connection);
        }
    });
    asyncTest('No facet, no call', 6, function () {
        var got_domain = false, got_context = false, got_groupby = false;
        var $fix = $('#qunit-fixture');
        var view = makeSearchView({
            get_domain: function () {
                got_domain = true;
                return null;
            },
            get_context: function () {
                got_context = true;
                return null;
            },
            get_groupby: function () {
                got_groupby = true;
                return null;
            }
        });
        var ds, cs, gs;
        view.on_search.add(function (d, c, g) {
            ds = d, cs = c, gs = g;
        });
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                view.do_search();
                ok(!got_domain, "no facet, should not have fetched domain");
                ok(_(ds).isEmpty(), "domains list should be empty");

                ok(!got_context, "no facet, should not have fetched context");
                ok(_(cs).isEmpty(), "contexts list should be empty");

                ok(!got_groupby, "no facet, should not have fetched groupby");
                ok(_(gs).isEmpty(), "groupby list should be empty");
            })
    });
    asyncTest('London, calling', 8, function () {
        var got_domain = false, got_context = false, got_groupby = false;
        var $fix = $('#qunit-fixture');
        var view = makeSearchView({
            get_domain: function (facet) {
                equal(facet.get('category'), "dummy");
                deepEqual(facet.values.toJSON(), [{label: "42", value: 42}]);
                got_domain = true;
                return null;
            },
            get_context: function () {
                got_context = true;
                return null;
            },
            get_groupby: function () {
                got_groupby = true;
                return null;
            }
        }, {dummy: 42});
        var ds, cs, gs;
        view.on_search.add(function (d, c, g) {
            ds = d, cs = c, gs = g;
        });
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                view.do_search();
                ok(got_domain, "should have fetched domain");
                ok(_(ds).isEmpty(), "domains list should be empty");

                ok(got_context, "should have fetched context");
                ok(_(cs).isEmpty(), "contexts list should be empty");

                ok(got_groupby, "should have fetched groupby");
                ok(_(gs).isEmpty(), "groupby list should be empty");
            })
    });
    asyncTest('Generate domains', 1, function () {
        var $fix = $('#qunit-fixture');
        var view = makeSearchView({
            get_domain: function (facet) {
                return facet.values.map(function (value) {
                    return ['win', '4', value.get('value')];
                });
            }
        }, {dummy: 42});
        var ds;
        view.on_search.add(function (d) { ds = d; });
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                view.do_search();
                deepEqual(ds, [[['win', '4', 42]]],
                    "search should yield an array of contexts");
            });
    });

    module('drawer', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            window.openerp.web.search(instance);

            instance.web.qweb.add_template(doc);

            mockifyRPC(instance.connection);
        }
    });
    asyncTest('is-drawn', 2, function () {
        var view = makeSearchView();
        var $fix = $('#qunit-fixture');
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                ok($fix.find('.oe_searchview_filters').length,
                   "filters drawer control has been drawn");
                ok($fix.find('.oe_searchview_advanced').length,
                   "filters advanced search has been drawn");
            });
    });

    module('filters', {
        setup: function () {
            instance = window.openerp.init([]);
            window.openerp.web.corelib(instance);
            window.openerp.web.coresetup(instance);
            window.openerp.web.chrome(instance);
            window.openerp.web.data(instance);
            window.openerp.web.search(instance);

            instance.web.qweb.add_template(doc);

            mockifyRPC(instance.connection, {
                '/web/searchview/load': function () {
                    // view with a single group of filters
                    return {result: {fields_view: {
                        type: 'search',
                        fields: {},
                        arch: {
                            tag: 'search',
                            attrs: {},
                            children: [{
                                tag: 'filter',
                                attrs: { string: "Foo1", domain: [ ['foo', '=', '1'] ] },
                                children: []
                            }, {
                                tag: 'filter',
                                attrs: {
                                    name: 'foo2',
                                    string: "Foo2",
                                    domain: [ ['foo', '=', '2'] ] },
                                children: []
                            }, {
                                tag: 'filter',
                                attrs: { string: "Foo3", domain: [ ['foo', '=', '3'] ] },
                                children: []
                            }]
                        }
                    }}};
                }
            });
        }
    });
    asyncTest('drawn', 3, function () {
        var view = makeSearchView();
        var $fix = $('#qunit-fixture');
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $fs = $fix.find('.oe_searchview_filters ul');
                // 3 filters, 1 filtergroup, 1 advanced and 1 Filters widget
                equal(view.inputs.length, 6,
                      'view should have 6 inputs total');
                equal($fs.children().length, 3,
                      "drawer should have a filter group with 3 filters");
                equal(_.str.strip($fs.children().eq(0).text()), "Foo1",
                      "Text content of first filter option should match filter string");
            });
    });
    asyncTest('click adding from empty query', 4, function () {
        var view = makeSearchView();
        var $fix = $('#qunit-fixture');
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $fs = $fix.find('.oe_searchview_filters ul');
                $fs.children(':eq(2)').trigger('click');
                equal(view.query.length, 1, "click should have added a facet");
                var facet = view.query.at(0);
                equal(facet.values.length, 1, "facet should have a single value");
                var value = facet.values.at(0);
                ok(value.get('value') instanceof instance.web.search.Filter,
                   "value should be a filter");
                equal(value.get('label'), "Foo3",
                      "value should be third filter");
            });
    });
    asyncTest('click adding from existing query', 4, function () {
        var view = makeSearchView({}, {foo2: true});
        var $fix = $('#qunit-fixture');
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $fs = $fix.find('.oe_searchview_filters ul');
                $fs.children(':eq(2)').trigger('click');
                equal(view.query.length, 1, "click should not have changed facet count");
                var facet = view.query.at(0);
                equal(facet.values.length, 2, "facet should have a second value");
                var v1 = facet.values.at(0);
                equal(v1.get('label'), "Foo2",
                      "first value should be default");
                var v2 = facet.values.at(1);
                equal(v2.get('label'), "Foo3",
                      "second value should be clicked filter");
            });
    });
    asyncTest('click removing from query', 2, function () {
        var view = makeSearchView({}, {foo2: true});
        var $fix = $('#qunit-fixture');
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $fs = $fix.find('.oe_searchview_filters ul');
                // sanity check
                equal(view.query.length, 1, "query should have default facet");
                $fs.children(':eq(1)').trigger('click');
                equal(view.query.length, 0, "click should have removed facet");
            });
    });

    // TODO: UI tests?
});
