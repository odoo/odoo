odoo.define('web.data_comparison_utils_tests', function(require) {
"use strict";

var dataComparisonUtils = require('web.dataComparisonUtils');
var DateClasses = dataComparisonUtils.DateClasses;

QUnit.module('dataComparisonUtils', function () {

    QUnit.module('DateClasses');


    QUnit.test('main parameters are correctly computed', function(assert) {
        assert.expect(30);

        var dateClasses;

        dateClasses = new DateClasses([['2019']]);
        assert.strictEqual(dateClasses.referenceIndex, 0);
        assert.strictEqual(dateClasses.dateClass(0, '2019'), 0);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2019']);

        dateClasses = new DateClasses([['2018', '2019']]);
        assert.strictEqual(dateClasses.referenceIndex, 0);
        assert.strictEqual(dateClasses.dateClass(0, '2018'), 0);
        assert.strictEqual(dateClasses.dateClass(0, '2019'), 1);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2018']);
        assert.deepEqual(dateClasses.dateClassMembers(1), ['2019']);

        dateClasses = new DateClasses([['2019'], []]);
        assert.strictEqual(dateClasses.referenceIndex, 0);
        assert.strictEqual(dateClasses.dateClass(0, '2019'), 0);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2019']);

        dateClasses = new DateClasses([[], ['2019']]);
        assert.strictEqual(dateClasses.referenceIndex, 1);
        assert.strictEqual(dateClasses.dateClass(1, '2019'), 0);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2019']);

        dateClasses = new DateClasses([['2019'],['2018', '2019']]);
        assert.strictEqual(dateClasses.referenceIndex, 0);
        assert.strictEqual(dateClasses.dateClass(0, '2019'), 0);
        assert.strictEqual(dateClasses.dateClass(1, '2018'), 0);
        assert.strictEqual(dateClasses.dateClass(1, '2019'), 1);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2019', '2018']);
        assert.deepEqual(dateClasses.dateClassMembers(1), ['2019']);


        dateClasses = new DateClasses([['2019'], ['2017', '2018', '2020'], ['2017', '2019']]);
        assert.strictEqual(dateClasses.referenceIndex, 0);
        assert.strictEqual(dateClasses.dateClass(0, '2019'), 0);
        assert.strictEqual(dateClasses.dateClass(1, '2017'), 0);
        assert.strictEqual(dateClasses.dateClass(1, '2018'), 1);
        assert.strictEqual(dateClasses.dateClass(1, '2020'), 2);
        assert.strictEqual(dateClasses.dateClass(2, '2017'), 0);
        assert.strictEqual(dateClasses.dateClass(2, '2019'), 1);
        assert.deepEqual(dateClasses.dateClassMembers(0), ['2019', '2017']);
        assert.deepEqual(dateClasses.dateClassMembers(1), ['2018', '2019']);
        assert.deepEqual(dateClasses.dateClassMembers(2), ['2020']);


    });

    QUnit.test('two overlapping datesets and classes representatives', function(assert) {
        assert.expect(4);

        var dateClasses = new DateClasses([['March 2017'], ['February 2017', 'March 2017']]);

        assert.strictEqual(dateClasses.representative(0, 0), 'March 2017');
        assert.strictEqual(dateClasses.representative(0, 1), 'February 2017');

        assert.strictEqual(dateClasses.representative(1, 0), undefined);
        assert.strictEqual(dateClasses.representative(1, 1), 'March 2017');
    });
});
});
