import {
    computed,
    onMounted,
    onPatched,
    onWillUnmount,
    proxy,
    signal,
    t,
    untrack,
    useEffect,
    useListener,
    usePlugin,
    useProps,
    useScope,
} from "@odoo/owl";

import { Reactive } from "@web/core/utils/reactive";
import { useLayoutEffect } from "@web/owl2/utils";

import { CallPermissionDeniedDialog } from "@mail/discuss/call/common/call_permission_denied_dialog";
import { monitorAudio } from "@mail/utils/common/media_monitoring";
import { browser } from "@web/core/browser/browser";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { useService } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

/**
 * Version of usePlugin() where the plugin is allowed to not be provided by any parented component.
 *
 * @template T
 * @param {T extends import("@odoo/owl").PluginConstructor} pluginType
 * @returns {import("@odoo/owl").PluginInstance<T>|undefined}
 */
export function useMaybePlugin(pluginType) {
    if (useScope().pluginManager?.getPluginById(pluginType.id)) {
        return usePlugin(pluginType);
    }
    return undefined;
}

/**
 * @param {() => HTMLElement} target
 * @param {string} eventName
 * @param {Function} handler
 * @param {boolean|AddEventListenerOptions} [eventParams]
 */
export function useLazyExternalListener(target, eventName, handler, eventParams) {
    let t;
    onMounted(() => {
        t = target();
        if (!t) {
            return;
        }
        t.addEventListener(eventName, handler, eventParams);
    });
    onPatched(() => {
        const t2 = target();
        if (t !== t2) {
            if (t) {
                t.removeEventListener(eventName, handler, eventParams);
            }
            if (t2) {
                t2.addEventListener(eventName, handler, eventParams);
            }
            t = t2;
        }
    });
    onWillUnmount(() => {
        if (!t) {
            return;
        }
        t.removeEventListener(eventName, handler, eventParams);
    });
}

export function onExternalClick(ref, cb) {
    let downTarget, upTarget;
    let targetDocument = document;
    function onClick(ev) {
        const el = ref();
        if (el && !el.contains(ev.composedPath()[0])) {
            cb(ev, { downTarget, upTarget });
            upTarget = downTarget = null;
        }
    }
    function onMousedown(ev) {
        downTarget = ev.target;
    }
    function onMouseup(ev) {
        upTarget = ev.target;
    }
    onMounted(() => {
        targetDocument = ref()?.ownerDocument || document;
        targetDocument.body.addEventListener("mousedown", onMousedown, true);
        targetDocument.body.addEventListener("mouseup", onMouseup, true);
        targetDocument.body.addEventListener("click", onClick, true);
    });
    onWillUnmount(() => {
        targetDocument.body.removeEventListener("mousedown", onMousedown, true);
        targetDocument.body.removeEventListener("mouseup", onMouseup, true);
        targetDocument.body.removeEventListener("click", onClick, true);
    });
}

/**
 * Hook that allows to determine precisely when refs are (mouse-)hovered.
 * Should provide a list of refs, and can add callbacks when elements are
 * hovered-in (onHover), hovered-out (onAway).
 *
 * @param {import("@odoo/owl").Signal<HTMLElement> | import("@odoo/owl").Signal<HTMLElement>[]} refs signal refs that determine whether this is in state "hovering".
 * @param {Object} param1
 * @param {() => void} [param1.onHover] callback when hovering the refs.
 * @param {() => void} [param1.onAway] callback when stop hovering the refs.
 * @param {() => Array} [param1.stateObserver] when provided, function that, when called, returns list of
 *   reactive state related to presence of targets' el. This is used to help the hook detect when the targets
 *   are removed from DOM, to properly mark the hovered target as non-hovered.
 */
export function useHover(refs, { onHover, onAway, stateObserver } = {}) {
    refs = Array.isArray(refs) ? refs : [refs];
    let wasHovering = false;
    let awayTimeout;
    let lastHoveredRef;
    const state = proxy({
        set isHover(newIsHover) {
            if (this._isHover !== newIsHover) {
                this._isHover = newIsHover;
                this._count++;
            }
        },
        get isHover() {
            void this._count;
            return this._isHover;
        },
        _count: 0,
        _isHover: false,
        refs,
    });
    /** @param {boolean} hovering */
    function setHover(hovering) {
        if (hovering && !wasHovering) {
            state.isHover = true;
            clearTimeout(awayTimeout);
            if (typeof onHover === "function") {
                onHover();
            }
        } else if (!hovering) {
            state.isHover = false;
            clearTimeout(awayTimeout);
            if (typeof onAway === "function") {
                awayTimeout = setTimeout(() => {
                    onAway();
                }, 100);
            }
        }
        wasHovering = hovering;
    }
    /** @param {MouseEvent} ev */
    function onmouseenter(ev) {
        if (state.isHover) {
            return;
        }
        for (const ref of state.refs) {
            const el = ref();
            if (!el) {
                continue;
            }
            if (el.contains(ev.target)) {
                setHover(true);
                lastHoveredRef = ref;
                return;
            }
        }
    }
    /** @param {MouseEvent} ev */
    function onmouseleave(ev) {
        if (!state.isHover) {
            return;
        }
        for (const ref of state.refs) {
            const el = ref();
            if (!el) {
                continue;
            }
            if (el.contains(ev.relatedTarget)) {
                return;
            }
        }
        setHover(false);
        lastHoveredRef = null;
    }

    for (const ref of refs) {
        useListener(ref, "mouseenter", (ev) => onmouseenter(ev), true);
        useListener(ref, "mouseleave", (ev) => onmouseleave(ev), true);
    }

    if (stateObserver) {
        useLayoutEffect((open) => {
            // Note: stateObserver is essentially used with useDropdownState()?.isOpen.
            // While isOpen can become false, the ref() can still be there for a short period of time.
            // Relying on isOpen becoming false forces good syncing of isHover state on dropdown close.
            if ((lastHoveredRef && !lastHoveredRef()) || !open) {
                setHover(false);
                lastHoveredRef = null;
            }
        }, stateObserver);
    }
    return state;
}

/**
 * Hook returning reactive scroll state for a given scrollable element.
 *
 * @param {import("@odoo/owl").Signal<Element>} ref - The ref of the scrollable element.
 * @returns {{
 *   hasScrollbar: boolean,
 *   canScrollBefore: boolean,
 *   canScrollAfter: boolean
 * }}
 */
export function useScrollState(ref) {
    const state = proxy({
        hasScrollbar: false,
        canScrollBefore: false,
        canScrollAfter: false,
    });
    function computeState() {
        const el = ref();
        if (!el) {
            return;
        }
        const hasVScroll = el.scrollHeight > el.clientHeight + 1;
        const hasHScroll = el.scrollWidth > el.clientWidth + 1;
        state.hasScrollbar = hasVScroll || hasHScroll;
        if (hasVScroll) {
            const scrollTop = el.scrollTop;
            state.canScrollBefore = scrollTop > 0;
            state.canScrollAfter = scrollTop + el.clientHeight < el.scrollHeight - 1;
        } else if (hasHScroll) {
            const scrollLeft = el.scrollLeft;
            state.canScrollBefore = scrollLeft > 0;
            state.canScrollAfter = scrollLeft + el.clientWidth < el.scrollWidth - 1;
        } else {
            state.canScrollBefore = false;
            state.canScrollAfter = false;
        }
    }
    useListener(ref, "scroll", computeState);
    useEffect(() => {
        const el = ref();
        if (!el) {
            return;
        }
        computeState();
        const resizeObserver = new ResizeObserver(computeState);
        resizeObserver.observe(el);
        return () => resizeObserver.disconnect();
    });
    return state;
}

/**
 * Hook that execute the callback function each time the scrollable element hit
 * the bottom minus the threshold.
 *
 * @param {string|import("@odoo/owl").Signal<HTMLElement|null>} refOrName scrollable t-ref name or signal ref to observe
 * @param {function} callback function to execute when scroll hit the bottom minus the threshold
 * @param {number} threshold number of threshold pixel to trigger the callback
 */
export function useOnBottomScrolled(ref, callback, threshold = 1) {
    function onScroll() {
        const el = ref();
        if (el && Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) < threshold) {
            callback();
        }
    }
    onMounted(() => {
        ref()?.addEventListener("scroll", onScroll);
    });
    onWillUnmount(() => {
        ref()?.removeEventListener("scroll", onScroll);
    });
}

/**
 * @param {string} refName
 * @param {function} [cb]
 */
export function useVisible(ref, cb, { ready = true } = {}) {
    const getEl = () => untrack(ref);
    const state = proxy({
        isVisible: undefined,
        ready,
    });
    function setValue(value) {
        state.isVisible = value;
        cb?.(state.isVisible);
    }
    const observer = new IntersectionObserver((entries) => {
        setValue(entries.at(-1).isIntersecting);
    });
    useLayoutEffect(
        (el, ready) => {
            if (el && ready) {
                observer.observe(el);
                return () => {
                    setValue(undefined);
                    observer.unobserve(el);
                };
            }
        },
        () => [getEl(), state.ready]
    );
    return state;
}

/**
 * @typedef {Object} MessageScrolling
 * @property {function} clear
 * @property {function} highlightMessage
 * @property {number|null} highlightedMessageId
 */

/**
 * @param {Object} params
 * @param {function(): import("models").Thread|null} params.thread
 * @param {function(): Object} [params.messageFetchRouteParams]
 * @param {number} [params.duration=1500]
 * @returns {MessageScrolling}
 */
export function useMessageScrolling({
    thread: threadFn,
    messageFetchRouteParams = () => ({}),
    duration = 1500,
}) {
    let timeout;
    const state = proxy({
        clear() {
            if (this.highlightedMessageId) {
                browser.clearTimeout(timeout);
                timeout = null;
                this.highlightedMessageId = null;
            }
        },
        /**
         * @param {import("models").Message} message
         */
        async highlightMessage(message) {
            const thread = threadFn();
            if (!thread) {
                return;
            }
            state.initiated = true;
            let messageScrollDirection;
            if (message.notIn(thread.messages)) {
                messageScrollDirection = message.id < thread.messages[0]?.id ? "top" : "bottom";
                await thread.loadAround({
                    messageId: message.id,
                    routeParams: messageFetchRouteParams(),
                });
            }
            const lastHighlightedMessageId = state.highlightedMessageId;
            this.clear();
            if (lastHighlightedMessageId === message.id) {
                // Give some time for the state to update.
                await new Promise(setTimeout);
            }
            thread.scrollTop = messageScrollDirection === "top" ? "bottom" : undefined;
            if (thread.scrollTop === "bottom") {
                state.startupPromise = new Promise((resolve) => (state.resolveStartup = resolve));
                await state.startupPromise;
                state.startupPromise = null;
                state.resolveStartup = null;
            }
            state.highlightedMessageId = message.id;
            state.initiated = false;
            timeout = browser.setTimeout(() => this.clear(), duration);
        },
        initiated: false,
        /**
         * Promise during highlight startup, i.e. highlight is initiated but isn't scrolling yet
         * Useful to set correct starting condition to initiate scroll to highlight, like scroll to bottom.
         */
        startupPromise: null,
        /** @type {(value?: void) => void | null}  */
        resolveStartup: null,
        /** @type {?Promise<void>} Promise during scrolling to highlight */
        scrollPromise: null,
        /** @type {(value?: void) => void | null}  */
        resolveScroll: null,
        /**
         * Scroll the element into view and expose a promise that will resolved
         * once the scroll is done.
         *
         * @param {Element} el
         */
        scrollTo(el) {
            state.resolveScroll?.();
            const { promise: scrollPromise, resolve: resolveScroll } = Promise.withResolvers();
            state.scrollPromise = scrollPromise;
            state.resolveScroll = resolveScroll;
            if ("onscrollend" in window) {
                document.addEventListener("scrollend", resolveScroll, {
                    capture: true,
                    once: true,
                });
            } else {
                // To remove when safari will support the "scrollend" event.
                setTimeout(resolveScroll, 250);
            }
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            return scrollPromise;
        },
        highlightedMessageId: null,
    });
    return state;
}

export class MessageSelectionState {
    selectedMessageId;
    /** @type {import("@odoo/owl").Signal<Set<number>>} */
    data = signal.Set(new Set(), { type: t.number() });

    clearSelected() {
        this.data().delete(this.selectedMessageId);
    }

    /** @param {import("models").Message} message */
    isSelected(message) {
        return this.data().has(message.id);
    }

    /** @param {import("models").Message} message */
    setSelected(message) {
        this.clearSelected();
        this.data().add(message.id);
        this.selectedMessageId = message.id;
    }

    get size() {
        return this.data().size;
    }
}

export function useMessageSelection() {
    return new MessageSelectionState();
}

export function useMicrophoneVolume() {
    let isClosed = false;
    let audioTrack = null;
    let disconnectAudioMonitor;
    let audioMonitorPromise;
    const store = useService("mail.store");
    const state = proxy({
        isReady: true,
        isActive: false,
        value: 0,
        toggle: async () => {
            if (!state.isReady) {
                return;
            }
            state.isReady = false;
            disconnectAudioMonitor?.();
            disconnectAudioMonitor = undefined;
            if (audioTrack) {
                audioTrack.stop();
                audioTrack = null;
                state.isReady = true;
                state.isActive = false;
                state.value = 0;
                return;
            }
            let track;
            try {
                const audioStream = await browser.navigator.mediaDevices.getUserMedia({
                    audio: store.settings.audioConstraints,
                });
                track = audioStream.getAudioTracks()[0];
            } catch {
                store.env.services.dialog.add(CallPermissionDeniedDialog, {
                    permissionType: "microphone",
                });
                return;
            }
            if (isClosed) {
                track.stop();
                return;
            }
            audioMonitorPromise = monitorAudio(track, {
                onTic: (value) => {
                    state.value = value;
                },
                processInterval: 100,
            });
            disconnectAudioMonitor = await audioMonitorPromise;
            audioTrack = track;
            state.isActive = true;
            state.isReady = true;
        },
    });
    onWillUnmount(async () => {
        isClosed = true;
        await audioMonitorPromise;
        audioTrack?.stop();
        disconnectAudioMonitor?.();
    });
    return state;
}

export function useSelection({ ref, model, preserveOnClickAwayPredicate = () => false }) {
    const ui = useService("ui");
    const elRef = ref;
    const getEl = () => untrack(elRef);
    function onSelectionChange() {
        const el = getEl();
        const activeElement = el?.getRootNode().activeElement;
        if (activeElement && activeElement === el) {
            Object.assign(model, {
                start: el.selectionStart,
                end: el.selectionEnd,
                direction: el.selectionDirection,
            });
        }
    }
    onExternalClick(elRef, async (ev) => {
        if (await preserveOnClickAwayPredicate(ev)) {
            return;
        }
        const el = getEl();
        if (!el) {
            return;
        }
        Object.assign(model, {
            start: el.value.length,
            end: el.value.length,
            direction: el.selectionDirection,
        });
    });
    onMounted(() => {
        document.addEventListener("selectionchange", onSelectionChange);
        document.addEventListener("input", onSelectionChange);
    });
    onWillUnmount(() => {
        document.removeEventListener("selectionchange", onSelectionChange);
        document.removeEventListener("input", onSelectionChange);
    });
    return {
        restore() {
            getEl()?.setSelectionRange(model.start, model.end, model.direction);
        },
        moveCursor(position) {
            model.start = model.end = position;
            const el = getEl();
            if (el && !ui.isSmall) {
                // In mobile, selection seems to adjust correctly.
                // Don't programmatically adjust, otherwise it shows soft keyboard!
                el.selectionStart = el.selectionEnd = position;
            }
        },
    };
}

/**
 * Shared search state machine for components that combine an optional async
 * fetch (typically an RPC) with an optional sync local lookup. Exposes reactive
 * fields (`searchTerm`, `searching`, `loading`, `results`) and methods (`run`,
 * `reset`). Subclass to add domain-specific fields while sharing the base logic.
 *
 * Narrow-dedup: if `fetch` resolves to `false` for some term, the next term
 * that starts with it skips the fetch (a narrower query cannot have results
 * when the broader one had none). Resolve to anything else to disable this for
 * the current bookmark; call `reset()` to drop it (e.g. on context change).
 */
export class SearchState extends Reactive {
    searchTerm = "";
    searching = false;
    loading = false;
    /** @type {any} */
    results;
    /** @type {string | undefined} */
    lastEmptyTerm;
    /** @type {Function | undefined} */
    sequential;
    initialResults;
    /** @type {((term: string) => Promise<boolean | void>) | null} */
    fetch = null;
    /** @type {((term: string) => any) | null} */
    filter = null;
    /** @type {(() => boolean) | null} */
    isActiveGetter = null;
    /** @type {(() => any[]) | null} */
    depsGetter = null;

    /**
     * @param {Object} [options]
     * @param {(term: string) => Promise<boolean | void>} [options.fetch] Async
     *  server call. Resolving to `false` signals "no results" for narrow-dedup.
     * @param {(term: string) => any} [options.filter] Sync local lookup that
     *  produces `results`. Runs immediately on term/deps change and again after
     *  `fetch` resolves (to pick up server-loaded data).
     * @param {any} [options.initialResults] Value assigned to `results` on
     *  reset. Defaults to an empty array.
     * @param {() => any[]} [options.deps] Extra reactive values read inside
     *  `fetch`/`filter`. Re-runs the search when they change.
     * @param {() => boolean} [options.isActive] Predicate deciding whether a
     *  search is active. Defaults to "term is non-empty". Override when a
     *  non-empty term is not the right signal (e.g. a mention popover stays
     *  active for an empty term as long as a delimiter is set).
     */
    constructor({ initialResults = [], fetch, filter, isActive, deps } = {}) {
        super();
        this.initialResults = initialResults;
        this.results = initialResults;
        if (fetch) {
            this.fetch = fetch;
        }
        if (filter) {
            this.filter = filter;
        }
        if (isActive) {
            this.isActiveGetter = isActive;
        }
        if (deps) {
            this.depsGetter = deps;
        }
        this.sequential = useSequential();
        useLayoutEffect(
            () => {
                if (!this.isActive) {
                    this.reset();
                    return;
                }
                if (this.filter) {
                    this.results = this.filter(this.searchTerm);
                }
                this.run();
            },
            () => [this.searchTerm, ...this.deps]
        );
        onWillUnmount(() => this.reset());
    }

    get isActive() {
        return this.isActiveGetter ? this.isActiveGetter() : !!this.searchTerm;
    }

    get deps() {
        return this.depsGetter?.() ?? [];
    }

    reset() {
        this.searchTerm = "";
        this.searching = false;
        this.loading = false;
        this.results = this.initialResults;
        this.lastEmptyTerm = undefined;
    }

    async run({ skipFetch = false } = {}) {
        if (!this.isActive) {
            this.reset();
            return;
        }
        const term = this.searchTerm;
        this.searching = true;
        if (this.lastEmptyTerm !== undefined && term.startsWith(this.lastEmptyTerm)) {
            // Broader term already had no results, so the narrower term
            // can't either — skip both the fetch and the local filter.
            return;
        }
        if (this.fetch && !skipFetch) {
            await this.sequential(async () => {
                this.loading = true;
                let result;
                try {
                    result = await this.fetch(term);
                } finally {
                    if (this.searchTerm === term) {
                        this.loading = false;
                    }
                }
                if (this.searchTerm === term) {
                    if (this.filter) {
                        this.results = this.filter(term);
                    }
                    this.lastEmptyTerm = result === false ? term : undefined;
                }
            });
        } else if (this.filter) {
            this.results = this.filter(term);
        }
    }
}

/**
 * `run({ skipFetch: true })` re-applies the filter without re-fetching,
 * e.g. after the upstream data was mutated locally.
 *
 * @param {ConstructorParameters<typeof SearchState>[0]} [options]
 * @returns {SearchState}
 */
export function useSearch(options = {}) {
    return proxy(new SearchState(options));
}

export function useSequential() {
    let inProgress = false;
    let nextFunction;
    let nextResolve;
    let nextReject;
    async function call() {
        const resolve = nextResolve;
        const reject = nextReject;
        const func = nextFunction;
        nextResolve = undefined;
        nextReject = undefined;
        nextFunction = undefined;
        inProgress = true;
        try {
            const data = await func();
            resolve(data);
        } catch (e) {
            reject(e);
        }
        inProgress = false;
        if (nextFunction && nextResolve) {
            call();
        }
    }
    return (func) => {
        nextResolve?.();
        const prom = new Promise((resolve, reject) => {
            nextResolve = resolve;
            nextReject = reject;
        });
        nextFunction = func;
        if (!inProgress) {
            call();
        }
        return prom;
    };
}

/** @param {import("@web/core/dropdown/dropdown_hooks").DropdownState} [dropdownState] */
export function useDiscussSystray(dropdownState) {
    const ui = useService("ui");
    if (dropdownState) {
        useEffect(() => {
            if (dropdownState.isOpen) {
                document.body.classList.add("o-mail-discuss-systray-menu-open");
            } else {
                document.body.classList.remove("o-mail-discuss-systray-menu-open");
            }
        });
    }
    return {
        class: "o-mail-DiscussSystray-class",
        get contentClass() {
            return `d-flex flex-column flex-grow-1 ${
                ui.isSmall ? "overflow-auto o-scrollbar-thin w-100 mh-100" : ""
            }`;
        },
        get menuClass() {
            return `p-0 o-mail-DiscussSystray ${
                ui.isSmall
                    ? "o-mail-systrayFullscreenDropdownMenu start-0 w-100 mh-100 d-flex flex-column mt-0 border-0 shadow-lg"
                    : ""
            }`;
        },
    };
}

export const useMovable = makeDraggableHook({
    name: "useMovable",
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDragStart: () => true,
    onDragEnd: () => true,
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return { top, left };
    },
});

export const LONG_PRESS_DELAY = 400;

/**
 * Subscribes to long press events on the element matching the given ref name.
 * It internally prevents false positives caused by scroll gestures.
 *
 * @param {import("@odoo/owl").Signal<Element>} ref The ref of the element to listen for long presses on.
 * @param {Object} options
 * @param {() => void} [options.action] Function called when a long press is detected.
 * @param {() => boolean} [options.predicate] Optional function to enable long press detection.
 */
export function useLongPress(ref, { action, predicate = () => true } = {}) {
    const MOVE_TRESHOLD = 10;
    let timer = null;
    let startX = 0;
    let startY = 0;

    function reset() {
        clearTimeout(timer);
        timer = null;
    }
    /** @param {TouchEvent} ev */
    function isTouchTargetInside(ev) {
        return ref()?.contains(ev.target);
    }
    useLazyExternalListener(
        () => window,
        "touchstart",
        (ev) => {
            if (!isTouchTargetInside(ev) || !predicate()) {
                return;
            }
            const touch = ev.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            timer = setTimeout(() => {
                action();
                reset();
            }, LONG_PRESS_DELAY);
        },
        true
    );
    useLazyExternalListener(
        () => window,
        "touchmove",
        (ev) => {
            if (!isTouchTargetInside(ev) || !timer) {
                return;
            }
            const touch = ev.touches[0];
            const dx = touch.screenX - startX;
            const dy = touch.screenY - startY;
            if (Math.hypot(dx, dy) > MOVE_TRESHOLD) {
                reset();
            }
        },
        true
    );
    useLazyExternalListener(
        () => window,
        "touchend",
        (ev) => {
            if (isTouchTargetInside(ev)) {
                reset();
            }
        },
        true
    );
    useLazyExternalListener(
        () => window,
        "touchcancel",
        (ev) => {
            if (isTouchTargetInside(ev)) {
                reset();
            }
        },
        true
    );
}

/**
 * Hook that gathers the signal refs of many children, each child saving its own
 * ref under an id of its choice.
 * @see useForwardRefsToParent
 */
export function useChildRefs() {
    /** @type {Map<any, import("@odoo/owl").Signal<Element>>} */
    const map = new Map();
    return proxy(map);
}

export class UseForwardRefsToParent {
    /**
     * @param {string} propName
     * @param {(any) => any} getRefIdFn
     * @param {import("@odoo/owl").Signal<Element>} ref
     */
    constructor(propName, getRefIdFn, ref) {
        const compProps = useProps();
        this.ref = ref;
        // Note: The `useChildRefs()` Map is shared with all children, using useLayoutEffect/willUnmount to ensure proper on/off life cycle hook calls for given child.
        // If we use setup/willDestroy we can have 2 fiber nodes of same child component with one finalizing with willDestroy from cancelling duplicated fiber node.
        useLayoutEffect(
            (map, key) => {
                if (map) {
                    this.registerRef(map, key);
                    return () => map.delete(key);
                }
            },
            () => [compProps[propName], getRefIdFn(compProps)]
        );
    }

    registerRef(map, key) {
        map.set(key, this.ref);
    }
}

/**
 * Hook that saves the `ref` of a child in the `useChildRefs()` map of its parent,
 * under an id of the child's choice.
 *
 * @param {string} propName name of prop that contains a `useChildRefs()` object
 * @param {(Props) => any} getRefIdFn function whose evaluation returns the key in `useChildRefs()` object to save the `ref`, with props passed as param.
 * @param {import("@odoo/owl").Signal<Element>} ref the `ref` that is saved in `useChildRefs()` at key from `getRefIdFn` function evaluation
 */
export function useForwardRefsToParent(propName, getRefIdFn, ref) {
    new UseForwardRefsToParent(propName, getRefIdFn, ref);
}

/**
 * Single read-only signal derived from one plain-value prop. The result is a signal tracking prop
 * changes, but it is less efficient than `propSignal` as a prop change always triggers an
 * unnecessary render of the parent. To be used only when the parent does not pass a signal and it
 * is not possible to update all parents to pass signals.
 *
 * @template S
 * @param {string} name
 * @param {S} shape shape of the final value (e.g. `t.number()`)
 * @returns {import("@odoo/owl").ReactiveValue<import("@odoo/owl").StripBrands<S>>} the resulting
 *   (read-only) signal, which always exists (never `undefined`), even when the prop is optional.
 */
export function propComputed(name, shape) {
    const rawProps = useProps({ [name]: shape });
    return computed(() => rawProps[name]);
}

/**
 * Single signal for one prop that is itself a signal: a thin wrapper over `useProps.static` that adds
 * the `t.signal(...)` typing. The parent must pass a stable signal reference (but its inner value
 * may change).
 *
 * @template S
 * @param {string} name
 * @param {S} shape shape of the final value (e.g. `t.number()`)
 * @param {object} [options]
 * @param {boolean} [options.optional]
 * @returns {import("@odoo/owl").ReactiveValue<import("@odoo/owl").StripBrands<S>>}
 */
export function propSignal(name, shape, { optional = false } = {}) {
    const type = t.signal(shape);
    return useProps.static(name, optional ? type.optional() : type);
}

/**
 * This hook makes it easier to enable right-click to open a dropdown at position of cursor
 *
 * @param {Object} param0
 * @param {import("@odoo/owl").Signal<Element>} param0.rootRef - The root ref of the element that has right-click.
 *   This rootRef defines the node where the right-click should work and needs to have `.position-relative`, so that
 *   the anchor of right-click dropdown can position itself with absolute positioning inside rootRef's node.
 * @param {() => Object} [param0.extraMenuProps={}] - Optional object of extra props provided to the context menu component.
 * @param {() => void} [param0.onClose] - Optional function invoked when the dropdown closes.
 * @param {() => void} [param0.onContextMenu] when set, provides a custom handler when right-clicking.
 */
export function useRightClickMenu({
    rootRef,
    extraMenuProps = () => ({}),
    onClose: onCloseParam,
    onContextMenu,
} = {}) {
    /**
     * @type {boolean} Whether the right-click dropdown is being closed.
     * Useful to detect when close comes from another right-click on the same element,
     * in order to show the browser right-click instead.
     */
    let isOngoingClose = false;
    const anchor = signal.ref();
    const dropdownState = useDropdownState({
        onClose: async () => {
            if (isOngoingClose) {
                return; // onClose can be called more than once. Limiting to a single onClose to prevent race-condition in tests.
            }
            onCloseParam?.();
            isOngoingClose = true;
            await new Promise((resolve) => setTimeout(() => requestAnimationFrame(resolve)));
            isOngoingClose = false;
            delete rootRef()?.dataset.rightClicking;
        },
    });
    const res = {
        get isOngoingClose() {
            return isOngoingClose;
        },
        get isOpen() {
            return dropdownState.isOpen;
        },
        get menuProps() {
            return {
                anchorRef: anchor,
                dropdownState,
                ...extraMenuProps(),
            };
        },
        /**
         * @param {Event} ev
         * @param {() => void} [onOpenCb]
         */
        open(ev, onOpenCb) {
            if (!rootRef()) {
                return;
            }
            rootRef().dataset.rightClicking = true;
            const el = anchor();
            el.style.left = ev.clientX + "px";
            el.style.top = ev.clientY + "px";
            dropdownState.open();
            onOpenCb?.();
            ev.preventDefault();
        },
    };
    useListener(rootRef, "contextmenu", (ev) => {
        if (onContextMenu) {
            onContextMenu(ev);
        } else {
            res.open(ev);
        }
    });
    return res;
}
