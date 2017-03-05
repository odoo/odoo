odoo.define('web.search_tests', function (require) {
"use strict";

var SearchView = require('web.SearchView');

QUnit.module('chrome', {}, function () {

    QUnit.module('Search View');

    QUnit.test('Adding a facet to the query creates a facet and a value', function (assert) {
        assert.expect(3);

        var query = new SearchView.SearchQuery();
        var field = {};
        query.add({
            category: 'Foo',
            field: field,
            values: [{label: 'Value', value: 3}]
        });

        var facet = query.at(0);
        assert.strictEqual(facet.get('category'), 'Foo');
        assert.strictEqual(facet.get('field'), field);
        assert.deepEqual(facet.get('values'), [{label: 'Value', value: 3}]);
    });

    QUnit.test('Adding two facets', function (assert) {
        assert.expect(3);

        var query = new SearchView.SearchQuery();
        query.add([
            { category: 'Foo', field: {}, values: [{label: 'Value', value: 3}] },
            { category: 'Bar', field: {}, values: [{label: 'Value 2', value: 4}] }
        ]);

        assert.strictEqual(query.length, 2);
        assert.strictEqual(query.at(0).values.length, 1);
        assert.strictEqual(query.at(1).values.length, 1);
    });

    QUnit.test('If a facet already exists, add values to it', function (assert) {
        assert.expect(2);

        var query = new SearchView.SearchQuery();
        var field = {};
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.strictEqual(query.length, 1, "adding an existing facet should merge new values into old facet");
        var facet = query.at(0);
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

    QUnit.test('Facet being implicitly changed should trigger change, not add', function (assert) {
        assert.expect(2);

        var query = new SearchView.SearchQuery();
        var field = {}, added = false, changed = false;
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.on('add', function () { added = true; })
                .on('change', function () { changed = true; });
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.ok(!added, "query.add adding values to a facet should not trigger an add");
        assert.ok(changed, "query.add adding values to a facet should not trigger a change");
    });

    QUnit.test('Toggling a facet, value which does not exist should add it', function (assert) {
        assert.expect(3);

        var query = new SearchView.SearchQuery();
        var field = {};
        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        assert.strictEqual(query.length, 1, "Should have created a single facet");
        var facet = query.at(0);
        assert.strictEqual(facet.values.length, 1, "Facet should have a single value");
        assert.deepEqual(facet.get('values'), [{label: 'V1', value: 0}],
                    "Facet's value should match input");
    });

    QUnit.test('Toggling a facet which exists with a value which does not should add the value to the facet', function (assert) {
        assert.expect(3);

        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.strictEqual(query.length, 1, "Should have edited the existing facet");
        var facet = query.at(0);
        assert.strictEqual(facet.values.length, 2, "Should have added the value to the existing facet");
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

    QUnit.test('Toggling a facet which exists with a value which does as well should remove the value from the facet', function (assert) {
        assert.expect(3);

        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});
        query.add({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V2', value: 1}]});

        assert.strictEqual(query.length, 1, 'Should have the same single facet');
        var facet = query.at(0);
        assert.strictEqual(facet.values.length, 1, "Should only have one value left in the facet");
        assert.deepEqual(facet.get('values'), [
            {label: 'V1', value: 0}
        ]);
    });

    QUnit.test('Toggling off the last value of a facet should remove the facet', function (assert) {
        assert.expect(1);

        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        assert.strictEqual(query.length, 0, 'Should have removed the facet');
    });


    QUnit.test('Intermediate emptiness should not remove the facet', function (assert) {
        assert.expect(3);

        var field = {};
        var query = new SearchView.SearchQuery();
        query.add({category: 'A', field: field, values: [{label: 'V1', value: 0}]});

        query.toggle({category: 'A', field: field, values: [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]});

        assert.strictEqual(query.length, 1, 'Should not have removed the facet');
        var facet = query.at(0);
        assert.strictEqual(facet.values.length, 1, "Should have one value");
        assert.deepEqual(facet.get('values'), [
            {label: 'V2', value: 1}
        ]);
    });

    QUnit.test('Reseting with multiple facets should still work to load defaults', function (assert) {
        assert.expect(3);

        var query = new SearchView.SearchQuery();
        var field = {};
        query.reset([
            {category: 'A', field: field, values: [{label: 'V1', value: 0}]},
            {category: 'A', field: field, values: [{label: 'V2', value: 1}]}]);

        assert.strictEqual(query.length, 1, 'Should have created a single facet');
        assert.strictEqual(query.at(0).values.length, 2, 'the facet should have merged two values');
        assert.deepEqual(query.at(0).get('values'), [
            {label: 'V1', value: 0},
            {label: 'V2', value: 1}
        ]);
    });

});
});
