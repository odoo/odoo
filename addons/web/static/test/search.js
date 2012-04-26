$(document).ready(function () {
    var xhr = QWeb2.Engine.prototype.get_xhr();
    xhr.open('GET', '/web/static/src/xml/base.xml', false);
    xhr.send(null);
    var doc = xhr.responseXML;

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

            instance.connection.responses = {};
            instance.connection.rpc_function = function (url, payload) {
                if (!(url.url in this.responses)) {
                    return $.Deferred().reject(
                        {}, 'failed',
                        _.str.sprintf("Url %s not found in mock responses",
                                      url.url)).promise();
                }
                return $.when(this.responses[url.url](payload));
            };
        }
    });

    function makeSearchView(dummy_widget_attributes) {
        instance.web.search.fields.add(
            'dummy', 'instance.dummy.DummyWidget');
        instance.dummy = {};
        instance.dummy.DummyWidget = instance.web.search.Field.extend(
            dummy_widget_attributes);
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
        instance.connection.responses['/web/searchview/get_filters'] = function () {
            return [];
        };
        instance.connection.responses['/web/searchview/fields_get'] = function () {
            return {result: {fields: {
                dummy: {type: 'char'}
            }}};
        };

        var dataset = {model: 'dummy.model', get_context: function () { return {}; }};
        return new instance.web.SearchView(null, dataset, false, {dummy: 42});
    }
    asyncTest('defaults calling', 2, function () {
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
        });
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
    // TODO: test defaults for various built-in widgets?
    asyncTest('completion calling', 4, function () {
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
});
