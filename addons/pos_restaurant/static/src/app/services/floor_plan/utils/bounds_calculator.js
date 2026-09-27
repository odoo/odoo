import { toRad } from "./utils";

/**
 * Lightweight 2D transformation matrix for translate, rotate, scale operations
 * Represents a 2D affine transformation matrix:
 * [ a  c  tx ]
 * [ b  d  ty ]
 * [ 0  0  1  ]
 */
export class Matrix2D {
    constructor() {
        this.reset();
    }

    reset() {
        this.a = 1;
        this.b = 0;
        this.c = 0;
        this.d = 1;
        this.tx = 0;
        this.ty = 0;
        return this;
    }

    translate(x, y) {
        this.tx += this.a * x + this.c * y;
        this.ty += this.b * x + this.d * y;
        return this;
    }

    rotate(degrees) {
        const rad = toRad(degrees);
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);

        const a = this.a;
        const b = this.b;
        const c = this.c;
        const d = this.d;

        this.a = a * cos + c * sin;
        this.b = b * cos + d * sin;
        this.c = c * cos - a * sin;
        this.d = d * cos - b * sin;

        return this;
    }

    scale(sx, sy = sx) {
        this.a *= sx;
        this.b *= sx;
        this.c *= sy;
        this.d *= sy;
        return this;
    }

    transformPoint(x, y) {
        return {
            x: this.a * x + this.c * y + this.tx,
            y: this.b * x + this.d * y + this.ty,
        };
    }

    transformPointInto(x, y, out) {
        Object.assign(out, this.transformPoint(x, y));
    }
}

const _matrix = new Matrix2D();
const _p0 = { x: 0, y: 0 };
const _p1 = { x: 0, y: 0 };
const _p2 = { x: 0, y: 0 };
const _p3 = { x: 0, y: 0 };

function setBounds(bounds, left, top, right, bottom) {
    bounds.left = left;
    bounds.right = right;
    bounds.top = top;
    bounds.bottom = bottom;
    bounds.width = right - left;
    bounds.height = bottom - top;
    bounds.centerX = left + bounds.width / 2;
    bounds.centerY = top + bounds.height / 2;
}

/**
 * Calculate element bounds using transform data and element properties
 * @param {Object} element - Floor element with left, top, width, height, rotation, scale
 * @param {Object} [outBounds] - Optional output object to avoid allocation. If not provided, a new object is returned.
 * @returns {Object} Bounds with left, right, top, bottom, width, height, centerX, centerY
 */
export function calculateBoundsFromTransform(element, outBounds = null) {
    const { left, top, width, height, rotation = 0, scale = 1, isLine } = element;

    // Determine output object
    const bounds = outBounds || {
        left: 0,
        right: 0,
        top: 0,
        bottom: 0,
        width: 0,
        height: 0,
        centerX: 0,
        centerY: 0,
    };

    // Fast path for non-rotated, non-scaled rectangles
    if (rotation === 0 && scale === 1) {
        setBounds(bounds, left, top, left + width, top + height);
        // For non-rotated elements, round corners to whole pixels to avoid sub-pixel gaps
        bounds.corners = {
            topLeft: { x: Math.round(left), y: Math.round(top) },
            topRight: { x: Math.round(left + width), y: Math.round(top) },
            bottomRight: { x: Math.round(left + width), y: Math.round(top + height) },
            bottomLeft: { x: Math.round(left), y: Math.round(top + height) },
        };
        return bounds;
    }

    const matrix = _matrix.reset();

    // Apply transformations in the correct order
    if (isLine) {
        // Lines rotate around left-center origin (transform-origin: left center)
        matrix.translate(left, top + height / 2);
        matrix.rotate(rotation);
        matrix.translate(0, -height / 2);
    } else {
        // Other shapes rotate around center (transform-origin: center center)
        matrix.translate(left + width / 2, top + height / 2);
        matrix.rotate(rotation);
        if (scale !== 1) {
            matrix.scale(scale, scale);
        }
        matrix.translate(-width / 2, -height / 2);
    }

    // Transform all four corners into reusable point objects
    matrix.transformPointInto(0, 0, _p0);
    matrix.transformPointInto(width, 0, _p1);
    matrix.transformPointInto(width, height, _p2);
    matrix.transformPointInto(0, height, _p3);

    // Find axis-aligned bounding box (AABB) using explicit comparisons
    let minX = _p0.x;
    let maxX = _p0.x;
    let minY = _p0.y;
    let maxY = _p0.y;

    if (_p1.x < minX) {
        minX = _p1.x;
    } else if (_p1.x > maxX) {
        maxX = _p1.x;
    }
    if (_p1.y < minY) {
        minY = _p1.y;
    } else if (_p1.y > maxY) {
        maxY = _p1.y;
    }

    if (_p2.x < minX) {
        minX = _p2.x;
    } else if (_p2.x > maxX) {
        maxX = _p2.x;
    }
    if (_p2.y < minY) {
        minY = _p2.y;
    } else if (_p2.y > maxY) {
        maxY = _p2.y;
    }

    if (_p3.x < minX) {
        minX = _p3.x;
    } else if (_p3.x > maxX) {
        maxX = _p3.x;
    }
    if (_p3.y < minY) {
        minY = _p3.y;
    } else if (_p3.y > maxY) {
        maxY = _p3.y;
    }

    setBounds(bounds, minX, minY, maxX, maxY);

    // Round transformed corner points to whole pixels to avoid sub-pixel gaps when snapping
    bounds.corners = {
        topLeft: { x: Math.round(_p0.x), y: Math.round(_p0.y) },
        topRight: { x: Math.round(_p1.x), y: Math.round(_p1.y) },
        bottomRight: { x: Math.round(_p2.x), y: Math.round(_p2.y) },
        bottomLeft: { x: Math.round(_p3.x), y: Math.round(_p3.y) },
    };

    return bounds;
}
