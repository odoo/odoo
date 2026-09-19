/**
 * What the manager needs of a desired surface: an identity to keep it alive by, and where the
 * layout wants it. Whatever else the caller renders from rides along, untouched.
 *
 * @typedef SurfaceDescriptor
 * @property {string} key stable identity, never index based
 * @property {string} placement where the layout wants this surface
 */

/**
 * The stable rendering identity of one entry of a stage. The key lives as long as the entry is
 * desired, so a layout change moves the surface instead of recreating it.
 *
 * @template {SurfaceDescriptor} T the descriptor the caller reconciles with
 */
export class Surface {
    /** @type {string} session/member based, never index based */
    key;
    /** @type {T|undefined} replaced — never mutated — on every reconcile */
    data;

    /**
     * @param {string} key
     */
    constructor(key) {
        this.key = key;
    }
}

/**
 * Keeps the {@link Surface} of a stage alive across layout changes.
 *
 * @template {SurfaceDescriptor} T the descriptor this manager reconciles with
 */
export class SurfaceManager {
    /** @type {Map<string, Surface<T>>} */
    _surfaces = new Map();

    /**
     * Duplicate keys are ignored. Pass a fresh descriptor per reconcile and render `surface.data`:
     * that new object is what tells the card its media changed.
     *
     * @param {T[]} descriptors desired surfaces in render order
     * @returns {Surface<T>[]}
     */
    reconcile(descriptors) {
        const next = new Map();
        const result = [];
        for (const descriptor of descriptors) {
            if (next.has(descriptor.key)) {
                continue;
            }
            const surface = this._surfaces.get(descriptor.key) ?? new Surface(descriptor.key);
            surface.data = descriptor;
            next.set(descriptor.key, surface);
            result.push(surface);
        }
        this._surfaces = next;
        return result;
    }

    /**
     * @param {string} key
     * @returns {Surface<T>|undefined}
     */
    get(key) {
        return this._surfaces.get(key);
    }

    get size() {
        return this._surfaces.size;
    }
}
