/** @odoo-module **/

/**
 * Transform a 2D point using a projective transformation matrix. Note that
 * this method is only well behaved for points that don't map to infinity!
 *
 * @param {number[][]} matrix - A projective transformation matrix
 * @param {number[]} point - A 2D point
 * @returns The transformed 2D point
 */
export function transform([[a, b, c], [d, e, f], [g, h, i]], [x, y]) {
    let z = g * x + h * y + i;
    return [(a * x + b * y + c) / z, (d * x + e * y + f) / z];
}

/**
 * Calculate the inverse of a 3x3 matrix assuming it is invertible.
 *
 * @param {number[][]} matrix - A 3x3 matrix
 * @returns The resulting 3x3 matrix
 */
function invert([[a, b, c], [d, e, f], [g, h, i]]) {
    const determinant = a * e * i - a * f * h - b * d * i + b * f * g + c * d * h - c * e * g;
    return [
        [(e * i - h * f) / determinant, (h * c - b * i) / determinant, (b * f - e * c) / determinant],
        [(g * f - d * i) / determinant, (a * i - g * c) / determinant, (d * c - a * f) / determinant],
        [(d * h - g * e) / determinant, (g * b - a * h) / determinant, (a * e - d * b) / determinant],
    ];
}

/**
 * Multiply two 3x3 matrices.
 *
 * @param {number[][]} a - A 3x3 matrix
 * @param {number[][]} b - A 3x3 matrix
 * @returns The resulting 3x3 matrix
 */
function multiply(a, b) {
    const [[a0, a1, a2], [a3, a4, a5], [a6, a7, a8]] = a;
    const [[b0, b1, b2], [b3, b4, b5], [b6, b7, b8]] = b;
    return [
        [a0 * b0 + a1 * b3 + a2 * b6, a0 * b1 + a1 * b4 + a2 * b7, a0 * b2 + a1 * b5 + a2 * b8],
        [a3 * b0 + a4 * b3 + a5 * b6, a3 * b1 + a4 * b4 + a5 * b7, a3 * b2 + a4 * b5 + a5 * b8],
        [a6 * b0 + a7 * b3 + a8 * b6, a6 * b1 + a7 * b4 + a8 * b7, a6 * b2 + a7 * b5 + a8 * b8],
    ];
}

/**
 * Find a projective transformation mapping a rectangular area at origin (0,0)
 * with a given width and height to a certain quadrilateral.
 *
 * @param {number} width - The width of the rectangular area
 * @param {number} height - The height of the rectangular area
 * @param {number[][]} quadrilateral - The vertices of the quadrilateral
 * @returns A projective transformation matrix
 */
export function getProjective(width, height, [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]) {
    // Calculate a set of homogeneous coordinates a, b, c of the first
    // point using the other three points as basis vectors in the
    // underlying vector space.
    const denominator = x3 * (y1 - y2) + x1 * (y2 - y3) + x2 * (y3 - y1);
    const a = (x0 * (y2 - y3) + x2 * (y3 - y0) + x3 * (y0 - y2)) / denominator;
    const b = (x0 * (y3 - y1) + x3 * (y1 - y0) + x1 * (y0 - y3)) / denominator;
    const c = (x0 * (y1 - y2) + x1 * (y2 - y0) + x2 * (y0 - y1)) / denominator;

    // The reverse transformation maps the homogeneous coordinates of
    // the last three corners of the original image onto the basis vectors
    // while mapping the first corner onto (1, 1, 1). The forward
    // transformation maps those basis vectors in addition to (1, 1, 1)
    // onto homogeneous coordinates of the corresponding corners of the
    // projective image. Combining these together yields the projective
    // transformation we are looking for.
    const reverse = invert([[width, -width, 0], [0, -height, height], [1, -1, 1]]);
    const forward = [[a * x1, b * x2, c * x3], [a * y1, b * y2, c * y3], [a, b, c]];

    return multiply(forward, reverse);
}

/**
 * Find an affine transformation matrix that exactly maps the vertices of a
 * triangle to their corresponding images of a projective transformation. The
 * resulting transformation will be an approximation of the projective
 * transformation for the area inside the triangle.
 *
 * @param {number[][]} projective - A projective transformation matrix
 * @param {number[][]} triangle - The vertices of a triangle
 * @returns - An affine transformation matrix
 */
export function getAffineApproximation(projective, [[x0, y0], [x1, y1], [x2, y2]]) {
    const a = transform(projective, [x0, y0]);
    const b = transform(projective, [x1, y1]);
    const c = transform(projective, [x2, y2]);

    return multiply(
        [[a[0], b[0], c[0]], [a[1], b[1], c[1]], [1, 1, 1]],
        invert([[x0, x1, x2], [y0, y1, y2], [1, 1, 1]]),
    );
}
