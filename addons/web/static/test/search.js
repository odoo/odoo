$(document).ready(function () {
    var instance;
    module('query', {
        setup: function () {
            instance = openerp.testing.instanceFor('search');
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
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
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
        if (!('/web/searchview/load' in instance.session.responses)) {
            instance.session.responses['/web/searchview/load'] = function () {
                return {result: {fields_view: {
                    type: 'search',
                    fields: {
                        dummy: {type: 'char', string: "Dummy"}
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
        instance.session.responses['/web/searchview/get_filters'] = function () {
            return {result: []};
        };
        instance.session.responses['/web/searchview/fields_get'] = function () {
            return {result: {fields: {
                dummy: {type: 'char', string: 'Dummy'}
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
        var view = {inputs: [], query: {on: function () {}}};
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
        instance.session.responses['/web/dataset/call_kw'] = function (req) {
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
        instance.session.responses['/web/dataset/call_kw'] = function (req) {
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
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
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
            .done(function () {
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
                field: {
                    get_domain: openerp.testing.noop,
                    get_context: openerp.testing.noop,
                    get_groupby: openerp.testing.noop
                },
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
        var field = {
            get_domain: openerp.testing.noop,
            get_context: openerp.testing.noop,
            get_groupby: openerp.testing.noop
        };
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
        instance.session.responses['/web/dataset/call_kw'] = function (req) {
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
        instance.session.responses['/web/dataset/call_kw'] = function (req) {
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
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
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
                equal(facet.get('category'), "Dummy");
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

    test('Field single value, default domain & context', function () {
        var f = new instance.web.search.Field({}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{value: 42}]
        });

        deepEqual(f.get_domain(facet), [['foo', '=', 42]],
            "default field domain is a strict equality of name to facet's value");
        equal(f.get_context(facet), null,
            "default field context is null");
    });
    test('Field multiple values, default domain & context', function () {
        var f = new instance.web.search.Field({}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{value: 42}, {value: 68}, {value: 999}]
        });

        var actual_domain = f.get_domain(facet);
        equal(actual_domain.__ref, "compound_domain",
              "multiple value should yield compound domain");
        deepEqual(actual_domain.__domains, [
                    ['|'],
                    ['|'],
                    [['foo', '=', 42]],
                    [['foo', '=', 68]],
                    [['foo', '=', 999]]
            ],
            "domain should OR a default domain for each value");
        equal(f.get_context(facet), null,
            "default field context is null");
    });
    test('Field single value, custom domain & context', function () {
        var f = new instance.web.search.Field({attrs:{
            context: "{'bob': self}",
            filter_domain: "[['edmund', 'is', self]]"
        }}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{value: "great"}]
        });

        var actual_domain = f.get_domain(facet);
        equal(actual_domain.__ref, "compound_domain",
              "@filter_domain should yield compound domain");
        deepEqual(actual_domain.__domains, [
            "[['edmund', 'is', self]]"
        ], 'should hold unevaluated custom domain');
        deepEqual(actual_domain.get_eval_context(), {
            self: "great"
        }, "evaluation context should hold facet value as self");

        var actual_context = f.get_context(facet);
        equal(actual_context.__ref, "compound_context",
              "@context should yield compound context");
        deepEqual(actual_context.__contexts, [
            "{'bob': self}"
        ], 'should hold unevaluated custom context');
        deepEqual(actual_context.get_eval_context(), {
            self: "great"
        }, "evaluation context should hold facet value as self");
    });
    test("M2O default", function () {
        var f = new instance.web.search.ManyToOneField(
            {}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        deepEqual(f.get_domain(facet), [['foo', '=', 42]],
            "m2o should use identity if default domain");
        deepEqual(f.get_context(facet), {default_foo: 42},
            "m2o should use value as context default");
    });
    test("M2O default multiple values", function () {
        var f = new instance.web.search.ManyToOneField(
            {}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [
                {label: "Foo", value: 42},
                {label: "Bar", value: 36}
            ]
        });

        deepEqual(f.get_domain(facet).__domains,
            [['|'], [['foo', '=', 42]], [['foo', '=', 36]]],
            "m2o should or multiple values");
        equal(f.get_context(facet), null,
            "m2o should not have default context in case of multiple values");
    });
    test("M2O custom operator", function () {
        var f = new instance.web.search.ManyToOneField(
            {attrs: {operator: 'boos'}}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        deepEqual(f.get_domain(facet), [['foo', 'boos', 'Foo']],
            "m2o should use label with custom operators");
        deepEqual(f.get_context(facet), {default_foo: 42},
            "m2o should use value as context default");
    });
    test("M2O custom domain & context", function () {
        var f = new instance.web.search.ManyToOneField({attrs: {
            context: "{'whee': self}",
            filter_domain: "[['filter', 'is', self]]"
        }}, {name: 'foo'}, {inputs: []});
        var facet = new instance.web.search.Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        var domain = f.get_domain(facet);
        deepEqual(domain.__domains, [
            "[['filter', 'is', self]]"
        ]);
        deepEqual(domain.get_eval_context(), {
            self: "Foo"
        }, "custom domain's self should be label");
        var context = f.get_context(facet);
        deepEqual(context.__contexts, [
            "{'whee': self}"
        ]);
        deepEqual(context.get_eval_context(), {
            self: "Foo"
        }, "custom context's self should be label");
    });

    asyncTest('FilterGroup', 6, function () {
        var view = {inputs: [], query: {on: function () {}}};
        var filter_a = new instance.web.search.Filter(
            {attrs: {name: 'a', context: 'c1', domain: 'd1'}}, view);
        var filter_b = new instance.web.search.Filter(
            {attrs: {name: 'b', context: 'c2', domain: 'd2'}}, view);
        var filter_c = new instance.web.search.Filter(
            {attrs: {name: 'c', context: 'c3', domain: 'd3'}}, view);
        var group = new instance.web.search.FilterGroup(
            [filter_a, filter_b, filter_c], view);
        group.facet_for_defaults({a: true, c: true})
            .always(start)
            .fail(function (error) { ok(false, error && error.message); })
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof instance.web.search.Facet)) {
                    model = new instance.web.search.Facet(facet);
                }

                var domain = group.get_domain(model);
                equal(domain.__ref, 'compound_domain',
                    "domain should be compound");
                deepEqual(domain.__domains, [
                    ['|'], 'd1', 'd3'
                ], "domain should OR filter domains");
                ok(!domain.get_eval_context(), "domain should have no evaluation context");
                var context = group.get_context(model);
                equal(context.__ref, 'compound_context',
                    "context should be compound");
                deepEqual(context.__contexts, [
                    'c1', 'c3'
                ], "context should merge all filter contexts");
                ok(!context.get_eval_context(), "context should have no evaluation context");
            });
    });

    module('removal', {
        setup: function () {
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
        }
    });
    asyncTest('clear button', function () {
        var $fix = $('#qunit-fixture');
        var view = makeSearchView({
            facet_for_defaults: function (defaults) {
                return $.when({
                    field: this,
                    category: 'Dummy',
                    values: [{label: 'dummy', value: defaults.dummy}]
                });
            }
        }, {dummy: 42});
        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                equal(view.query.length, 1, "view should have default facet");
                $fix.find('.oe_searchview_clear').click();
                equal(view.query.length, 0, "cleared view should not have any facet");
            });
    });

    module('drawer', {
        setup: function () {
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
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
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance, {
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
                // 3 filters, 1 filtergroup, 1 custom filters widget,
                // 1 advanced and 1 Filters widget
                equal(view.inputs.length, 7,
                      'view should have 7 inputs total');
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

    module('saved_filters', {
        setup: function () {
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
        }
    });
    asyncTest('checkboxing', 6, function () {
        var view = makeSearchView();
        instance.session.responses['/web/searchview/get_filters'] = function () {
            return {result: [{
                name: "filter name",
                user_id: 42
            }]};
        };
        var $fix = $('#qunit-fixture');

        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $row = $fix.find('.oe_searchview_custom li:first').click();

                ok($row.hasClass('oe_selected'), "should check/select the filter's row");
                ok($row.hasClass("oe_searchview_custom_private"),
                    "should have private filter note/class");
                equal(view.query.length, 1, "should have only one facet");
                var values = view.query.at(0).values;
                equal(values.length, 1,
                    "should have only one value in the facet");
                equal(values.at(0).get('label'), 'filter name',
                    "displayed label should be the name of the filter");
                equal(values.at(0).get('value'), null,
                    "should have no value set");
            })
    });
    asyncTest('removal', 1, function () {
        var view = makeSearchView();
        instance.session.responses['/web/searchview/get_filters'] = function () {
            return {result: [{
                name: "filter name",
                user_id: 42
            }]};
        };
        var $fix = $('#qunit-fixture');

        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $row = $fix.find('.oe_searchview_custom li:first').click();

                view.query.remove(view.query.at(0));
                ok(!$row.hasClass('oe_selected'),
                    "should not be checked anymore");
            })
    });

    module('advanced', {
        setup: function () {
            instance = openerp.testing.instanceFor('search');

            openerp.testing.loadTemplate(instance);

            openerp.testing.mockifyRPC(instance);
        }
    });
    asyncTest('single-advanced', 6, function () {
        var view = makeSearchView();
        var $fix = $('#qunit-fixture');

        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $advanced = $fix.find('.oe_searchview_advanced');
                // open advanced search (not actually useful)
                $advanced.find('> h4').click();
                // select proposition (only one)
                var $prop = $advanced.find('> form li:first');
                // field select should have two possible values, dummy and id
                equal($prop.find('.searchview_extended_prop_field option').length,
                      2, "advanced search should provide choice between two fields");
                // field should be dummy
                equal($prop.find('.searchview_extended_prop_field').val(),
                      'dummy',
                      "only field should be dummy");
                // operator should be "contains"/'ilike'
                equal($prop.find('.searchview_extended_prop_op').val(),
                      'ilike', "default char operator should be ilike");
                // put value in
                $prop.find('.searchview_extended_prop_value input')
                     .val("stupid value");
                // validate advanced search
                $advanced.find('button.oe_apply').click();

                // resulting search
                equal(view.query.length, 1, "search query should have a single facet");
                var facet = view.query.at(0);
                ok(!facet.get('field').get_context(facet),
                   "advanced search facets should yield no context");
                deepEqual(facet.get('field').get_domain(facet),
                          [['dummy', 'ilike', "stupid value"]],
                          "advanced search facet should return proposed domain");
            });
    });
    asyncTest('multiple-advanced', 3, function () {
        var view = makeSearchView();
        var $fix = $('#qunit-fixture');

        view.appendTo($fix)
            .always(start)
            .fail(function (error) { ok(false, error.message); })
            .done(function () {
                var $advanced = $fix.find('.oe_searchview_advanced');
                // open advanced search (not actually useful)
                $advanced.find('> h4').click();
                // open second condition
                $advanced.find('button.oe_add_condition').click();
                // select first proposition
                var $prop1 = $advanced.find('> form li:first');
                $prop1.find('.searchview_extended_prop_field').val('dummy').change();
                $prop1.find('.searchview_extended_prop_op').val('ilike');
                $prop1.find('.searchview_extended_prop_value input')
                     .val("stupid value");

                // select first proposition
                var $prop2 = $advanced.find('> form li:last');
                // need to trigger event manually or op not changed
                $prop2.find('.searchview_extended_prop_field').val('id').change();
                $prop2.find('.searchview_extended_prop_op').val('=');
                $prop2.find('.searchview_extended_prop_value input')
                     .val(42);
                // validate advanced search
                $advanced.find('button.oe_apply').click();

                // resulting search
                equal(view.query.length, 1, "search query should have a single facet");
                var facet = view.query.at(0);
                ok(!facet.get('field').get_context(facet),
                   "advanced search facets should yield no context");
                deepEqual(facet.get('field').get_domain(facet),
                          ['|', ['dummy', 'ilike', "stupid value"],
                                ['id', '=', 42]],
                          "advanced search facet should return proposed domain");
            });
    });
    // TODO: UI tests?
});
