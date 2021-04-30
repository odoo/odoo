odoo.define('point_of_sale.unit.test_posRound', function (require) {
    'use strict';

    const { posRound } = require('point_of_sale.utils');
    const { float_is_zero } = require('web.utils');

    const N_DECIMAL = 6;

    function createChecker(assert, rounder) {
        return function (valueToRound, prec, expectedRoundedValue) {
            const rounded = rounder(valueToRound, prec);
            const msg = `round(${valueToRound}, ${prec}) result to ${rounded}, expected: ${expectedRoundedValue}`;
            assert.ok(float_is_zero(rounded - expectedRoundedValue, N_DECIMAL), msg);
        };
    }

    QUnit.module('unit tests for posRound', {});

    QUnit.test('round HALF-UP, assume default epsilon of 1e-6', async function (assert) {
        assert.expect(44);
        const roundHalfUp = (value, prec) => posRound(value, prec, 'HALF-UP', N_DECIMAL);
        const _check = createChecker(assert, roundHalfUp);

        _check(10, 0.05, 10);
        _check(10.01, 0.05, 10);
        _check(10.02, 0.05, 10);
        _check(10.03, 0.05, 10.05);
        _check(10.04, 0.05, 10.05);
        _check(10.05, 0.05, 10.05);
        _check(10.06, 0.05, 10.05);
        _check(10.07, 0.05, 10.05);
        _check(10.08, 0.05, 10.1);
        _check(10.09, 0.05, 10.1);
        _check(10.1, 0.05, 10.1);

        _check(10, 0.02, 10);
        _check(10.01, 0.02, 10.02);
        _check(10.02, 0.02, 10.02);
        _check(10.03, 0.02, 10.04);
        _check(10.04, 0.02, 10.04);
        _check(10.05, 0.02, 10.06);
        _check(10.06, 0.02, 10.06);
        _check(10.07, 0.02, 10.08);
        _check(10.08, 0.02, 10.08);
        _check(10.09, 0.02, 10.1);
        _check(10.1, 0.02, 10.1);

        _check(-10, 0.05, -10);
        _check(-10.01, 0.05, -10);
        _check(-10.02, 0.05, -10);
        _check(-10.03, 0.05, -10.05);
        _check(-10.04, 0.05, -10.05);
        _check(-10.05, 0.05, -10.05);
        _check(-10.06, 0.05, -10.05);
        _check(-10.07, 0.05, -10.05);
        _check(-10.08, 0.05, -10.1);
        _check(-10.09, 0.05, -10.1);
        _check(-10.1, 0.05, -10.1);

        _check(-10, 0.02, -10);
        _check(-10.01, 0.02, -10);
        _check(-10.02, 0.02, -10.02);
        _check(-10.03, 0.02, -10.02);
        _check(-10.04, 0.02, -10.04);
        _check(-10.05, 0.02, -10.04);
        _check(-10.06, 0.02, -10.06);
        _check(-10.07, 0.02, -10.06);
        _check(-10.08, 0.02, -10.08);
        _check(-10.09, 0.02, -10.08);
        _check(-10.1, 0.02, -10.1);
    });

    QUnit.test('round UP, assume default epsilon of 1e-6', async function (assert) {
        assert.expect(56);
        const roundHalfUp = (value, prec) => posRound(value, prec, 'UP', N_DECIMAL);
        const _check = createChecker(assert, roundHalfUp);

        _check(10, 0.02, 10);
        _check(10.01, 0.02, 10.02);
        _check(10.02, 0.02, 10.02);
        _check(10.03, 0.02, 10.04);
        _check(10.04, 0.02, 10.04);
        _check(10.05, 0.02, 10.06);
        _check(10.06, 0.02, 10.06);
        _check(10.07, 0.02, 10.08);
        _check(10.08, 0.02, 10.08);
        _check(10.09, 0.02, 10.1);
        _check(10.1, 0.02, 10.1);

        _check(10, 0.03, 10.02);
        _check(10.01, 0.03, 10.02);
        _check(10.02, 0.03, 10.02);
        _check(10.03, 0.03, 10.05);
        _check(10.04, 0.03, 10.05);
        _check(10.05, 0.03, 10.05);
        _check(10.06, 0.03, 10.08);
        _check(10.07, 0.03, 10.08);
        _check(10.08, 0.03, 10.08);
        _check(10.09, 0.03, 10.11);
        _check(10.1, 0.03, 10.11);
        _check(10.11, 0.03, 10.11);

        _check(10, 0.05, 10);
        _check(10.01, 0.05, 10.05);
        _check(10.02, 0.05, 10.05);
        _check(10.03, 0.05, 10.05);
        _check(10.04, 0.05, 10.05);
        _check(10.05, 0.05, 10.05);
        _check(10.06, 0.05, 10.1);
        _check(10.07, 0.05, 10.1);
        _check(10.08, 0.05, 10.1);
        _check(10.09, 0.05, 10.1);
        _check(10.1, 0.05, 10.1);

        _check(-10, 0.02, -10);
        _check(-10.01, 0.02, -10);
        _check(-10.02, 0.02, -10.02);
        _check(-10.03, 0.02, -10.02);
        _check(-10.04, 0.02, -10.04);
        _check(-10.05, 0.02, -10.04);
        _check(-10.06, 0.02, -10.06);
        _check(-10.07, 0.02, -10.06);
        _check(-10.08, 0.02, -10.08);
        _check(-10.09, 0.02, -10.08);
        _check(-10.1, 0.02, -10.1);

        _check(-10, 0.05, -10);
        _check(-10.01, 0.05, -10);
        _check(-10.02, 0.05, -10);
        _check(-10.03, 0.05, -10);
        _check(-10.04, 0.05, -10);
        _check(-10.05, 0.05, -10.05);
        _check(-10.06, 0.05, -10.05);
        _check(-10.07, 0.05, -10.05);
        _check(-10.08, 0.05, -10.05);
        _check(-10.09, 0.05, -10.05);
        _check(-10.1, 0.05, -10.1);
    });

    QUnit.test('round DOWN, assume default epsilon of 1e-6', async function (assert) {
        assert.expect(56);
        const roundHalfUp = (value, prec) => posRound(value, prec, 'DOWN', N_DECIMAL);
        const _check = createChecker(assert, roundHalfUp);

        _check(10, 0.02, 10);
        _check(10.01, 0.02, 10);
        _check(10.02, 0.02, 10.02);
        _check(10.03, 0.02, 10.02);
        _check(10.04, 0.02, 10.04);
        _check(10.05, 0.02, 10.04);
        _check(10.06, 0.02, 10.06);
        _check(10.07, 0.02, 10.06);
        _check(10.08, 0.02, 10.08);
        _check(10.09, 0.02, 10.08);
        _check(10.1, 0.02, 10.1);

        _check(10, 0.03, 9.99);
        _check(10.01, 0.03, 9.99);
        _check(10.02, 0.03, 10.02);
        _check(10.03, 0.03, 10.02);
        _check(10.04, 0.03, 10.02);
        _check(10.05, 0.03, 10.05);
        _check(10.06, 0.03, 10.05);
        _check(10.07, 0.03, 10.05);
        _check(10.08, 0.03, 10.08);
        _check(10.09, 0.03, 10.08);
        _check(10.1, 0.03, 10.08);
        _check(10.11, 0.03, 10.11);

        _check(10, 0.05, 10);
        _check(10.01, 0.05, 10);
        _check(10.02, 0.05, 10);
        _check(10.03, 0.05, 10);
        _check(10.04, 0.05, 10);
        _check(10.05, 0.05, 10.05);
        _check(10.06, 0.05, 10.05);
        _check(10.07, 0.05, 10.05);
        _check(10.08, 0.05, 10.05);
        _check(10.09, 0.05, 10.05);
        _check(10.1, 0.05, 10.1);

        _check(-10, 0.02, -10);
        _check(-10.01, 0.02, -10.02);
        _check(-10.02, 0.02, -10.02);
        _check(-10.03, 0.02, -10.04);
        _check(-10.04, 0.02, -10.04);
        _check(-10.05, 0.02, -10.06);
        _check(-10.06, 0.02, -10.06);
        _check(-10.07, 0.02, -10.08);
        _check(-10.08, 0.02, -10.08);
        _check(-10.09, 0.02, -10.1);
        _check(-10.1, 0.02, -10.1);

        _check(-10, 0.05, -10);
        _check(-10.01, 0.05, -10.05);
        _check(-10.02, 0.05, -10.05);
        _check(-10.03, 0.05, -10.05);
        _check(-10.04, 0.05, -10.05);
        _check(-10.05, 0.05, -10.05);
        _check(-10.06, 0.05, -10.1);
        _check(-10.07, 0.05, -10.1);
        _check(-10.08, 0.05, -10.1);
        _check(-10.09, 0.05, -10.1);
        _check(-10.1, 0.05, -10.1);
    });
});
