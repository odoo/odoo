import {
    Component,
    onMounted,
    onPatched,
    onWillUnmount,
    toRaw,
    useComponent,
    useEffect,
    useRef,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";

import { monitorAudio } from "@mail/utils/common/media_monitoring";
import { browser } from "@web/core/browser/browser";
import { OVERLAY_SYMBOL } from "@web/core/overlay/overlay_container";
import { Deferred } from "@web/core/utils/concurrency";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export function useLazyExternalListener(target, eventName, handler, eventParams) {
    const boundHandler = handler.bind(useComponent());
    let t;
    onMounted(() => {
        t = target();
        if (!t) {
            return;
        }
        t.addEventListener(eventName, boundHandler, eventParams);
    });
    onPatched(() => {
        const t2 = target();
        if (t !== t2) {
            if (t) {
                t.removeEventListener(eventName, boundHandler, eventParams);
            }
            if (t2) {
                t2.addEventListener(eventName, boundHandler, eventParams);
            }
            t = t2;
        }
    });
    onWillUnmount(() => {
        if (!t) {
            return;
        }
        t.removeEventListener(eventName, boundHandler, eventParams);
    });
}

export function onExternalClick(refName, cb) {
    let downTarget, upTarget;
    const ref = useRef(refName);
    function onClick(ev) {
        if (ref.el && !ref.el.contains(ev.composedPath()[0])) {
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
        document.body.addEventListener("mousedown", onMousedown, true);
        document.body.addEventListener("mouseup", onMouseup, true);
        document.body.addEventListener("click", onClick, true);
    });
    onWillUnmount(() => {
        document.body.removeEventListener("mousedown", onMousedown, true);
        document.body.removeEventListener("mouseup", onMouseup, true);
        document.body.removeEventListener("click", onClick, true);
    });
}

/**
 * Hook that allows to determine precisely when refs are (mouse-)hovered.
 * Should provide a list of ref names, and can add callbacks when elements are
 * hovered-in (onHover), hovered-out (onAway), hovering for some time (onHovering).
 *
 * @param {string | string[] | Function} refNames name of refs that determine whether this is in state "hovering".
 *   ref name that end with "*" means it takes parented HTML node into account too. Useful for floating
 *   menu where dropdown menu container is not accessible. Function type is for useChildRef support.
 * @param {Object} param1
 * @param {() => void} [param1.onHover] callback when hovering the ref names.
 * @param {() => void} [param1.onAway] callback when stop hovering the ref names.
 * @param {number, () => void} [param1.onHovering] array where 1st param is duration until start hovering
 *   and function to be executed at this delay duration after hovering is kept true.
 * @param {() => Array} [param1.stateObserver] when provided, function that, when called, returns list of
 *   reactive state related to presence of targets' el. This is used to help the hook detect when the targets
 *   are removed from DOM, to properly mark the hovered target as non-hovered.
 * @returns {({ isHover: boolean })}
 */
export function useHover(refNames, { onHover, onAway, stateObserver, onHovering } = {}) {
    refNames = Array.isArray(refNames) ? refNames : [refNames];
    const targets = [];
    let wasHovering = false;
    let hoveringTimeout;
    let awayTimeout;
    let lastHoveredTarget;
    for (const refName of refNames) {
        if (typeof refName === "function") {
            // Special case: useChildRef support
            targets.push({ ref: refName });
            continue;
        }
        targets.push({ ref: useRef(refName) });
    }
    const state = useState({
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
        _contains: [],
        _count: 0,
        _isHover: false,
        _targets: targets,
        addTarget(target) {
            state._targets.push(target);
            const handleMouseenter = (ev) => onmouseenter(ev);
            const handleMouseleave = (ev) => onmouseleave(ev);
            target.ref.el.addEventListener("mouseenter", handleMouseenter, true);
            target.ref.el.addEventListener("mouseleave", handleMouseleave, true);
            return () => {
                target.ref.el.removeEventListener("mouseenter", handleMouseenter, true);
                target.ref.el.removeEventListener("mouseleave", handleMouseleave, true);
                const idx = state._targets.findIndex((t) => t === target);
                if (idx) {
                    state._targets.splice(idx, 1);
                }
            };
        },
    });
    function setHover(hovering) {
        if (hovering && !wasHovering) {
            state.isHover = true;
            clearTimeout(awayTimeout);
            clearTimeout(hoveringTimeout);
            if (typeof onHover === "function") {
                onHover();
            }
            if (Array.isArray(onHovering)) {
                const [delay, cb] = onHovering;
                hoveringTimeout = setTimeout(() => {
                    cb();
                }, delay);
            }
        } else if (!hovering) {
            state.isHover = false;
            clearTimeout(awayTimeout);
            if (typeof onAway === "function") {
                awayTimeout = setTimeout(() => {
                    clearTimeout(hoveringTimeout);
                    onAway();
                }, 100);
            }
        }
        wasHovering = hovering;
    }
    function onmouseenter(ev) {
        if (state.isHover) {
            return;
        }
        for (const target of toRaw(state)._targets) {
            if (!target.ref.el) {
                continue;
            }
            if (target.ref.el.contains(ev.target)) {
                setHover(true);
                lastHoveredTarget = target;
                return;
            }
        }
        for (const contains of state._contains) {
            if (contains(ev.target)) {
                setHover(true);
                return;
            }
        }
    }
    function onmouseleave(ev) {
        if (!state.isHover) {
            return;
        }
        for (const target of toRaw(state._targets)) {
            if (!target.ref.el) {
                continue;
            }
            if (target.ref.el.contains(ev.relatedTarget)) {
                return;
            }
        }
        for (const contains of state._contains) {
            if (contains(ev.relatedTarget)) {
                return;
            }
        }
        setHover(false);
        lastHoveredTarget = null;
    }

    for (const target of targets) {
        useLazyExternalListener(
            () => target.ref.el,
            "mouseenter",
            (ev) => onmouseenter(ev),
            true
        );
        useLazyExternalListener(
            () => target.ref.el,
            "mouseleave",
            (ev) => onmouseleave(ev),
            true
        );
    }

    if (stateObserver) {
        useEffect((open) => {
            // Note: stateObserver is essentially used with useDropdownState()?.isOpen.
            // While isOpen can become false, the ref.el can still be there for a short period of time.
            // Relying on isOpen becoming false forces good syncing of isHover state on dropdown close.
            if ((lastHoveredTarget && !lastHoveredTarget.ref.el) || !open) {
                setHover(false);
                lastHoveredTarget = null;
            }
        }, stateObserver);
    }
    return state;
}

export class UseHoverOverlay extends Component {
    static props = ["slots", "hover"];
    static template = xml`<div t-ref="root"><t t-slot="default"/></div>`;

    setup() {
        super.setup();
        this.root = useRef("root");
        const overlayContains = toRaw(this.env[OVERLAY_SYMBOL].contains);
        let removeTarget;
        onMounted(() => {
            this.props.hover._contains.push(overlayContains);
            removeTarget = this.props.hover.addTarget({
                ref: { el: this.root.el.closest(".o-overlay-item") },
            });
        });
        onWillUnmount(() => {
            const idx = this.props.hover._contains.find((c) => c === overlayContains);
            if (idx) {
                this.props.hover._contains.splice(idx, 1);
            }
            removeTarget?.();
        });
    }
}

/**
 * Hook that execute the callback function each time the scrollable element hit
 * the bottom minus the threshold.
 *
 * @param {string} refName scrollable t-ref name to observe
 * @param {function} callback function to execute when scroll hit the bottom minus the threshold
 * @param {number} threshold number of threshold pixel to trigger the callback
 */
export function useOnBottomScrolled(refName, callback, threshold = 1) {
    const ref = useRef(refName);
    function onScroll() {
        if (Math.abs(ref.el.scrollTop + ref.el.clientHeight - ref.el.scrollHeight) < threshold) {
            callback();
        }
    }
    onMounted(() => {
        ref.el?.addEventListener("scroll", onScroll);
    });
    onWillUnmount(() => {
        ref.el?.removeEventListener("scroll", onScroll);
    });
}

/**
 * @param {string} refName
 * @param {function} [cb]
 */
export function useVisible(refName, cb, { ready = true } = {}) {
    const ref = useRef(refName);
    const state = useState({
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
    useEffect(
        (el, ready) => {
            if (el && ready) {
                observer.observe(el);
                return () => {
                    setValue(undefined);
                    observer.unobserve(el);
                };
            }
        },
        () => [ref.el, state.ready]
    );
    return state;
}

/**
 * @typedef {Object} MessageScrolling
 * @property {function} clear
 * @property {function} highlightMessage
 * @property {number|null} highlightedMessageId
 * @returns {MessageScrolling}
 */
export function useMessageScrolling(duration = 2000) {
    let timeout;
    const state = useState({
        clear() {
            if (this.highlightedMessageId) {
                browser.clearTimeout(timeout);
                timeout = null;
                this.highlightedMessageId = null;
            }
        },
        /**
         * @param {import("models").Message} message
         * @param {import("models").Thread} thread
         */
        async highlightMessage(message, thread) {
            state.initiated = true;
            let messageScrollDirection;
            if (message.notIn(thread.messages)) {
                messageScrollDirection = message.id < thread.messages[0]?.id ? "top" : "bottom";
                await thread.loadAround(message.id);
            }
            const lastHighlightedMessageId = state.highlightedMessageId;
            this.clear();
            if (lastHighlightedMessageId === message.id) {
                // Give some time for the state to update.
                await new Promise(setTimeout);
            }
            thread.scrollTop = messageScrollDirection === "top" ? "bottom" : undefined;
            if (thread.scrollTop === "bottom") {
                state.startupDeferred = new Deferred();
                await state.startupDeferred;
                state.startupDeferred = null;
            }
            state.highlightedMessageId = message.id;
            state.initiated = false;
            timeout = browser.setTimeout(() => this.clear(), duration);
        },
        initiated: false,
        /**
         * Deferred during highlight startup, i.e. highlight is initiated but isn't scrolling yet
         * Useful to set correct starting condition to initiate scroll to highlight, like scroll to bottom.
         */
        startupDeferred: null,
        /** Deferred during scrolling to highlight */
        scrollPromise: null,
        /**
         * Scroll the element into view and expose a promise that will resolved
         * once the scroll is done.
         *
         * @param {Element} el
         */
        scrollTo(el) {
            state.scrollPromise?.resolve();
            const scrollPromise = new Deferred();
            state.scrollPromise = scrollPromise;
            if ("onscrollend" in window) {
                document.addEventListener("scrollend", scrollPromise.resolve, {
                    capture: true,
                    once: true,
                });
            } else {
                // To remove when safari will support the "scrollend" event.
                setTimeout(scrollPromise.resolve, 250);
            }
            el.scrollIntoView({ behavior: "smooth", block: "center" });
            return scrollPromise;
        },
        highlightedMessageId: null,
    });
    return state;
}

export function useMicrophoneVolume() {
    let isClosed = false;
    let audioTrack = null;
    let disconnectAudioMonitor;
    let audioMonitorPromise;
    const store = useService("mail.store");
    const state = useState({
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
                store.env.services.notification.add(
                    _t('"%(hostname)s" requires microphone access', {
                        hostname: browser.location.host,
                    }),
                    { type: "warning" }
                );
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

export function useSelection({ refName, model, preserveOnClickAwayPredicate = () => false }) {
    const ui = useService("ui");
    const ref = useRef(refName);
    function onSelectionChange() {
        const activeElement = ref.el?.getRootNode().activeElement;
        if (activeElement && activeElement === ref.el) {
            Object.assign(model, {
                start: ref.el.selectionStart,
                end: ref.el.selectionEnd,
                direction: ref.el.selectionDirection,
            });
        }
    }
    onExternalClick(refName, async (ev) => {
        if (await preserveOnClickAwayPredicate(ev)) {
            return;
        }
        if (!ref.el) {
            return;
        }
        Object.assign(model, {
            start: ref.el.value.length,
            end: ref.el.value.length,
            direction: ref.el.selectionDirection,
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
            ref.el?.setSelectionRange(model.start, model.end, model.direction);
        },
        moveCursor(position) {
            model.start = model.end = position;
            if (ref.el && !ui.isSmall) {
                // In mobile, selection seems to adjust correctly.
                // Don't programmatically adjust, otherwise it shows soft keyboard!
                ref.el.selectionStart = ref.el.selectionEnd = position;
            }
        },
    };
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

export function useDiscussSystray() {
    const ui = useService("ui");
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
 * @param {string} refName The ref name of the element to listen for long presses on.
 * @param {Object} options
 * @param {() => void} [options.action] Function called when a long press is detected.
 * @param {() => boolean} [options.predicate] Optional function to enable long press detection.
 */
export function useLongPress(refName, { action, predicate = () => true } = {}) {
    const MOVE_TRESHOLD = 10;
    const ref = useRef(refName);
    let timer = null;
    let startX = 0;
    let startY = 0;

    function reset() {
        clearTimeout(timer);
        timer = null;
    }
    useLazyExternalListener(
        () => ref.el,
        "touchstart",
        (ev) => {
            if (!predicate()) {
                return;
            }
            const touch = ev.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
            timer = setTimeout(() => {
                action();
                reset();
            }, LONG_PRESS_DELAY);
        }
    );
    useLazyExternalListener(
        () => ref.el,
        "touchmove",
        (ev) => {
            if (!timer) {
                return;
            }
            const touch = ev.touches[0];
            const dx = touch.screenX - startX;
            const dy = touch.screenY - startY;
            if (Math.hypot(dx, dy) > MOVE_TRESHOLD) {
                reset();
            }
        }
    );
    useLazyExternalListener(() => ref.el, "touchend", reset);
    useLazyExternalListener(() => ref.el, "touchcancel", reset);
}

export const inDiscussCallViewProps = ["isPip?"];
export function useInDiscussCallView() {
    const component = useComponent();
    useSubEnv({
        inDiscussCallView: {
            get isPip() {
                return component.props.isPip;
            },
        },
    });
}
