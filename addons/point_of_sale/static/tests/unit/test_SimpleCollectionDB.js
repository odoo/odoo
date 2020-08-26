odoo.define('point_of_sale.tests.SimpleCollectionDB', function (require) {
    'use strict';

    const SimpleCollectionDB = require('point_of_sale.SimpleCollectionDB');

    QUnit.test('basics', function (assert) {
        assert.expect(11);
        const testDB = new SimpleCollectionDB(() => 'simple-collection-test', 'testDB');

        testDB.setItem('a', { x: 1 });
        testDB.setItem('b', { y: 2 });

        assert.deepEqual(testDB.getKeys(), ['a', 'b']);
        assert.deepEqual(testDB.getItem('a'), { x: 1 });
        assert.deepEqual(testDB.getItem('b'), { y: 2 });

        testDB.setItem('a', { newX: 2 });
        assert.deepEqual(testDB.getItem('a'), { newX: 2 });

        testDB.removeItem('a');
        assert.deepEqual(testDB.getItem('a'), null);
        assert.deepEqual(testDB.getKeys(), ['b']);
        assert.deepEqual(testDB.getItems(), [{ y: 2 }]);

        testDB.removeItem('b');
        assert.deepEqual(testDB.getKeys(), []);
        assert.deepEqual(testDB.getItem('b'), null);

        testDB.setItem('b', 1);
        assert.deepEqual(testDB.getItem('b'), 1);

        testDB.clearItems();
        assert.deepEqual(testDB.getItem('b'), null);
    });

    QUnit.test('no leaks between different dbs', function (assert) {
        assert.expect(6);
        const db1 = new SimpleCollectionDB(() => 'simple-test', 'db1');
        const db2 = new SimpleCollectionDB(() => 'simple-test', 'db2');

        db1.setItem('a', { a: 1 });
        db1.setItem('b', { b: 2 });
        db1.setItem('same_key_diff_val', 'value 1');
        db2.setItem('x', { x: 10 });
        db2.setItem('y', { y: 11 });
        db2.setItem('same_key_diff_val', 'value 2');

        assert.deepEqual(db1.getKeys(), ['a', 'b', 'same_key_diff_val']);
        assert.deepEqual(db2.getKeys(), ['x', 'y', 'same_key_diff_val']);
        assert.strictEqual(db1.getItem('same_key_diff_val'), 'value 1');
        assert.strictEqual(db2.getItem('same_key_diff_val'), 'value 2');

        db1.clearItems();
        db2.clearItems();
        assert.deepEqual(db1.getKeys(), []);
        assert.deepEqual(db2.getKeys(), []);
    });
});
