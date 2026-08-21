/**
 * Imperative geometry renderer of the meeting stage. Every positioned surface gets a target
 * rectangle; the renderer hands the move to the Web Animations API as a `transform` animation
 * (compositor-only, so it keeps running smoothly while the main thread renders the call) and
 * never touches the OWL render loop.
 *
 * Rendering contract:
 * - the element's box (width/height) is always the *target* size, so container queries and
 *   overlays are already laid out for the destination while the visual scales in;
 * - the element's inline `transform` is always its *resting* state, i.e. the target; the animation
 *   only overrides it while it runs, so it needs no fill mode and leaves nothing to commit when it
 *   ends;
 * - the animated visual position/size is `translate3d(...) scale(...)` from the box's top-left
 *   origin;
 * - a new target interrupts the running animation from the current visual rectangle
 *   (latest-layout-wins, never a queued animation);
 * - new surfaces snap to their target (no animation on first appearance);
 * - so does a move the user is driving with a pointer (`animate: false`): it has to land where the
 *   pointer is on this very frame, not 200ms behind it;
 * - surfaces the layout gave no geometry are released with {@link GeometryRenderer.remove};
 * - {@link GeometryRenderer.prune} drops the entries of surfaces that disappeared, so a long
 *   call never accumulates detached elements.
 */

/** Duration (ms) of a geometry transition. */
export const GEOMETRY_ANIMATION_DURATION = 200;
/** Timing function of a geometry transition. */
export const GEOMETRY_ANIMATION_EASING = "cubic-bezier(0.2, 0, 0, 1)";

/**
 * @typedef Rect
 * @property {number} x
 * @property {number} y
 * @property {number} width
 * @property {number} height
 */

function rectsEqual(a, b) {
    return a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

/**
 * @param {Rect} from
 * @param {Rect} to
 * @param {number} t
 * @returns {Rect}
 */
function lerpRect(from, to, t) {
    return {
        x: from.x + (to.x - from.x) * t,
        y: from.y + (to.y - from.y) * t,
        width: from.width + (to.width - from.width) * t,
        height: from.height + (to.height - from.height) * t,
    };
}

/**
 * @param {Rect} visual the rectangle to show
 * @param {Rect} box the element's box size
 * @returns {string} the transform showing `visual` on an element whose box is `box`. Scaling the
 *  box back to the visual size keeps the animation to transform properties alone, so the browser
 *  never re-lays-out a frame of it.
 */
function transformOf(visual, box) {
    return `translate3d(${visual.x}px, ${visual.y}px, 0) scale(${
        box.width ? visual.width / box.width : 0
    }, ${box.height ? visual.height / box.height : 0})`;
}

/**
 * Put an element at rest on `rect`.
 *
 * @param {HTMLElement} el
 * @param {Rect} rect
 */
function applyFinal(el, rect) {
    el.style.transformOrigin = "0 0";
    el.style.width = `${rect.width}px`;
    el.style.height = `${rect.height}px`;
    el.style.transform = `translate3d(${rect.x}px, ${rect.y}px, 0)`;
}

export class GeometryRenderer {
    /**
     * @param {Object} [param0]
     * @param {number} [param0.duration=GEOMETRY_ANIMATION_DURATION] transition duration (ms)
     * @param {string} [param0.easing=GEOMETRY_ANIMATION_EASING] transition timing function
     */
    constructor({
        duration = GEOMETRY_ANIMATION_DURATION,
        easing = GEOMETRY_ANIMATION_EASING,
    } = {}) {
        this._duration = duration;
        this._easing = easing;
        /** @type {Map<string, {el: HTMLElement, from: Rect, target: Rect, animation: Animation|undefined}>} */
        this._entries = new Map();
    }

    /** @type {number} */
    get size() {
        return this._entries.size;
    }

    /**
     * Set the target rectangle of a surface and animate to it from its current visual rectangle.
     * Calling it with the same target is a no-op (patches re-apply the layout geometry on every
     * render): only the current visual and the latest target are ever kept, never a queue.
     *
     * @param {string} key surface key
     * @param {Rect} rect target rectangle
     * @param {HTMLElement} el element to move
     * @param {Object} [param3]
     * @param {boolean} [param3.animate=true] whether to transition from the current visual
     *  rectangle. False for a move the user is dragging: the surface must be under the pointer on
     *  this frame, and the next drag step would interrupt the animation anyway.
     */
    setTarget(key, rect, el, { animate = true } = {}) {
        const entry = this._entries.get(key);
        if (!entry) {
            // New surface: snap to its target, no animation on first appearance.
            applyFinal(el, rect);
            this._entries.set(key, { el, from: rect, target: rect, animation: undefined });
            return;
        }
        const current = this.currentRect(key);
        // A fresh element renders this key (e.g. the previous one was unmounted): the animation
        // belongs to the old element, so it is restarted below on the new one from the same visual.
        const elChanged = entry.el !== el;
        if (!elChanged && rectsEqual(entry.target, rect)) {
            return;
        }
        entry.animation?.cancel();
        entry.animation = undefined;
        entry.el = el;
        entry.from = current;
        entry.target = rect;
        applyFinal(el, rect);
        if (!animate || rectsEqual(current, rect)) {
            // Nothing to transition: either the caller wants the surface there right now, or the
            // visual is already there (e.g. the target went back to its previous value).
            return;
        }
        entry.animation = el.animate(
            [{ transform: transformOf(current, rect) }, { transform: transformOf(rect, rect) }],
            { duration: this._duration, easing: this._easing }
        );
    }

    /**
     * The rectangle a surface is visually occupying right now, mid-animation included. Read from
     * the running effect rather than interpolated here, so an interrupted move restarts from
     * wherever the browser has actually taken it.
     *
     * @param {string} key surface key
     * @returns {Rect|undefined} `undefined` for an unknown surface.
     */
    currentRect(key) {
        const entry = this._entries.get(key);
        if (!entry) {
            return undefined;
        }
        const progress = entry.animation?.effect?.getComputedTiming().progress;
        if (progress === undefined || progress === null) {
            // No animation, or one that has no progress of its own: either it is over (the surface
            // rests on its target) or it has not started yet (it still shows where it came from).
            return entry.animation?.playState === "running" ? entry.from : entry.target;
        }
        return lerpRect(entry.from, entry.target, progress);
    }

    /**
     * Release a surface: drop its entry and, when `el` is given (it is still rendered, the layout
     * simply gave it no geometry), reset its inline geometry so the CSS takes over again.
     *
     * @param {string} key surface key
     * @param {HTMLElement} [el] element whose inline geometry should be reset
     */
    remove(key, el) {
        this._entries.get(key)?.animation?.cancel();
        if (el) {
            el.style.transform = "";
            el.style.width = "";
            el.style.height = "";
        }
        this._entries.delete(key);
    }

    /**
     * Drop the entries of every surface that is not in `activeKeys` anymore. Surfaces leave the
     * desired set when participants leave, layouts hide them or filters drop them; their
     * elements are unmounted by OWL, so only the entry has to go.
     *
     * @param {Set<string>} activeKeys keys of the currently desired surfaces
     */
    prune(activeKeys) {
        for (const [key, entry] of this._entries) {
            if (!activeKeys.has(key)) {
                entry.animation?.cancel();
                this._entries.delete(key);
            }
        }
    }

    /**
     * Release every surface and stop its animation. The renderer must not be used after disposal.
     */
    dispose() {
        for (const entry of this._entries.values()) {
            entry.animation?.cancel();
        }
        this._entries.clear();
    }
}
