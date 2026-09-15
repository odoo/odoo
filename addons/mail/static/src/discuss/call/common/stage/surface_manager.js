/**
 * A card, plus where the layout wants it: what a surface is handed on every reconcile.
 *
 * @typedef {import("@mail/discuss/call/common/call").CardData & {placement: string}} SurfaceDescriptor
 */

/**
 * The stable rendering identity of a participant media entry (camera, screen or invitation). The
 * key lives as long as the entry is desired, so a layout change moves the surface instead of
 * recreating it.
 */
export class Surface {
    /** @type {string} session/member based, never index based */
    key;
    /** @type {SurfaceDescriptor|undefined} replaced — never mutated — on every reconcile */
    data;

    /**
     * @param {string} key
     */
    constructor(key) {
        this.key = key;
    }
}

/** Keeps the {@link Surface} of a stage alive across layout changes. */
export class SurfaceManager {
    /** @type {Map<string, Surface>} */
    _surfaces = new Map();

    /**
     * Duplicate keys are ignored. Pass a fresh descriptor per reconcile and render `surface.data`:
     * that new object is what tells the card its media changed.
     *
     * @param {SurfaceDescriptor[]} descriptors desired surfaces in render order
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
     */
    get(key) {
        return this._surfaces.get(key);
    }

    get size() {
        return this._surfaces.size;
    }
}
