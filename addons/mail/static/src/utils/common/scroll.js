import { onMounted, onPatched, onWillPatch, signal, useOnChange } from "@odoo/owl";

/**
 * Stored scroll position of a list: either `"bottom"` when at the end of the
 * list (optionally `"bottom-smooth"` to reach it with a smooth scroll), or the
 * distance in pixels from the start of the list.
 *
 * @typedef {number|"bottom"|"bottom-smooth"|undefined} ScrollPosition
 */

/**
 * Item to scroll to, taking precedence over any other scroll: either the key
 * of an item to center, or the end of the list.
 *
 * @typedef {{ key: any }|{ end: true }} ScrollTarget
 */

/**
 * @param {ScrollPosition} position
 */
function isEndPosition(position) {
    return typeof position === "string" && position.includes("bottom");
}

/**
 * @param {HTMLElement} el the element with the scrollbar.
 * @returns {Promise<void>} resolved once the ongoing scroll of `el` ends.
 */
export function waitForScrollEnd(el) {
    const { promise, resolve } = Promise.withResolvers();
    if ("onscrollend" in window) {
        // also wait for the ancestors of `el`, which can scroll instead of it
        /** @type {Set<EventTarget>} */
        const scrolling = new Set();
        const isRelevant = (target) => target.contains?.(el);
        // A scroll that doesn't change the position emits no "scrollend", nor
        // does an element removed while scrolling: also resolve once idle.
        let timeout;
        const onScroll = (ev) => {
            if (ev) {
                if (!isRelevant(ev.target)) {
                    return;
                }
                scrolling.add(ev.target);
            }
            window.clearTimeout(timeout);
            timeout = window.setTimeout(resolve, 250);
        };
        const onScrollEnd = (ev) => {
            // ignore scrolls that started before waiting
            if (scrolling.delete(ev.target) && !scrolling.size) {
                resolve();
            }
        };
        onScroll();
        document.addEventListener("scroll", onScroll, { capture: true });
        document.addEventListener("scrollend", onScrollEnd, { capture: true });
        promise.then(() => {
            window.clearTimeout(timeout);
            document.removeEventListener("scroll", onScroll, { capture: true });
            document.removeEventListener("scrollend", onScrollEnd, { capture: true });
        });
    } else {
        // To remove when safari will support the "scrollend" event.
        window.setTimeout(resolve, 250);
    }
    return promise;
}

/**
 * Item to smoothly scroll to: `fromEnd` tells whether to jump to the end of the
 * list before scrolling to the item.
 *
 * @typedef {{ key: any, fromEnd?: boolean }} RevealedItem
 */

/**
 * @typedef {Object} ScrollManagerParams
 * @property {import("@odoo/owl").ReactiveValue<HTMLElement>} ref the element
 *  with the scrollbar.
 * @property {() => boolean} [reversed] whether the end of the list is displayed
 *  at the top.
 * @property {() => boolean} ready whether the items are displayed. The scroll
 *  is only applied when ready.
 * @property {() => { start: number, end: number }} bounds keys of the first
 *  and last items, increasing from start to end (e.g. record ids). Used to
 *  detect items added at either end of the list.
 * @property {() => boolean} [hasMoreAfterEnd] whether more items can be loaded
 *  after the last one, in which case the list is never considered at its end.
 * @property {() => ScrollPosition} getPosition
 * @property {(position: ScrollPosition) => void} setPosition
 * @property {(key: any) => HTMLElement|undefined} getItemEl element of the item
 *  with the given key, if rendered.
 * @property {(itemEl: HTMLElement) => HTMLElement} [getItemScrollTarget] element
 *  to scroll into view to reveal the given item element.
 * @property {(end: number) => any} [getFirstItemAfter] key of the item to
 *  scroll to, rather than scrolling to the end, when items are added after
 *  `end` while at the end of the list.
 * @property {() => ScrollTarget|undefined} [getTarget]
 * @property {(target: ScrollTarget) => void} [onTargetReached]
 * @property {() => RevealedItem|undefined} [getRevealedItem] item to smoothly
 *  scroll to, as soon as it is rendered and the scroll is applied. Restoring
 *  the stored position is paused while there is one.
 * @property {() => void} onNotReady called when the scroll cannot be applied
 *  because the items are not displayed. The owner is expected to reset its
 *  state, including this scroll with `reset()`.
 * @property {() => void} [onFirstApply] called when the scroll is applied for
 *  the first time since the last reset.
 * @property {() => void} [onScroll] called when the scrollable element scrolls.
 */

/**
 * Manages the scroll of a list whose items can be added at both ends.
 *
 * 1. A target (@see ScrollTarget) takes precedence over anything else.
 * 2. When items are added at either end, the items already on screen should
 *    visually stay in place. When the extra items are added at the bottom the
 *    same scroll top position should be kept, and when they are added at the
 *    top, their extra height should be compensated in the scroll position.
 * 3. When the scroll is at the end, it should stay at the end when there is a
 *    change of height: new items, images loaded, ...
 * 4. The scroll position is stored with `setPosition` and restored from
 *    `getPosition`, which allows to restore the last position of a list when
 *    going back and forth between lists.
 * 5. Restoring the position is skipped while an item is revealed (see
 *    `getRevealedItem`).
 */
export class ScrollManager {
    /**
     * Last scroll value that was automatically set. This prevents from
     * setting the same value 2 times in a row. This is not supposed to have
     * an effect, unless the value was changed from outside in the meantime,
     * in which case resetting the value would incorrectly override the
     * other change. This should give enough time to scroll/resize event to
     * register the new scroll value.
     */
    lastSetValue = undefined;
    /**
     * The snapshot mechanism (point 2) should only apply after the items have
     * been displayed at least once. Technically this is after the first patch
     * following when `ready` is true. This is what this variable holds.
     */
    initialized = false;
    /**
     * The snapshot of current scrollTop and scrollHeight for the purpose
     * of keeping items in place when adding items (point 2).
     */
    snapshot = undefined;
    /**
     * The bounds of the items that are already rendered, useful to detect
     * whether items have been added since last render to decide when to apply
     * the snapshot to keep items in place (point 2).
     *
     * @type {{ start: number, end: number }|undefined}
     */
    bounds = undefined;
    /**
     * Whether it was possible to load more items after the end in the last
     * rendered state, useful to decide when to apply the snapshot to keep items
     * in place (point 2).
     */
    hadMoreAfterEnd = false;
    /** @type {Promise|undefined} */
    smoothScrollingPromise;
    /** @type {Promise|undefined} */
    revealPromise;

    /**
     * @param {ScrollManagerParams} params
     */
    constructor(params) {
        this.params = params;
        this.ref = params.ref;
        this.revealRequest = signal(null);
        /** Key of the item that `apply` waits for to be rendered, if any. */
        this.pendingItemKey = signal(null);
        this.apply = this.apply.bind(this);
        this.onScroll = this.onScroll.bind(this);
        useOnChange(
            () => {
                const item = this.params.getRevealedItem?.();
                return [item?.key, item?.fromEnd ?? false];
            },
            (key, fromEnd) => {
                // when cleared, the item may not be rendered yet: don't reveal
                // it later
                this.revealRequest.set(key === undefined ? null : { key, fromEnd });
            }
        );
        useOnChange(
            () => {
                const request = this.revealRequest();
                return [request, request && this.params.getItemEl(request.key)];
            },
            (request, itemEl) => {
                if (request && itemEl) {
                    this.apply();
                }
            }
        );
        useOnChange(
            () => {
                const key = this.pendingItemKey();
                return [key !== null && this.params.getItemEl(key)];
            },
            (itemEl) => {
                if (itemEl) {
                    this.apply();
                }
            }
        );
        onWillPatch(() => {
            if (!this.initialized) {
                return;
            }
            this.snapshot = {
                scrollHeight: this.ref().scrollHeight,
                scrollTop: this.ref().scrollTop,
            };
        });
        onMounted(this.apply);
        onPatched(this.apply);
        /**
         * Size of the list element at the last notification, to ignore the
         * first notification, which `observe()` always triggers: it can come
         * before the items are rendered, and applying the scroll then would
         * save a wrong position.
         */
        let size;
        const observer = new ResizeObserver(([entry]) => {
            const { width, height } = entry.contentRect;
            if (size && (size.width !== width || size.height !== height)) {
                this.apply();
            }
            size = { width, height };
        });
        useOnChange(
            () => [this.ref(), this.params.ready()],
            (el, ready) => {
                if (el && ready) {
                    el.addEventListener("scroll", this.onScroll);
                    observer.observe(el);
                    return () => {
                        observer.unobserve(el);
                        el.removeEventListener("scroll", this.onScroll);
                    };
                }
            }
        );
    }

    get reversed() {
        return this.params.reversed?.() ?? false;
    }

    get isAtEnd() {
        if (this.hadMoreAfterEnd) {
            return false;
        }
        const el = this.ref();
        return this.reversed
            ? el.scrollTop < 30
            : el.scrollHeight - el.scrollTop - el.clientHeight < 30;
    }

    get isSmoothScrolling() {
        return Boolean(this.smoothScrollingPromise);
    }

    /**
     * Scroll top value of the end of the list.
     */
    get endScrollTop() {
        return this.reversed ? 0 : this.ref().scrollHeight - this.ref().clientHeight;
    }

    apply() {
        if (!this.params.ready()) {
            this.params.onNotReady();
            return;
        }
        if (!this.applyContextually()) {
            return;
        }
        this.pendingItemKey.set(null);
        this.snapshot = undefined;
        this.bounds = this.params.bounds();
        this.hadMoreAfterEnd = this.params.hasMoreAfterEnd?.() ?? false;
        if (!this.initialized) {
            this.initialized = true;
            this.params.onFirstApply?.();
        }
        // After the scroll is applied, so that it doesn't override the reveal.
        const request = this.revealRequest();
        const itemEl = request && this.params.getItemEl(request.key);
        if (itemEl) {
            this.revealItem(itemEl, request);
        }
    }

    /**
     * @returns {Boolean} true when the scroll is applied, false when the items
     *  to scroll to are not rendered yet.
     */
    applyContextually() {
        const target = this.params.getTarget?.();
        if (target) {
            return this.applyTarget(target);
        }
        const el = this.ref();
        const bounds = this.params.bounds();
        const position = this.params.getPosition();
        const addedBefore = bounds.start < this.bounds?.start;
        const addedAfter = bounds.end > this.bounds?.end;
        const addedAtTop = this.reversed ? addedAfter : addedBefore;
        const addedAtBottom = this.reversed
            ? addedBefore
            : addedAfter && (this.hadMoreAfterEnd || !isEndPosition(position));
        if (this.snapshot && addedAtTop) {
            this.set(this.snapshot.scrollTop + el.scrollHeight - this.snapshot.scrollHeight);
        } else if (this.snapshot && addedAtBottom) {
            this.set(this.snapshot.scrollTop);
        } else if (!this.params.getRevealedItem?.() && position !== undefined) {
            let value;
            if (isEndPosition(position)) {
                const key = addedAfter
                    ? this.params.getFirstItemAfter?.(this.bounds.end)
                    : undefined;
                if (key !== undefined) {
                    const itemEl = this.params.getItemEl(key);
                    if (!itemEl) {
                        this.pendingItemKey.set(key);
                        return false;
                    }
                    this.getItemScrollTarget(itemEl).scrollIntoView({
                        behavior: "instant",
                        block: this.reversed ? "end" : "start",
                    });
                    this.save();
                    return true;
                }
                value = this.endScrollTop;
            } else {
                value = this.reversed ? el.scrollHeight - position - el.clientHeight : position;
            }
            if (
                (this.lastSetValue === undefined || Math.abs(this.lastSetValue - value) > 1) &&
                !this.isSmoothScrolling
            ) {
                this.set(value, {
                    smooth: typeof position === "string" && position.includes("smooth"),
                });
            }
        }
        return true;
    }

    /**
     * @param {ScrollTarget} target
     * @returns {Boolean} true when the scroll is applied, false when the item
     *  to scroll to is not rendered yet.
     */
    applyTarget(target) {
        if (target.end) {
            this.set(this.endScrollTop);
        } else {
            const itemEl = this.params.getItemEl(target.key);
            if (!itemEl) {
                this.pendingItemKey.set(target.key);
                return false;
            }
            this.set(itemEl.offsetTop - this.ref().offsetHeight / 2 + itemEl.offsetHeight / 2);
        }
        this.params.onTargetReached?.(target);
        return true;
    }

    /**
     * @param {HTMLElement} itemEl
     */
    getItemScrollTarget(itemEl) {
        return this.params.getItemScrollTarget?.(itemEl) ?? itemEl;
    }

    onScroll() {
        this.params.onScroll?.();
        if (!this.revealPromise) {
            // saved after the reveal, so that restoring it doesn't interrupt it
            this.save();
        }
    }

    reset() {
        this.pendingItemKey.set(null);
        this.lastSetValue = undefined;
        this.snapshot = undefined;
        this.bounds = undefined;
        this.initialized = false;
        this.hadMoreAfterEnd = false;
    }

    /**
     * @param {HTMLElement} itemEl
     * @param {{ key: any, fromEnd: boolean }} request
     */
    async revealItem(itemEl, { key, fromEnd }) {
        this.revealRequest.set(null);
        const { promise, resolve } = Promise.withResolvers();
        this.revealPromise = promise;
        promise.then(() => {
            if (this.revealPromise === promise) {
                this.revealPromise = undefined;
                if (this.ref()) {
                    this.save();
                }
            }
        });
        if (fromEnd) {
            this.set(this.endScrollTop);
            // Let the jump to the end complete, so that its "scrollend" event
            // is not mistaken for the end of the reveal.
            await new Promise((resolve) => window.requestAnimationFrame(resolve));
            // may have been re-rendered
            itemEl = this.ref() && this.params.getItemEl(key);
            if (!itemEl) {
                // list closed or item removed
                resolve();
                return;
            }
        }
        // the stored position is outdated by the reveal
        this.params.setPosition(undefined);
        waitForScrollEnd(this.ref()).then(resolve);
        this.getItemScrollTarget(itemEl).scrollIntoView({ behavior: "smooth", block: "center" });
    }

    save() {
        const el = this.ref();
        if (this.isAtEnd) {
            this.params.setPosition("bottom");
        } else {
            this.params.setPosition(
                this.reversed ? el.scrollHeight - el.scrollTop - el.clientHeight : el.scrollTop
            );
        }
    }

    set(value, { smooth = false } = {}) {
        if (smooth) {
            const promise = waitForScrollEnd(this.ref());
            this.smoothScrollingPromise = promise;
            promise.then(() => {
                if (this.smoothScrollingPromise === promise) {
                    this.smoothScrollingPromise = undefined;
                }
            });
        }
        this.ref().scrollTo({ behavior: smooth ? "smooth" : undefined, top: value });
        this.lastSetValue = value;
        this.save();
    }

    /**
     * @returns {Promise} resolved once the ongoing reveal and smooth scroll, if
     *  any, are done.
     */
    waitForIdle() {
        return Promise.all([this.revealPromise, this.smoothScrollingPromise]);
    }
}

/**
 * @param {ScrollManagerParams} params
 * @returns {ScrollManager}
 */
export function useScrollManager(params) {
    return new ScrollManager(params);
}
