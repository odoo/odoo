odoo.define_section('search.query', ['web.SearchView'], function (test) {

    test('Adding a facet to the query creates a facet and a value', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        var field = {};
        query.add({
            category: 'Foo',
            field: field,
            values: [{label: 'Value', value: 3}]
        });

        var facet = query.at(0);
        assert.equal(facet.get('category'), 'Foo');
        assert.equal(facet.get('field'), field);
        assert.deepEqual(facet.get('values'), [{label: 'Value', value: 3}]);
    });

    test('Adding two facets', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        query.add([
            { category: 'Foo', field: {}, values: [{label: 'Value', value: 3}] },
            { category: 'Bar', field: {}, values: [{label: 'Value 2', value: 4}] }
        ]);

        assert.equal(query.length, 2);
        assert.equal(query.at(0).values.length, 1);
        assert.equal(query.at(1).values.length, 1);
    });

    test('If a facet already exists, add values to it', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        var field = {};
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.equal(query.length, 1, "adding an existing facet should merge new values into old facet");
        var facet = query.at(0);
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

    test('Facet being implicitly changed should trigger change, not add', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        var field = {}, added = false, changed = false;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.on('add', function () { added = true; })
             .on('change', function () { changed = true; });
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.ok(!added, "query.add adding values to a facet should not trigger an add");
        assert.
        ok(changed, "query.add adding values to a facet should not trigger a change");
    });

    test('Toggling a facet, value which does not exist should add it', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        var field = {};
        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        assert.equal(query.length, 1, "Should have created a single facet");
        var facet = query.at(0);
        assert.equal(facet.values.length, 1, "Facet should have a single value");
        assert.deepEqual(facet.get('values'), [{label: 'V1', value: 0}],
                  "Facet's value should match input");
    });

    test('Toggling a facet which exists with a value which does not should add the value to the facet', function (assert, SearchView) {
        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.equal(query.length, 1, "Should have edited the existing facet");
        var facet = query.at(0);
        assert.equal(facet.values.length, 2, "Should have added the value to the existing facet");
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

    test('Toggling a facet which exists with a value which does as well should remove the value from the facet', function (assert, SearchView) {
        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.equal(query.length, 1, 'Should have the same single facet');
        var facet = query.at(0);
        assert.equal(facet.values.length, 1, "Should only have one value left in the facet");
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0}
        ]);
    });

    test('Toggling off the last value of a facet should remove the facet', function (assert, SearchView) {
        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        assert.equal(query.length, 0, 'Should have removed the facet');
    });

    test('Intermediate emptiness should not remove the facet', function (assert, SearchView) {
        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]});

        assert.equal(query.length, 1, 'Should not have removed the facet');
        var facet = query.at(0);
        assert.equal(facet.values.length, 1, "Should have one value");
        assert.deepEqual(facet.get('values'), [
            {label: 'V2', value: 1}
        ]);
    });

    test('Reseting with multiple facets should still work to load defaults', function (assert, SearchView) {
        var query = new SearchView.SearchQuery();
        var field = {};
        query.reset([
            {category: 'A', field: field, values: [{label: 'V1', value: 0}]},
            {category: 'A', field: field, values: [{label: 'V2', value: 1}]}]);

        assert.equal(query.length, 1, 'Should have created a single facet');
        assert.equal(query.at(0).values.length, 2, 'the facet should have merged two values');
        assert.deepEqual(query.at(0).get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

});

/**
 * Builds a basic search view with a single "dummy" field. The dummy
 * extends `instance.web.search.Field`, it does not add any (class)
 * attributes beyond what is provided through ``dummy_widget_attributes``.
 *
 * The view is returned un-started, it is the caller's role to start it
 * (or use DOM-insertion methods to start it indirectly).
 *
 * @param instance
 * @param [dummy_widget_attributes={}]
 * @param [defaults={}]
 * @return {instance.web.SearchView}
 */

function makeSearchView (test, dummy_widget_attributes, defaults, options) {
    var core = test.deps['web.core'];
    var search_inputs = test.deps['web.search_inputs'];
    var data = test.deps['web.data'];
    var SearchView = test.deps['web.SearchView'];

    var mock = test.mock;
    var assert = test.assert

    var DummyWidget = search_inputs.Field.extend(dummy_widget_attributes || {});
    core.search_widgets_registry.add('dummy', DummyWidget);

    mock.add('dummy.model:fields_view_get', function () {
        return {
            type: 'search',
            fields: {
                dummy: {type: 'char', string: "Dummy", searchable: true}
            },
            arch: '<search><field name="dummy" widget="dummy"/></search>'
        };
    }, true);

    mock.add('ir.filters:get_filters', function () {
        return [];
    });

    mock.add('dummy.model:fields_get', function () {
        return {
            dummy: {type: 'char', string: 'Dummy', searchable: true}
        };
    });


    // instance.client = { action_manager: { inner_action: undefined } };

    var dataset = new data.DataSet(null, 'dummy.model');
    
    var mock_parent = {getParent: function () {return null;}};
    
    options = _.defaults(options || {}, {$buttons: $('<div>')});
    
    var view = new SearchView(mock_parent, dataset, false, defaults, options);

    view.on('invalid_search', this, function () {
        assert.ok(false, JSON.stringify([].slice(arguments)));
    });
    return view;
};

odoo.define_section('search.defaults', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {
    test('calling', function (assert) {
        assert.expect(2);
        var defaults_called = false;

        var view = makeSearchView(this, {
            facet_for_defaults: function (defaults) {
                defaults_called = true;
                return $.when({
                    field: this,
                    category: 'Dummy',
                    values: [{label: 'dummy', value: defaults.dummy}]
                });
            }
        }, {dummy: 42});
        var $fix = $( "#qunit-fixture");
        return view.appendTo($fix)
            .done(function () {
                assert.ok(defaults_called, "should have called defaults");
                assert.deepEqual(
                    view.query.toJSON(),
                    [{category: 'Dummy', values: [{label: 'dummy', value: 42}]}],
                    "should have generated a facet with the default value");
            });
    });

    test('FilterGroup', function (assert, search_inputs, SearchView) {
        assert.expect(3);

        var Facet = SearchView.Facet;

        var view = {inputs: [], query: {on: function () {}}};
        var filter_a = new search_inputs.Filter(
            {attrs: {name: 'a'}}, view);
        var filter_b = new search_inputs.Filter(
            {attrs: {name: 'b'}}, view);
        var group = new search_inputs.FilterGroup(
            [filter_a, filter_b], view);
        return group.facet_for_defaults({a: true, b: true})
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof Facet)) {
                    model = new Facet(facet);
                }
                var values = model.values;
                assert.equal(values.length, 2, 'facet should have two values');
                assert.strictEqual(values.at(0).get('value'), filter_a);
                assert.strictEqual(values.at(1).get('value'), filter_b);
            });
    });

    test('Field', function (assert, search_inputs, SearchView) {
        assert.expect(4);
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new search_inputs.Field(
            {attrs: {string: 'Dummy', name: 'dummy'}}, {}, view);
        
        return f.facet_for_defaults({dummy: 42})
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof Facet)) {
                    model = new Facet(facet);
                }
                assert.strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                assert.strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                assert.equal(model.values.length, 1, "facet should have a single value");
                assert.deepEqual(
                    model.values.toJSON(),
                    [{label: '42', value: 42}],
                    "facet value should match provided default");
                });
    });

    test('Selection: valid value', function (assert, search_inputs, SearchView, core) {
        assert.expect(4);

        var SelectionField = core.search_widgets_registry.get('selection');
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new SelectionField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Qux"]]},
            view);
        return f.facet_for_defaults({dummy: 3})
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof Facet)) {
                    model = new Facet(facet);
                }
                assert.strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                assert.strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                assert.equal(model.values.length, 1, "facet should have a single value");
                assert.deepEqual(
                    model.values.toJSON(),
                    [{label: 'Baz', value: 3}],
                    "facet value should match provided default's selection");
            });
    });

    test('Selection: invalid value', function (assert, search_inputs, SearchView, core) {
        assert.expect(1);

        var SelectionField = core.search_widgets_registry.get('selection');

        var view = {inputs: []};
        var f = new SelectionField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Qux"]]},
            view);
        return f.facet_for_defaults({dummy: 42})
            .done(function (facet) {
                assert.ok(!facet, "an invalid value should result in a not-facet");
            });
    });

    test("M2O default: value", function (assert, search_inputs, SearchView, core) {
        assert.expect(5);

        var ManyToOneField =  core.search_widgets_registry.get('many2one');
        var Facet = SearchView.Facet;

        var view = {inputs: [], dataset: {get_context: function () {}}}, id = 4;
        var f = new ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        mock.add('dummy.model.name:name_get', function (args) {
            assert.equal(args[0], id);
            return [[id, "DumDumDum"]];
        });
        return f.facet_for_defaults({dummy: id})
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof Facet)) {
                    model = new Facet(facet);
                }
                assert.strictEqual(
                    model.get('category'),
                    f.attrs.string,
                    "facet category should be field label");
                assert.strictEqual(
                    model.get('field'), f,
                    "facet field should be field which created default");
                assert.equal(model.values.length, 1, "facet should have a single value");
                assert.deepEqual(
                    model.values.toJSON(),
                    [{label: 'DumDumDum', value: id}],
                    "facet value should match provided default's selection");
            });
    });

    test("M2O default: value array", function (assert, search_inputs, SearchView, core) {
        assert.expect(2);

        var ManyToOneField =  core.search_widgets_registry.get('many2one');
        var Facet = SearchView.Facet;

        var view = {inputs: [], dataset: {get_context: function () {}}}, id = 5;
        var f = new ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        mock.add('dummy.model.name:name_get', function (args) {
            assert.equal(args[0], id);
            return [[id, "DumDumDum"]];
        });
        return f.facet_for_defaults({dummy: [id]})
        .done(function (facet) {
            var model = facet;
            if (!(model instanceof Facet)) {
                model = new Facet(facet);
            }
            assert.deepEqual(
                model.values.toJSON(),
                [{label: "DumDumDum", value: id}],
                "should support default as a singleton");
        });
    });

    test("M2O default: value", function (assert, search_inputs, SearchView, core) {
        assert.expect(1);

        var ManyToOneField =  core.search_widgets_registry.get('many2one');

        var view = {inputs: [], dataset: {get_context: function () {}}}, id = 4;
        var f = new ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        mock.add('dummy.model.name:name_get', function () { return []; });
        return f.facet_for_defaults({dummy: id})
            .done(function (facet) {
                assert.ok(!facet, "an invalid m2o default should yield a non-facet");
            });
    });

    test("M2O default: values", function (assert, search_inputs, SearchView, core) {
        assert.expect(1);

        var ManyToOneField =  core.search_widgets_registry.get('many2one');

        var view = {inputs: []};
        var f = new ManyToOneField(
            {attrs: {name: 'dummy', string: 'Dummy'}},
            {relation: 'dummy.model.name'},
            view);
        assert.raises(function () { f.facet_for_defaults({dummy: [6, 7]}); },
               "should not accept multiple default values");
    });


});

odoo.define_section('search.completions', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('calling', function (assert) {
        assert.expect(4);
        var view = makeSearchView(this, {
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

        var done = $.Deferred();
        var $fix = $('#qunit-fixture');
        
        view.appendTo($fix)
            .then(function () {
                view.complete_global_search({term: "dum"}, function (completions) {
                    assert.equal(completions.length, 1, "should have a single completion");
                    var completion = completions[0];
                    assert.equal(completion.label, "Dummy",
                          "should have provided label");
                    assert.equal(completion.facet.category, "Dummy",
                          "should have provided category");
                    assert.deepEqual(completion.facet.values,
                              [{label: 'dummy', value: 42}],
                              "should have provided values");
                    done.resolve();
                });
            }).fail(function () { done.reject.apply(done, arguments); });
        return done;
    });

    test('facet selection', function (assert) {
        assert.expect(2);
        var completion = {
            label: "Dummy",
            facet: {
                field: {
                    get_domain: odoo.testing.noop,
                    get_context: odoo.testing.noop,
                    get_groupby: odoo.testing.noop
                },
                category: 'Dummy',
                values: [{label: 'dummy', value: 42}]
            }
        };

        var $fix = $('#qunit-fixture');
        var view = makeSearchView(this);
        return view.appendTo($fix)
            .done(function () {
                view.select_completion(
                    {preventDefault: function () {}},
                    {item: completion});
                assert.equal(view.query.length, 1, "should have one facet in the query");
                assert.deepEqual(
                    view.query.at(0).toJSON(),
                    {category: 'Dummy', values: [{label: 'dummy', value: 42}]},
                    "should have the right facet in the query");
            });
    });

    test('facet selection: new value existing facet', function (assert) {
        assert.expect(8);
        var field = {
            get_domain: odoo.testing.noop,
            get_context: odoo.testing.noop,
            get_groupby: odoo.testing.noop
        };
        var completion = {
            label: "Dummy",
            facet: {
                field: field,
                category: 'Dummy',
                values: [{label: 'dummy', value: 42}]
            }
        };

        var $fix = $('#qunit-fixture');
        var view = makeSearchView(this);
        return view.appendTo($fix)
            .done(function () {
                view.query.add({field: field, category: 'Dummy',
                                values: [{label: 'previous', value: 41}]});
                assert.equal(view.query.length, 1, 'should have newly added facet');
                view.select_completion(
                    {preventDefault: function () {}},
                    {item: completion});
                assert.equal(view.query.length, 1, "should still have only one facet");
                var facet = view.query.at(0);
                var values = facet.get('values');
                assert.equal(values.length, 2, 'should have two values');
                assert.equal(values[0].label, 'previous');
                assert.equal(values[0].value, 41);
                assert.equal(values[1].label, 'dummy');
                assert.equal(values[1].value, 42);
                assert.deepEqual(
                    values,
                    [{label: 'previous', value: 41}, {label: 'dummy', value: 42}],
                    "should have added selected value to old one");
            });
    });

    test('Field', function (assert, search_inputs) {
        assert.expect(1);

        var view = {inputs: []};
        var f = new search_inputs.Field({attrs: {}}, {}, view);

        return f.complete('foo')
            .done(function (completions) {
                assert.ok(_(completions).isEmpty(), "field should not provide any completion");
            });
    });

    test('CharField', function (assert, search_inputs, SearchView, core) {
        assert.expect(6);
        var view = {inputs: []};
        var CharField = core.search_widgets_registry.get('char');
        var Facet = SearchView.Facet;

        var f = new CharField(
            {attrs: {string: "Dummy"}}, {}, view);
        return f.complete('foo<')
            .done(function (completions) {
                assert.equal(completions.length, 1, "should provide a single completion");
                var c = completions[0];
                assert.equal(c.label, "Search <em>Dummy</em> for: <strong>foo&lt;</strong>",
                      "should propose a fuzzy matching/searching, with the" +
                      " value escaped");
                assert.ok(c.facet, "completion should contain a facet proposition");
                var facet = new Facet(c.facet);
                assert.equal(facet.get('category'), f.attrs.string,
                      "completion facet should bear the field's name");
                assert.strictEqual(facet.get('field'), f,
                            "completion facet should yield the field");
                assert.deepEqual(facet.values.toJSON(), [{label: 'foo<', value: 'foo<'}],
                          "facet should have single value using completion item");
            });
    });

    test('Selection: match found', function (assert, search_inputs, SearchView, core) {
        assert.expect(14);

        var SelectionField = core.search_widgets_registry.get('selection');

        var view = {inputs: []};
        var f = new SelectionField(
            {attrs: {string: "Dummy"}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Bazador"]]},
            view);
        return f.complete("ba")
            .done(function (completions) {
                assert.equal(completions.length, 4,
                    "should provide two completions and a section title");
                assert.deepEqual(completions[0], {label: "Dummy"});

                var c1 = completions[1];
                assert.equal(c1.label, "Bar");
                assert.equal(c1.facet.category, f.attrs.string);
                assert.strictEqual(c1.facet.field, f);
                assert.deepEqual(c1.facet.values, [{label: "Bar", value: 2}]);

                var c2 = completions[2];
                assert.equal(c2.label, "Baz");
                assert.equal(c2.facet.category, f.attrs.string);
                assert.strictEqual(c2.facet.field, f);
                assert.deepEqual(c2.facet.values, [{label: "Baz", value: 3}]);

                var c3 = completions[3];
                assert.equal(c3.label, "Bazador");
                assert.equal(c3.facet.category, f.attrs.string);
                assert.strictEqual(c3.facet.field, f);
                assert.deepEqual(c3.facet.values, [{label: "Bazador", value: 4}]);
            });
    });

    test('Selection: no match', function (assert, search_inputs, SearchView, core) {
        assert.expect(1);

        var SelectionField = core.search_widgets_registry.get('selection');

        var view = {inputs: []};
        var f = new SelectionField(
            {attrs: {string: "Dummy"}},
            {selection: [[1, "Foo"], [2, "Bar"], [3, "Baz"], [4, "Bazador"]]},
            view);
        return f.complete("qux")
            .done(function (completions) {
                assert.ok(!completions, "if no value matches the needle, no completion shall be provided");
            });
    });

    test('Date', function (assert, search_inputs, SearchView, core) {
        assert.expect(6);
        core._t.database.parameters = {
            date_format: '%Y-%m-%d',
            time_format: '%H:%M:%S'
        };

        var DateField = core.search_widgets_registry.get('date');
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new DateField(
            {attrs: {string: "Dummy"}}, {type: 'datetime'}, view);
        return f.complete('2012-05-21T21:21:21')
            .done(function (completions) {
                assert.equal(completions.length, 1, "should provide a single completion");
                var c = completions[0];
                assert.equal(c.label, "Search <em>Dummy</em> at: <strong>2012-05-21 21:21:21</strong>");
                var facet = new Facet(c.facet);
                assert.equal(facet.get('category'), f.attrs.string);
                assert.equal(facet.get('field'), f);
                var value = facet.values.at(0);
                assert.equal(value.get('label'), "2012-05-21 21:21:21");
                assert.equal(value.get('value').getTime(),
                      new Date(2012, 4, 21, 21, 21, 21).getTime());
            });
    });

    test("M2O complete", function (assert, search_inputs, SearchView, core) {
        assert.expect(4);
        var ManyToOneField = core.search_widgets_registry.get('many2one');

        var view = {inputs: [], dataset: {get_context: function () {}}};
        var f = new ManyToOneField(
            {attrs: {string: 'Dummy'}}, {relation: 'dummy.model'}, view);
        return f.complete("bob")
            .done(function (c) {
                assert.equal(c.length, 1, "should return one line");
                var bob = c[0];
                assert.ok(bob.expand, "should return an expand callback");
                assert.ok(bob.facet, "should have a facet");
                assert.ok(bob.label, "should have a label");
            });
    });

    test("M2O expand", {asserts: 11}, function (assert, search_inputs, SearchView, core) {
        assert.expect(11);
        var ManyToOneField = core.search_widgets_registry.get('many2one');
        var Facet = SearchView.Facet;

        mock.add('dummy.model:name_search', function (args, kwargs) {
            assert.deepEqual(args, []);
            assert.strictEqual(kwargs.name, 'bob');
            return [[42, "choice 1"], [43, "choice @"]];
        });

        var view = {inputs: [], dataset: {get_context: function () {}}};
        var f = new ManyToOneField(
            {attrs: {string: 'Dummy'}}, {relation: 'dummy.model'}, view);
        return f.expand("bob")
            .done(function (c) {
                assert.equal(c.length, 2, "should return results");

                var f1 = new Facet(c[0].facet);
                assert.equal(c[0].label, "choice 1");
                assert.equal(f1.get('category'), f.attrs.string);
                assert.equal(f1.get('field'), f);
                assert.deepEqual(f1.values.toJSON(), [{label: 'choice 1', value: 42}]);

                var f2 = new Facet(c[1].facet);
                assert.equal(c[1].label, "choice @");
                assert.equal(f2.get('category'), f.attrs.string);
                assert.equal(f2.get('field'), f);
                assert.deepEqual(f2.values.toJSON(), [{label: 'choice @', value: 43}]);
            });
    });

    test("M2O no match", function (assert, search_inputs, SearchView, core) {
        assert.expect(3);
        var ManyToOneField = core.search_widgets_registry.get('many2one');

        mock.add('dummy.model:name_search', function (args, kwargs) {
            assert.deepEqual(args, []);
            assert.strictEqual(kwargs.name, 'bob');
            return [];
        });

        var view = {inputs: [], dataset: {get_context: function () {}}};
        var f = new ManyToOneField(
            {attrs: {string: 'Dummy'}}, {relation: 'dummy.model'}, view);
        return f.expand("bob")
            .done(function (c) {
                assert.ok(!c, "no match should yield no completion");
            });
    });

    test("M2O filtered", function (assert, search_inputs, SearchView, core) {
        assert.expect(2);
        var ManyToOneField = core.search_widgets_registry.get('many2one');

        mock.add('dummy.model:name_search', function (args, kwargs) {
            assert.deepEqual(args, [], "should have no positional arguments");
            assert.deepEqual(kwargs, {
                name: 'bob',
                limit: 8,
                args: [['foo', '=', 'bar']],
                context: {flag: 1},
            }, "should use filtering domain");
            return [[42, "Match"]];
        });
        var view = {
            inputs: [],
            dataset: {get_context: function () { return {flag: 1}; }}
        };
        var f = new ManyToOneField(
            {attrs: {string: 'Dummy', domain: [["foo", "=", "bar"]]}},
            {relation: 'dummy.model'}, view);
        return f.expand("bob");
    });

    test("M2O custom operator", function (assert, search_inputs, SearchView, core) {
        assert.expect(8);
        var ManyToOneField = core.search_widgets_registry.get('many2one');
        var Facet = SearchView.Facet;

        mock.add('dummy.model:name_search', function (args, kwargs) {
            assert.deepEqual(args, [], "should have no positional arguments");
            // the operator is meant for the final search term generation, not the autocompletion
            assert.equal(kwargs.operator, undefined, "operator should not be used for autocompletion")
            assert.strictEqual(kwargs.name, 'bob');
            return [[42, "Match"]];
        });
        var view = {inputs: [], dataset: {get_context: function () {}}};
        var f = new ManyToOneField(
            {attrs: {string: 'Dummy', operator: 'ilike'}},
            {relation: 'dummy.model'}, view);

        return f.expand('bob')
            .done(function (c) {
                assert.equal(c.length, 1, "should return result");

                var f1 = new Facet(c[0].facet);
                assert.equal(c[0].label, "Match");
                assert.equal(f1.get('category'), f.attrs.string);
                assert.equal(f1.get('field'), f);
                assert.deepEqual(f1.values.toJSON(), [{label: 'Match', value: 42}]);
            });
    });

    test('Integer: invalid', function (assert, search_inputs, SearchView, core) {
        assert.expect(1);
        var IntegerField = core.search_widgets_registry.get('integer');

        var view = {inputs: []};
        var f = new IntegerField(
            {attrs: {string: "Dummy"}}, {}, view);
        return f.complete("qux")
            .done(function (completions) {
                assert.ok(!completions, "non-number => no completion");
            });
    });

    test('Integer: non-zero', function (assert, search_inputs, SearchView, core) {
        assert.expect(5);
        var IntegerField = core.search_widgets_registry.get('integer');
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new IntegerField(
            {attrs: {string: "Dummy"}}, {}, view);
        return f.complete("-2")
            .done(function (completions) {
                assert.equal(completions.length, 1, "number fields provide 1 completion only");
                var facet = new Facet(completions[0].facet);
                assert.equal(facet.get('category'), f.attrs.string);
                assert.equal(facet.get('field'), f);
                var value = facet.values.at(0);
                assert.equal(value.get('label'), "-2");
                assert.equal(value.get('value'), -2);
            });
    });

    test('Integer: zero', function (assert, search_inputs, SearchView, core) {
        assert.expect(3);
        var IntegerField = core.search_widgets_registry.get('integer');
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new IntegerField(
            {attrs: {string: "Dummy"}}, {}, view);
        return f.complete("0")
            .done(function (completions) {
                assert.equal(completions.length, 1, "number fields provide 1 completion only");
                var facet = new Facet(completions[0].facet);
                var value = facet.values.at(0);
                assert.equal(value.get('label'), "0");
                assert.equal(value.get('value'), 0);
            });
    });

    test('Float: non-zero', function (assert, search_inputs, SearchView, core) {
        assert.expect(5);
        var FloatField = core.search_widgets_registry.get('float');
        var Facet = SearchView.Facet;

        var view = {inputs: []};
        var f = new FloatField(
            {attrs: {string: "Dummy"}}, {}, view);
        return f.complete("42.37")
            .done(function (completions) {
                assert.equal(completions.length, 1, "float fields provide 1 completion only");
                var facet = new Facet(completions[0].facet);
                assert.equal(facet.get('category'), f.attrs.string);
                assert.equal(facet.get('field'), f);
                var value = facet.values.at(0);
                assert.equal(value.get('label'), "42.37");
                assert.equal(value.get('value'), 42.37);
            });
    });
});

odoo.define_section('search.serialization', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('No facet, no call', function (assert, search_inputs, SearchView, core) {
        assert.expect(6);
        var got_domain = false, got_context = false, got_groupby = false;
        var view = makeSearchView(this, {
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
        view.on('search_data', this, function (d, c, g) {
            ds = d; cs = c; gs = g;
        });
        var $fix = $('qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                view.do_search();
                assert.ok(!got_domain, "no facet, should not have fetched domain");
                assert.ok(_(ds).isEmpty(), "domains list should be empty");

                assert.ok(!got_context, "no facet, should not have fetched context");
                assert.ok(_(cs).isEmpty(), "contexts list should be empty");

                assert.ok(!got_groupby, "no facet, should not have fetched groupby");
                assert.ok(_(gs).isEmpty(), "groupby list should be empty");
            });
    });

    test('London, calling', function (assert, search_inputs, SearchView, core) {
        assert.expect(8);

        var got_domain = false,
            got_context = false,
            got_groupby = false;

        var view = makeSearchView(this, {
            get_domain: function (facet) {
                assert.equal(facet.get('category'), "Dummy");
                assert.deepEqual(facet.values.toJSON(), [{label: "42", value: 42}]);
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
        view.on('search_data', this, function (d, c, g) {
            ds = d; cs = c; gs = g;
        });
        var $fix = $('qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                view.do_search();
                assert.ok(got_domain, "should have fetched domain");
                assert.ok(_(ds).isEmpty(), "domains list should be empty");

                assert.ok(got_context, "should have fetched context");
                assert.ok(_(cs).isEmpty(), "contexts list should be empty");

                assert.ok(got_groupby, "should have fetched groupby");
                assert.ok(_(gs).isEmpty(), "groupby list should be empty");
            });
    });

    test('Generate domains', function (assert) {
        assert.expect(1);
        var view = makeSearchView(this, {
            get_domain: function (facet) {
                return facet.values.map(function (value) {
                    return ['win', '4', value.get('value')];
                });
            }
        }, {dummy: 42});
        var ds;
        view.on('search_data', this, function (d) { ds = d; });
        var $fix = $('qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                view.do_search();
                assert.deepEqual(ds, [[['win', '4', 42]]],
                    "search should yield an array of contexts");
            });
    });

    test('Field single value, default domain & context', function (assert, search_inputs, SearchView) {
        var Facet = SearchView.Facet;
        var f = new search_inputs.Field({}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{value: 42}]
        });

        assert.deepEqual(f.get_domain(facet), [['foo', '=', 42]],
            "default field domain is a strict equality of name to facet's value");
        assert.equal(f.get_context(facet), null,
            "default field context is null");
    });

    test('Field multiple values, default domain & context', function (assert, search_inputs, SearchView) {
        var Facet = SearchView.Facet;

        var f = new search_inputs.Field({}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{value: 42}, {value: 68}, {value: 999}]
        });

        var actual_domain = f.get_domain(facet);
        assert.equal(actual_domain.__ref, "compound_domain",
              "multiple value should yield compound domain");
        assert.deepEqual(actual_domain.__domains, [
                    ['|'],
                    ['|'],
                    [['foo', '=', 42]],
                    [['foo', '=', 68]],
                    [['foo', '=', 999]]
            ],
            "domain should OR a default domain for each value");
        assert.equal(f.get_context(facet), null,
            "default field context is null");
    });

    test('Field single value, custom domain & context', function (assert, search_inputs, SearchView) {
        var Facet = SearchView.Facet;

        var f = new search_inputs.Field({attrs:{
            context: "{'bob': self}",
            filter_domain: "[['edmund', 'is', self]]"
        }}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{value: "great"}]
        });

        var actual_domain = f.get_domain(facet);
        assert.equal(actual_domain.__ref, "compound_domain",
              "@filter_domain should yield compound domain");
        assert.deepEqual(actual_domain.__domains, [
            "[['edmund', 'is', self]]"
        ], 'should hold unevaluated custom domain');
        assert.deepEqual(actual_domain.get_eval_context(), {
            self: "great"
        }, "evaluation context should hold facet value as self");

        var actual_context = f.get_context(facet);
        assert.equal(actual_context.__ref, "compound_context",
              "@context should yield compound context");
        assert.deepEqual(actual_context.__contexts, [
            "{'bob': self}"
        ], 'should hold unevaluated custom context');
        assert.deepEqual(actual_context.get_eval_context(), {
            self: "great"
        }, "evaluation context should hold facet value as self");
    });

    test("M2O default", function (assert, search_inputs, SearchView, core) {
        var Facet = SearchView.Facet;

        var ManyToOneField = core.search_widgets_registry.get('many2one');

        var f = new ManyToOneField(
            {}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        assert.deepEqual(f.get_domain(facet), [['foo', '=', 42]],
            "m2o should use identity if default domain");
        assert.deepEqual(f.get_context(facet), {default_foo: 42},
            "m2o should use value as context default");
    });

    test("M2O default multiple values", function (assert, search_inputs, SearchView, core) {
        var Facet = SearchView.Facet;
        var ManyToOneField = core.search_widgets_registry.get('many2one');

        var f = new ManyToOneField(
            {}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [
                {label: "Foo", value: 42},
                {label: "Bar", value: 36}
            ]
        });

        assert.deepEqual(f.get_domain(facet).__domains,
            [['|'], [['foo', '=', 42]], [['foo', '=', 36]]],
            "m2o should or multiple values");
        assert.equal(f.get_context(facet), null,
            "m2o should not have default context in case of multiple values");
    });

    test("M2O custom operator", function (assert, search_inputs, SearchView, core) {
        var Facet = SearchView.Facet;
        var ManyToOneField = core.search_widgets_registry.get('many2one');
        var f = new ManyToOneField(
            {attrs: {operator: 'boos'}}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        assert.deepEqual(f.get_domain(facet), [['foo', 'boos', 'Foo']],
            "m2o should use label with custom operators");
        assert.deepEqual(f.get_context(facet), {default_foo: 42},
            "m2o should use value as context default");
    });

    test("M2O custom domain & context", function (assert, search_inputs, SearchView, core) {
        var Facet = SearchView.Facet;
        var ManyToOneField = core.search_widgets_registry.get('many2one');

        var f = new ManyToOneField({attrs: {
            context: "{'whee': self}",
            filter_domain: "[['filter', 'is', self]]"
        }}, {name: 'foo'}, {inputs: []});
        var facet = new Facet({
            field: f,
            values: [{label: "Foo", value: 42}]
        });

        var domain = f.get_domain(facet);
        assert.deepEqual(domain.__domains, [
            "[['filter', 'is', self]]"
        ]);
        assert.deepEqual(domain.get_eval_context(), {
            self: "Foo"
        }, "custom domain's self should be label");
        var context = f.get_context(facet);
        assert.deepEqual(context.__contexts, [
            "{'whee': self}"
        ]);
        assert.deepEqual(context.get_eval_context(), {
            self: "Foo"
        }, "custom context's self should be label");
    });

    test('FilterGroup', function (assert, search_inputs, SearchView) {
        assert.expect(6);

        var Facet = SearchView.Facet;
        var Filter = search_inputs.Filter;
        var FilterGroup = search_inputs.FilterGroup;

        var view = {inputs: [], query: {on: function () {}}};
        var filter_a = new Filter(
            {attrs: {name: 'a', context: '{"c1": True}', domain: 'd1'}}, view);
        var filter_b = new Filter(
            {attrs: {name: 'b', context: '{"c2": True}', domain: 'd2'}}, view);
        var filter_c = new Filter(
            {attrs: {name: 'c', context: '{"c3": True}', domain: 'd3'}}, view);
        var group = new FilterGroup(
            [filter_a, filter_b, filter_c], view);
        return group.facet_for_defaults({a: true, c: true})
            .done(function (facet) {
                var model = facet;
                if (!(model instanceof Facet)) {
                    model = new Facet(facet);
                }

                var domain = group.get_domain(model);
                assert.equal(domain.__ref, 'compound_domain',
                    "domain should be compound");
                assert.deepEqual(domain.__domains, [
                    ['|'], 'd1', 'd3'
                ], "domain should OR filter domains");
                ok(!domain.get_eval_context(), "domain should have no evaluation context");
                var context = group.get_context(model);
                assert.equal(context.__ref, 'compound_context',
                    "context should be compound");
                assert.deepEqual(context.__contexts, [
                    '{"c1": True}', '{"c3": True}'
                ], "context should merge all filter contexts");
                assert.ok(!context.get_eval_context(), "context should have no evaluation context");
            });
    });

    test('Empty filter domains', {asserts: 4}, function (assert, search_inputs, SearchView) {
        assert.expect(4);

        var Facet = SearchView.Facet;
        var Filter = search_inputs.Filter;
        var FilterGroup = search_inputs.FilterGroup;

        var view = {inputs: [], query: {on: function () {}}};
        var filter_a = new Filter(
            {attrs: {name: 'a', context: '{}', domain: '[]'}}, view);
        var filter_b = new Filter(
            {attrs: {name: 'b', context: '{}', domain: '[]'}}, view);
        var filter_c = new Filter(
            {attrs: {name: 'c', context: '{b: 42}', domain: '[["a", "=", 3]]'}}, view);
        var group = new FilterGroup(
            [filter_a, filter_b, filter_c], view);
        var t1 = group.facet_for_defaults({a: true, c: true})
        .done(function (facet) {
            var model = facet;
            if (!(model instanceof Facet)) {
                model = new Facet(facet);
            }

            var domain = group.get_domain(model);
            assert.deepEqual(domain, '[["a", "=", 3]]', "domain should ignore empties");
            var context = group.get_context(model);
            assert.deepEqual(context, '{b: 42}', "context should ignore empties");
        });

        var t2 = group.facet_for_defaults({a: true, b: true})
        .done(function (facet) {
            var model = facet;
            if (!(model instanceof Facet)) {
                model = new Facet(facet);
            }

            var domain = group.get_domain(model);
            assert.equal(domain, null, "domain should ignore empties");
            var context = group.get_context(model);
            assert.equal(context, null, "context should ignore empties");
        });
        return $.when(t1, t2);
    });
});

odoo.define_section('search.serialization', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('is-drawn', function (assert) {
        assert.expect(3);
        var view = makeSearchView(this, false, false, {$buttons: $('<div>')});
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                assert.ok(view.$buttons.find('.filters-menu').length,
                   "filters menu has been drawn");
                assert.ok(view.$buttons.find('.group-by-menu').length,
                   "group by menu has been drawn");
                assert.ok(view.$buttons.find('.o_favorites_menu').length,
                   "favorites menu has been drawn");
            });
    });

});

odoo.define_section('search.filters', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {
    function setup () {
        mock.add('dummy.model:fields_view_get', function () {
            // view with a single group of filters
            return {
                type: 'search',
                fields: {},
                arch: '<search>' +
                        '<filter string="Foo1" domain="[ [\'foo\', \'=\', \'1\'] ]"/>' +
                        '<filter name="foo2" string="Foo2" domain="[ [\'foo\', \'=\', \'2\'] ]"/>' +
                        '<filter string="Foo3" domain="[ [\'foo\', \'=\', \'3\'] ]"/>' +
                        '</search>',
            };
        });
    }

    test('drawn', function (assert) {
        setup();
        assert.expect(3);
        var view = makeSearchView(this);
        var $fix = $('#qunit-fixture');

        return view.appendTo($fix)
            .done(function () {
                var $filters = view.$buttons.find('.filters-menu li'),
                    $favorites = view.$buttons.find('.o_favorites_menu li'),
                    $groupby = view.$buttons.find('.group-by-menu li');
                // 3 filters, 1 separator, 1 button add filter, 
                // 1 filter condition menu, 1 apply button
                assert.equal($filters.length, 7,
                      'filter menu should have 7 elements total');

                // 1 divider, 1 save search button, 1 text input, 2 checkboxes, 
                // 1 save button, 3 add to dashboard things (a, input, button)
                // this test is disabled because the number of elements depends on
                // the various addons installed.
                // assert.equal($favorites.length, 9,
                //       "favorites menu should have 9 elements");

                // 1 divider, 1 add custom group button, 1 select groupby, 1 apply button,
                assert.equal($groupby.length, 4,
                      "groupby menu should have 4 element");
                assert.equal(_.str.strip($filters.find('a')[0].textContent), "Foo1",
                      "Text content of first filter option should match filter string");
            });
    });

    test('click adding from empty query', function (assert, search_inputs) {
        assert.expect(4);
        setup();
        var Filter = search_inputs.Filter;

        var view = makeSearchView(this);
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $fs = view.$buttons.find('.filters-menu li a');
                $fs.eq(2).trigger('click');
                assert.equal(view.query.length, 1, "click should have added a facet");
                var facet = view.query.at(0);
                assert.equal(facet.values.length, 1, "facet should have a single value");
                var value = facet.values.at(0);
                assert.ok(value.get('value') instanceof Filter,
                   "value should be a filter");
                assert.equal(value.get('label'), "Foo3",
                      "value should be third filter");
            });
    });

    test('click adding from existing query', function (assert) {
        assert.expect(4);
        setup();
        var view = makeSearchView(this, {}, {foo2: true});

        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $fs = view.$buttons.find('.filters-menu li a');
                $fs.eq(2).trigger('click');
                assert.equal(view.query.length, 1, "click should not have changed facet count");
                var facet = view.query.at(0);
                assert.equal(facet.values.length, 2, "facet should have a second value");
                var v1 = facet.values.at(0);
                assert.equal(v1.get('label'), "Foo2",
                      "first value should be default");
                var v2 = facet.values.at(1);
                assert.equal(v2.get('label'), "Foo3",
                      "second value should be clicked filter");
            });
    });


    test('click removing from query', function (assert) {
        assert.expect(4);
        setup();

        var calls = 0;
        var view = makeSearchView(this, {}, {foo2: true});
        view.on('search_data', null, function () {
            ++calls;
        });
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $fs = view.$buttons.find('.filters-menu li a');
                // sanity check
                assert.equal(view.query.length, 1, "query should have default facet");
                assert.strictEqual(calls, 0);
                $fs.eq(1).trigger('click');
                assert.equal(view.query.length, 0, "click should have removed facet");
                assert.strictEqual(calls, 1, "one search should have been triggered");
            });
    });
});

odoo.define_section('search.groupby', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('basic', ['web.FavoriteMenu', 'web.FilterMenu', 'web.GroupByMenu'], function (assert, search_inputs, SearchView, core, data, FavoriteMenu, FilterMenu, GroupByMenu) {
        assert.expect(12);
        mock.add('dummy.model:fields_view_get', function () {
            return {
                type: 'search',
                fields: {},
                arch: [
                    '<search>',
                        '<filter string="Foo" context="{\'group_by\': \'foo\'}"/>',
                        '<filter string="Bar" context="{\'group_by\': \'bar\'}"/>',
                        '<filter string="Baz" context="{\'group_by\': \'baz\'}"/>',
                    '</search>'
                ].join(''),
            };
        });
        var view = makeSearchView(this);
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
        .done(function () {
            assert.equal(view.search_fields.length, 0); // 0 fields
            assert.equal(view.filters.length, 0); // 0 filters (in filter menu)
            assert.equal(view.groupbys.length, 1); // 1 group of groupbys
            var group = view.groupbys[0];
            assert.ok(group instanceof search_inputs.GroupbyGroup, 
                    'should have a GroupbyGroup input');
            assert.equal(group.filters.length, 3); // 3 group bys in group
            assert.ok(group.getParent() === view,
                "group's parent should be the searchview");

            group.toggle(group.filters[0]);
            group.toggle(group.filters[2]);

            var results = view.build_search_data();
            assert.deepEqual(results.domains, [], "should have no domain");
            assert.deepEqual(results.contexts, [
                new data.CompoundContext(
                    "{'group_by': 'foo'}", "{'group_by': 'baz'}")
            ], "should have compound contexts");
            assert.deepEqual(results.groupbys, [
                "{'group_by': 'foo'}",
                "{'group_by': 'baz'}"
            ], "should have sequence of contexts");

            assert.ok(view.filter_menu instanceof FilterMenu, 'should have a filter menu');
            assert.ok(view.groupby_menu instanceof GroupByMenu, 'should have a group by menu');
            assert.ok(view.favorite_menu instanceof FavoriteMenu, 'should have a favorite menu');
        });
    });

    test('unified multiple groupby groups', function (assert, search_inputs, SearchView, core, data) {
        assert.expect(3);
        mock.add('dummy.model:fields_view_get', function () {
            return {
                type: 'search',
                fields: {},
                arch: [
                    '<search>',
                        '<filter string="Foo" context="{\'group_by\': \'foo\'}"/>',
                        '<separator/>',
                        '<filter string="Bar" context="{\'group_by\': \'bar\'}"/>',
                        '<separator/>',
                        '<filter string="Baz" context="{\'group_by\': \'baz\'}"/>',
                    '</search>'
                ].join(''),
            };
        });
        var view = makeSearchView(this);
        var $fix = $('#qunit-fixture');

        return view.appendTo($fix)
        .done(function () {
            var groups = view.groupbys;
            assert.equal(groups.length, 3, "should have 3 GroupbyGroups");

            groups[0].toggle(groups[0].filters[0]);
            groups[2].toggle(groups[2].filters[0]);
            assert.equal(view.query.length, 1,
                  "should have unified groupby groups in single facet");
            assert.deepEqual(view.build_search_data(), {
                domains: [],
                contexts: [new data.CompoundContext(
                    "{'group_by': 'foo'}", "{'group_by': 'baz'}")],
                groupbys: [ "{'group_by': 'foo'}", "{'group_by': 'baz'}" ],
            }, "should only have contexts & groupbys in search data");
        });
    });
});

odoo.define_section('search.filters.saved', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('checkboxing', function (assert) {
        assert.expect(6);
        var view = makeSearchView(this, undefined, undefined, {action: {id: 1}});
        mock.add('ir.filters:get_filters', function () {
            return [{ name: "filter name", user_id: 42 }];
        });

        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $li = view.favorite_menu.$el.find('li:first').click();

                assert.ok($li.hasClass('selected'), "should check/select the filter's row");
                assert.ok($li.hasClass("oe_searchview_custom_private"),
                    "should have private filter note/class");
                assert.equal(view.query.length, 1, "should have only one facet");
                var values = view.query.at(0).values;
                assert.equal(values.length, 1,
                    "should have only one value in the facet");
                assert.equal(values.at(0).get('label'), 'filter name',
                    "displayed label should be the name of the filter");
                assert.equal(values.at(0).get('value'), null,
                    "should have no value set");
            });
    });

    test('removal', function (assert) {
        assert.expect(1);
        var view = makeSearchView(this);
        mock.add('ir.filters:get_filters', function () {
            return [{ name: "filter name", user_id: 42 }];
        });

        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $row = view.favorite_menu.$el.find('li:first').click();

                view.query.remove(view.query.at(0));
                assert.ok(!$row.hasClass('selected'),
                    "should not be checked anymore");
            });
    });

    test('toggling', function (assert) {
        assert.expect(2);
        var view = makeSearchView(this, undefined, undefined, {action: {id: 1}});
        mock.add('ir.filters:get_filters', function () {
            return [{name: 'filter name', user_id: 42, id: 1}];
        });

        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $row = view.favorite_menu.$el.find('li:first').click();
                assert.equal(view.query.length, 1, "should have one facet");
                $row.click();
                assert.equal(view.query.length, 0, "should have removed facet");
            });
    });

    test('replacement', function (assert) {
        assert.expect(4);

        var view = makeSearchView(this, undefined, undefined, {action: {id: 1}});
        mock.add('ir.filters:get_filters', function () {
            return [
                {name: 'f', user_id: 42, id: 1, context: {'private': 1}},
                {name: 'f', user_id: false, id: 2, context: {'private': 0}}
            ];
        });
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                view.favorite_menu.$el.find('li:first').click();
                assert.equal(view.query.length, 1, "should have one facet");
                assert.deepEqual(
                    view.query.at(0).get('field').get_context(),
                    {'private': 1},
                    "should have selected first filter");
                view.favorite_menu.$el.find('li').eq(1).click();
                assert.equal(view.query.length, 1, "should have one facet");
                assert.deepEqual(
                    view.query.at(0).get('field').get_context(),
                    {'private': 0},
                    "should have selected second filter");
            });
    });

    test('creation', ['web.session'], function (assert, search_inputs, SearchView, core, data, session) {
        assert.expect(2);
        // force a user context
        session.user_context = {foo: 'bar'};

        var view = makeSearchView(this);
        var done = $.Deferred();

        mock.add('ir.filters:get_filters', function () { return []; });
        mock.add('ir.filters:create_or_replace', function (args) {
            var filter = args[0];
            assert.deepEqual(filter.context, {}, "should have empty context");
            assert.deepEqual(filter.domain, [], "should have empty domain");
            done.resolve();
        });
        var $fix = $('#qunit-fixture');
        return view.appendTo($fix)
        .then(function () {
            view.favorite_menu.$el.find('.oe-save-name input').first().val("filter name");
            view.favorite_menu.$el.find('.oe-save-name button').click();
            return done.promise();
        });
    });
});

odoo.define_section('search.advanced', ['web.search_inputs', 'web.SearchView', 'web.core', 'web.data'], function (test, mock) {

    test('single-advanced', function (assert) {
        assert.expect(6);
        var view = makeSearchView(this);

        var $fix = $('qunit-fixture');
        return view.appendTo($fix)
            .done(function () {
                var $filter_menu = view.filter_menu.$el;
                // open advanced search (not actually useful)
                $filter_menu.find('.oe-add-filter').click();
                // select proposition (only one)
                var $prop = $filter_menu.find('.oe-filter-condition');
                // field select should have two possible values, dummy and id
                assert.equal($prop.find('select:first option').length,
                      2, "advanced search should provide choice between two fields");
                // field should be dummy
                assert.equal($prop.find('select:first').val(),
                      'dummy',
                      "only field should be dummy");
                // operator should be "contains"/'ilike'
                assert.equal($prop.find('.searchview_extended_prop_op').val(),
                      'ilike', "default char operator should be ilike");
                // put value in
                $prop.find('.searchview_extended_prop_value input')
                     .val("stupid value");
                // validate advanced search
                $filter_menu.find('button.oe-apply-filter').click();
                // resulting search
                assert.equal(view.query.length, 1, "search query should have a single facet");
                var facet = view.query.at(0);
                assert.ok(!facet.get('field').get_context(facet),
                   "advanced search facets should yield no context");
                assert.deepEqual(facet.get('field').get_domain(facet),
                          [['dummy', 'ilike', "stupid value"]],
                          "advanced search facet should return proposed domain");
            });
    });

    test('multiple-advanced', function (assert) {
        assert.expect(3);
        var view = makeSearchView(this);

        var $fix = $('qunit-fixture');

        return view.appendTo($fix)
            .done(function () {
                var $filter_menu = view.filter_menu.$el;
                // open advanced search (not actually useful)
                $filter_menu.find('.oe-add-filter').click();
                // open second condition
                $filter_menu.find('a.oe-add-condition').click();

                // select first proposition
                var $prop1 = $filter_menu.find('.oe-filter-condition:first');
                $prop1.find('select.searchview_extended_prop_field').val("dummy").change();
                $prop1.find('select.searchview_extended_prop_op').val('ilike');
                $prop1.find('.searchview_extended_prop_value input')
                     .val("stupid value");

                // select first proposition
                var $prop2 = $filter_menu.find('.oe-filter-condition:last');
                // need to trigger event manually or op not changed
                $prop2.find('select.searchview_extended_prop_field').val('id').change();
                $prop2.find('select.searchview_extended_prop_op').val('=');
                $prop2.find('.searchview_extended_prop_value input')
                     .val(42);
                // validate advanced search
                $filter_menu.find('button.oe-apply-filter').click();

                // resulting search
                assert.equal(view.query.length, 1, "search query should have a single facet");
                var facet = view.query.at(0);
                assert.ok(!facet.get('field').get_context(facet),
                   "advanced search facets should yield no context");
                assert.deepEqual(facet.get('field').get_domain(facet).eval(),
                          ['|', ['dummy', 'ilike', "stupid value"],
                                ['id', '=', 42]],
                          "advanced search facet should return proposed domain");
            });
    });

});


