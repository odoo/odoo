/** @typedef {import("@mail/discuss/call/common/stage/surface_manager").StagePipeline} StagePipeline */
/** @typedef {import("@mail/discuss/call/common/stage/surface_manager").SurfaceKey} SurfaceKey */

/**
 * The last step of the {@link StagePipeline}.
 *
 * Moves elements to target rectangles through the Web Animations API, outside the OWL render loop.
 * Between animations an element's box is already the target size and its inline transform already
 * the target, so container queries lay out for the destination and nothing is committed at the end.
 */

/** Time (ms) a surface takes to reach a new rectangle. */
export const GEOMETRY_ANIMATION_DURATION = 200;
/** Easing of that move: quick to leave, slow to settle. */
export const GEOMETRY_ANIMATION_EASING = "cubic-bezier(0.2, 0, 0, 1)";

/**
 * @typedef Rect
 * @property {number} x
 * @property {number} y
 * @property {number} width
 * @property {number} height
 */

/**
 * @param {Rect} a
 * @param {Rect} b
 */
function rectsEqual(a, b) {
    return a.x === b.x && a.y === b.y && a.width === b.width && a.height === b.height;
}

/**
 * Linear interpolation between two rectangles: the one `t` of the way from `from` to `to`.
 *
 * @param {Rect} from
 * @param {Rect} to
 * @param {number} t progress, 0 at `from` and 1 at `to`
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
 * Shows `visual` on an element sized `box`. Scaling rather than resizing keeps the animation to
 * transform properties alone, so the browser never re-lays-out a frame of it.
 *
 * @param {Rect} visual the rectangle to show
 * @param {Rect} box the element's box size
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
        /** @type {Map<SurfaceKey, {el: HTMLElement, from: Rect, target: Rect, animation: Animation|undefined}>} */
        this._entries = new Map();
    }

    get size() {
        return this._entries.size;
    }

    /**
     * Animate a surface to `rect` from wherever it visually is. Latest target wins; re-setting the
     * same one is a no-op, as every patch re-applies the layout geometry.
     *
     * @param {SurfaceKey} key
     * @param {Rect} rect target rectangle
     * @param {HTMLElement} el element to move
     * @param {Object} [param3]
     * @param {boolean} [param3.animate=true] false for a drag: the surface has to be under the
     *  pointer on this frame.
     */
    setTarget(key, rect, el, { animate = true } = {}) {
        const entry = this._entries.get(key);
        if (!entry) {
            // No animation on first appearance.
            applyFinal(el, rect);
            this._entries.set(key, { el, from: rect, target: rect, animation: undefined });
            return;
        }
        const current = this.currentRect(key);
        // The running animation belongs to the old element, so restart it on the new one.
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
            return;
        }
        entry.animation = el.animate(
            [{ transform: transformOf(current, rect) }, { transform: transformOf(rect, rect) }],
            { duration: this._duration, easing: this._easing }
        );
    }

    /**
     * The rectangle a surface visually occupies right now, mid-animation included. Progress comes
     * from the running effect, so an interrupted move restarts from where the browser took it.
     *
     * @param {SurfaceKey} key
     */
    currentRect(key) {
        const entry = this._entries.get(key);
        if (!entry) {
            return undefined;
        }
        const progress = entry.animation?.effect?.getComputedTiming().progress;
        if (progress === undefined || progress === null) {
            // Not started yet (still at its origin), or over (resting on its target).
            return entry.animation?.playState === "running" ? entry.from : entry.target;
        }
        return lerpRect(entry.from, entry.target, progress);
    }

    /**
     * @param {SurfaceKey} key
     * @param {HTMLElement} [el] still-rendered element to hand back to the stylesheet
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
     * Drop the entries of the surfaces that are gone, so a long call keeps no detached element.
     *
     * @param {Set<SurfaceKey>} activeKeys keys of the currently desired surfaces
     */
    prune(activeKeys) {
        for (const [key, entry] of this._entries) {
            if (!activeKeys.has(key)) {
                entry.animation?.cancel();
                this._entries.delete(key);
            }
        }
    }

    /** Release every surface. The renderer must not be used afterwards. */
    dispose() {
        for (const entry of this._entries.values()) {
            entry.animation?.cancel();
        }
        this._entries.clear();
    }
}
