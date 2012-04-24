$(document).ready(function () {
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
    test('Adding an array of facet is not valid', function () {
        var query = new instance.web.search.SearchQuery;

        raises(function () {
            query.add([
                { category: 'Foo', field: {}, values: [{label: 'Value', value: 3}] },
                { category: 'Bar', field: {}, values: [{label: 'Value 2', value: 4}] }
            ]);
        });
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
    test('Intermediate emptyness should not remove the facet', function () {
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
    // TODO: if the last FacetValue of a facet is removed, the facet should be removed from the query

    test('Reseting with multiple facets should still work to load defaults', function () {
        var query = new instance.web.search.SearchQuery;
        var field = {};
        query.reset([
            {category: 'A', field: field, values: [{label: 'V1', value: 0}]},
            {category: 'B', field: field, values: [{label: 'V2', value: 1}]}]);

        equal(query.length, 1, 'Should have created a single facet');
        equal(query.at(0).values.length, 2, 'the facet should have merged two values');
        deepEqual(query.at(0).get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ])
    });
});
