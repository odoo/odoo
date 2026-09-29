import { onMounted, onPatched, onWillPatch, onWillUnmount, signal, useOnChange } from "@odoo/owl";

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
 * Delay in ms without scroll after which a scroll is considered ended when no
 * "scrollend" event is dispatched.
 */
export const SCROLL_IDLE_DELAY = 250;

/**
 * @param {HTMLElement} el the element with the scrollbar.
 * @param {Object} [options]
 * @param {() => boolean} [options.isDone] whether the awaited scroll is done,
 *  to ignore the end of another scroll (e.g. of an earlier instant scroll whose
 *  events are only dispatched after this one started) and to keep waiting for
 *  it when idle.
 * @returns {Promise<void>} resolved once the ongoing scroll of `el` ends.
 */
export function waitForScrollEnd(el, { isDone = () => true } = {}) {
    const { promise, resolve } = Promise.withResolvers();
    if ("onscrollend" in window) {
        // also wait for the ancestors of `el`, which can scroll instead of it
        /** @type {Set<EventTarget>} */
        const scrolling = new Set();
        const isRelevant = (target) => target.contains?.(el);
        /**
         * Whether the last scroll ended before the awaited scroll was done,
         * e.g. when interrupted by the user. Cleared when scrolling again, as
         * it can also be the end of a scroll that started before waiting.
         */
        let interrupted = false;
        // A scroll that doesn't change the position emits no "scrollend", nor
        // does an element removed while scrolling, nor a smooth scroll cut
        // short by an instant one: also resolve once idle. While the awaited
        // scroll is still expected, keep waiting a bit longer, as its frames
        // can be delayed (e.g. on a busy machine).
        let timeout;
        let idleCount = 0;
        const onIdle = () => {
            if (
                !el.isConnected ||
                interrupted ||
                (!scrolling.size && isDone()) ||
                ++idleCount >= 4
            ) {
                resolve();
            } else {
                timeout = window.setTimeout(onIdle, SCROLL_IDLE_DELAY);
            }
        };
        const onScroll = (ev) => {
            if (ev) {
                if (!isRelevant(ev.target)) {
                    return;
                }
                scrolling.add(ev.target);
                interrupted = false;
                idleCount = 0;
            }
            window.clearTimeout(timeout);
            timeout = window.setTimeout(onIdle, SCROLL_IDLE_DELAY);
        };
        const onScrollEnd = (ev) => {
            // ignore scrolls that started before waiting
            if (!scrolling.delete(ev.target) || scrolling.size) {
                return;
            }
            if (isDone()) {
                resolve();
            } else {
                interrupted = true;
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
        window.setTimeout(resolve, SCROLL_IDLE_DELAY);
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
                if (key === undefined) {
                    this.cancelReveal();
                }
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
        // listened from the patch rendering the ready items, after `apply`: not
        // from a change of `ready`, as a reset patch can set it to false and
        // back to true, and the scroll of that patch must not be saved
        let listenedEl;
        const stopListening = () => {
            if (listenedEl) {
                observer.unobserve(listenedEl);
                listenedEl.removeEventListener("scroll", this.onScroll);
                listenedEl = undefined;
            }
        };
        const listen = () => {
            const el = this.params.ready() ? this.ref() : undefined;
            if (el === listenedEl) {
                return;
            }
            stopListening();
            if (el) {
                el.addEventListener("scroll", this.onScroll);
                observer.observe(el);
                listenedEl = el;
            }
        };
        onMounted(listen);
        onPatched(listen);
        onWillUnmount(stopListening);
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
        if (!this.revealPromise && !this.isSmoothScrolling) {
            // saved after the reveal or smooth scroll, so that restoring it
            // doesn't interrupt it
            this.save();
        }
    }

    /**
     * Stops tracking the ongoing reveal, if any: the stored position no longer
     * waits for it, and is not overridden once its scroll ends.
     */
    cancelReveal() {
        this.revealPromise = undefined;
    }

    reset() {
        this.cancelReveal();
        this.smoothScrollingPromise = undefined;
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
        promise.then((revealed) => {
            if (this.revealPromise === promise) {
                this.revealPromise = undefined;
                if (revealed && this.ref()) {
                    this.save();
                }
            }
        });
        if (fromEnd) {
            this.set(this.endScrollTop);
            // Let the jump to the end complete, so that its "scrollend" event
            // is not mistaken for the end of the reveal.
            await new Promise((resolve) => window.requestAnimationFrame(resolve));
            // may have been re-rendered or withdrawn (e.g. jump to the end)
            itemEl =
                this.ref() &&
                this.params.getRevealedItem?.()?.key === key &&
                this.params.getItemEl(key);
            if (!itemEl) {
                // list closed, item removed or reveal withdrawn: keep the
                // stored position, which may have been set in the meantime
                resolve(false);
                return;
            }
        }
        // the stored position is outdated by the reveal
        this.params.setPosition(undefined);
        waitForScrollEnd(this.ref()).then(() => resolve(true));
        this.getItemScrollTarget(itemEl).scrollIntoView({ behavior: "smooth", block: "center" });
    }

    /**
     * Current position in pixels from the start of the list.
     */
    get pixelPosition() {
        const el = this.ref();
        return this.reversed ? el.scrollHeight - el.scrollTop - el.clientHeight : el.scrollTop;
    }

    save() {
        this.params.setPosition(this.isAtEnd ? "bottom" : this.pixelPosition);
    }

    /**
     * Stores the current position in pixels, even at the end of the list, and
     * lets the next `apply` set it again: the items on screen stay in place
     * through the next change instead of sticking to the end.
     */
    keepPosition() {
        this.params.setPosition(this.pixelPosition);
        this.lastSetValue = undefined;
    }

    set(value, { smooth = false } = {}) {
        if (smooth) {
            this.smoothScroll(value);
            return;
        }
        this.ref().scrollTo({ top: value });
        this.lastSetValue = value;
        this.save();
    }

    /**
     * Smoothly scrolls to the given value. The stored position is kept during
     * the scroll and applied again once it ends, so that the scroll lands on
     * it even when cut short (e.g. the list grew meanwhile, or its frames were
     * delayed), unless the user scrolled in the meantime.
     *
     * @param {number} value
     */
    smoothScroll(value) {
        const el = this.ref();
        let scrolledByUser = false;
        const onUserScroll = () => (scrolledByUser = true);
        const userEvents = ["wheel", "touchstart", "pointerdown", "keydown"];
        for (const type of userEvents) {
            el.addEventListener(type, onUserScroll, { passive: true });
        }
        const promise = waitForScrollEnd(el, {
            isDone: () =>
                Math.abs(el.scrollTop - Math.min(value, el.scrollHeight - el.clientHeight)) <= 1,
        });
        this.smoothScrollingPromise = promise;
        promise.then(() => {
            for (const type of userEvents) {
                el.removeEventListener(type, onUserScroll);
            }
            if (this.smoothScrollingPromise !== promise) {
                return;
            }
            this.smoothScrollingPromise = undefined;
            if (!this.ref() || !this.params.ready()) {
                return;
            }
            if (scrolledByUser) {
                this.save();
                return;
            }
            if (this.params.getPosition() === "bottom-smooth") {
                this.params.setPosition("bottom");
            }
            this.lastSetValue = undefined;
            this.apply();
        });
        el.scrollTo({ behavior: "smooth", top: value });
        this.lastSetValue = value;
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
