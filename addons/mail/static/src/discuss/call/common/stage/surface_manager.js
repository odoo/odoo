/** @typedef {import("@mail/discuss/call/common/stage/layout_engine").SurfacePlacement} SurfacePlacement */

/**
 * How a stage puts its surfaces on screen, in the order it runs:
 *
 *   1. `surface_manager.js` reconciles the desired surfaces, one lasting identity per key.
 *   2. `layout_engine.js` turns the measured stage and those surfaces into a rect each.
 *   3. `geometry_renderer.js` animates the real elements to those rects.
 *
 * Nothing holds this type: it is here to be linked to from each module taking part, so they read
 * as steps of one flow. Where the parameters come from is the caller's business.
 *
 * @typedef StagePipeline
 */

/** @typedef {string} SurfaceKey the caller's stable identity for one entry of a stage */

/**
 * The first step of the {@link StagePipeline}.
 *
 * What the manager needs of a desired surface: an identity to keep it alive by, and where the
 * layout wants it. Whatever else the caller renders from rides along, untouched.
 *
 * @typedef SurfaceData
 * @property {SurfaceKey} key stable identity, never index based
 * @property {SurfacePlacement} placement where the layout wants this surface
 */

/**
 * The stable rendering identity of one entry of a stage. The key lives as long as the entry is
 * desired, so a layout change moves the surface instead of recreating it.
 *
 * @template {SurfaceData} T the surface data the caller reconciles with
 */
export class Surface {
    /** @type {SurfaceKey} the caller's stable identity, never index based */
    key;
    /** @type {T|undefined} replaced — never mutated — on every reconcile */
    data;

    /**
     * @param {SurfaceKey} key
     */
    constructor(key) {
        this.key = key;
    }
}

/**
 * Keeps the {@link Surface} of a stage alive across layout changes.
 *
 * @template {SurfaceData} T the surface data this manager reconciles with
 */
export class SurfaceManager {
    /** @type {Map<SurfaceKey, Surface<T>>} */
    _surfaces = new Map();

    /**
     * Duplicate keys are ignored. Pass fresh surface data per reconcile and render `surface.data`:
     * the surface keeps its identity, so that new object is the only sign its content changed.
     *
     * @param {T[]} surfaceDataList desired surfaces in render order
     * @returns {Surface<T>[]}
     */
    reconcile(surfaceDataList) {
        const next = new Map();
        const result = [];
        for (const surfaceData of surfaceDataList) {
            if (next.has(surfaceData.key)) {
                continue;
            }
            const surface = this._surfaces.get(surfaceData.key) ?? new Surface(surfaceData.key);
            surface.data = surfaceData;
            next.set(surfaceData.key, surface);
            result.push(surface);
        }
        this._surfaces = next;
        return result;
    }

    /**
     * @param {SurfaceKey} key
     * @returns {Surface<T>|undefined}
     */
    get(key) {
        return this._surfaces.get(key);
    }

    get size() {
        return this._surfaces.size;
    }
}
