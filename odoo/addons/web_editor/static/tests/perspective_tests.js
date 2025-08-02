/** @odoo-module **/

import {getAffineApproximation, getProjective, transform} from '@web_editor/js/editor/perspective_utils';

const epsilon = 100 * Number.EPSILON;

function midpoint([x0, y0], [x1, y1], weight = 0.5) {
    return [weight * (x0 + y0), (1.0 - weight) * (x1 + y1)];
}

function pointEqual(assert, a, b) {
    assert.pushResult({
        result: Math.abs(a[0] - b[0]) < epsilon && Math.abs(a[1] - b[1]) < epsilon,
        expected: `(${a[0]}, ${a[1]})`,
        actual: `(${b[0]}, ${b[1]})`,
    });
}

function notPointEqual(assert, a, b) {
    assert.pushResult({
        result: Math.abs(a[0] - b[0]) > epsilon || Math.abs(a[1] - b[1]) > epsilon,
        expected: `(${a[0]}, ${a[1]})`,
        actual: `different from (${b[0]}, ${b[1]})`,
    });
}

QUnit.module('Perspective Utils', {

}, function () {
    QUnit.test("Should correctly transform 2D points using a projective transformation", async function (assert) {
        assert.expect(3);

        const translation = [[0, 0, 3], [0, 0, 5], [0, 0, 1]];
        pointEqual(assert, transform(translation, [0, 0]), [3, 5]);

        const scale = [[2, 0, 0], [0, 0.5, 0], [0, 0, 1]];
        pointEqual(assert, transform(scale, [1, 1]), [2, 0.5]);

        const perspective = [[1, 0, 0], [0, 1, 0], [1, 1, 1]];
        pointEqual(assert, transform(perspective, [4, 5]), [0.4, 0.5]);
    });
    QUnit.test("Should find an affine approximation of a projective transformation", async function (assert) {
        assert.expect(4);

        const a = [0, 0];
        const b = [1, 0];
        const c = [0, 1];

        const projective = [[1, 2, 3], [2, 4, 5], [2, 2, 1]];
        const affine = getAffineApproximation(projective, [a, b, c]);

        pointEqual(assert, transform(projective, a), transform(affine, a));
        pointEqual(assert, transform(projective, b), transform(affine, b));
        pointEqual(assert, transform(projective, c), transform(affine, c));

        notPointEqual(assert, (projective, [1, 1]), transform(affine, [1, 1]));
    });
    QUnit.test("Should identically transform common edge points of two affine approximations", async function (assert) {
        assert.expect(3);

        const a = [0, 0];
        const b = [1, 0];
        const c = [1, 1];
        const d = [0, 1];

        const projective = [[1, 2, 3], [2, 4, 5], [2, 2, 1]];
        const affine1 = getAffineApproximation(projective, [a, b, d]);
        const affine2 = getAffineApproximation(projective, [b, c, d]);

        pointEqual(assert, transform(affine1, midpoint(b, d, 0.2)), transform(affine2, midpoint(b, d, 0.2)));
        pointEqual(assert, transform(affine1, midpoint(b, d, 0.5)), transform(affine2, midpoint(b, d, 0.5)));
        pointEqual(assert, transform(affine1, midpoint(b, d, 0.8)), transform(affine2, midpoint(b, d, 0.8)));
    });
    QUnit.test("Should find a projective transformation for a given quadrilateral", async function (assert) {
        assert.expect(4);

        const width = 2;
        const height = 3;

        const a = [0.1, 0.3];
        const b = [1.9, 0.1];
        const c = [1.7, 2.9];
        const d = [0.1, 2.8];

        const projective = getProjective(width, height, [a, b, c, d]);

        pointEqual(assert, a, transform(projective, [0, 0]));
        pointEqual(assert, b, transform(projective, [width, 0]));
        pointEqual(assert, c, transform(projective, [width, height]));
        pointEqual(assert, d, transform(projective, [0, height]));
    });
});
