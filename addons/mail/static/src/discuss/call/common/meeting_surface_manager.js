/**
 * A `MeetingSurface` is the stable rendering identity of a participant media entry (a camera
 * stream, a screen stream or a call invitation) in the meeting. Its {@link MeetingSurface.key}
 * never changes while the participant is in the call, so layout changes (grid ⇄ sidebar ⇄
 * spotlight, pin/unpin, reorder, resize) move the surface around instead of recreating it.
 *
 * The surface is intentionally decoupled from the OWL component that renders it: the component
 * may be created/destroyed, but the surface (and its identity) persists as long as the media
 * entry is desired by the current layout.
 *
 * What the surface owns is *identity and rendering bookkeeping*, never the card data itself:
 * {@link MeetingSurface.data} is an immutable snapshot that is **replaced** on every reconcile,
 * never mutated in place. The card component receives that snapshot as its `cardData` prop, so a
 * media change (a camera turning on, a stream being swapped) reaches it as a new prop value. A
 * surface mutated in place would keep the same prop reference and the card would keep rendering
 * its previous state; DOM reuse comes from the `t-key` on {@link MeetingSurface.key}, not from
 * the identity of the data object.
 *
 * @property {string} key stable identity (session/member based, never index based)
 * @property {Object|undefined} data immutable card data snapshot, replaced on every reconcile.
 *  Carries the placement the current layout wants for the surface.
 */
export class MeetingSurface {
    /**
     * @param {string} key
     */
    constructor(key) {
        this.key = key;
        /** @type {Object|undefined} */
        this.data = undefined;
    }
}

/**
 * Owns the set of {@link MeetingSurface} of a meeting and keeps them alive across layout
 * changes. The only way to create or destroy a surface is to remove its descriptor from the
 * desired list passed to {@link MeetingSurfaceManager.reconcile}: a surface with the same key
 * in two consecutive reconciles is guaranteed to be the exact same instance.
 *
 * The manager is pure JS (no DOM, no OWL, no reactive state): it only maintains the identity
 * mapping. Rendering, geometry and RTC policy are handled elsewhere.
 */
export class MeetingSurfaceManager {
    constructor() {
        this._surfaces = new Map();
    }

    /**
     * Reconcile the desired surface descriptors with the current set: existing surfaces are
     * reused, new ones are created, stale ones are dropped. Duplicate keys in the desired list
     * are ignored (a surface is only rendered once).
     *
     * A reused surface takes the new descriptor as its {@link MeetingSurface.data} snapshot; the
     * descriptor is never merged into the surface. Callers must therefore pass a fresh descriptor
     * object per reconcile, and must render `surface.data` rather than the surface itself: that
     * is what makes a media change reach the card component as a new prop value.
     *
     * @param {Object[]} descriptors desired surfaces in render order
     * @param {string} descriptors[].key
     * @returns {MeetingSurface[]} reconciled surfaces in the desired order
     */
    reconcile(descriptors) {
        const next = new Map();
        const result = [];
        for (const descriptor of descriptors) {
            if (next.has(descriptor.key)) {
                continue;
            }
            const surface =
                this._surfaces.get(descriptor.key) ?? new MeetingSurface(descriptor.key);
            surface.data = descriptor;
            next.set(descriptor.key, surface);
            result.push(surface);
        }
        this._surfaces = next;
        return result;
    }

    /**
     * @param {string} key
     * @returns {MeetingSurface|undefined}
     */
    get(key) {
        return this._surfaces.get(key);
    }

    /** @type {number} */
    get size() {
        return this._surfaces.size;
    }
}
