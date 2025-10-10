import {
    onMounted,
    onPatched,
    onWillUnmount,
    useComponent,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { Deferred } from "@web/core/utils/concurrency";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
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
 * @param {string | string[]} refNames name of refs that determine whether this is in state "hovering".
 *   ref name that end with "*" means it takes parented HTML node into account too. Useful for floating
 *   menu where dropdown menu container is not accessible.
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
        targets.push({
            ref: refName.endsWith("*")
                ? useRef(refName.substring(0, refName.length - 1))
                : useRef(refName),
        });
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
        _count: 0,
        _isHover: false,
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
                }, 200);
            }
        }
        wasHovering = hovering;
    }
    function onmouseenter(ev) {
        if (state.isHover) {
            return;
        }
        for (const target of targets) {
            if (!target.ref.el) {
                continue;
            }
            if (target.ref.el.contains(ev.target)) {
                setHover(true);
                lastHoveredTarget = target;
                return;
            }
        }
    }
    function onmouseleave(ev) {
        if (!state.isHover) {
            return;
        }
        for (const target of targets) {
            if (!target.ref.el) {
                continue;
            }
            if (target.ref.el.contains(ev.relatedTarget)) {
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
        useEffect(() => {
            if (lastHoveredTarget && !lastHoveredTarget.ref.el) {
                setHover(false);
                lastHoveredTarget = null;
            }
        }, stateObserver);
    }
    return state;
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
        ref.el.addEventListener("scroll", onScroll);
    });
    onWillUnmount(() => {
        ref.el.removeEventListener("scroll", onScroll);
    });
}

/**
 * @param {string} refName
 * @param {function} cb
 */
export function useVisible(refName, cb, { ready = true } = {}) {
    const ref = useRef(refName);
    const state = useState({
        isVisible: undefined,
        ready,
    });
    function setValue(value) {
        state.isVisible = value;
        cb(state.isVisible);
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

export function useMessageHighlight(duration = 2000) {
    let timeout;
    const notification = useState(useService("notification"));
    const state = useState({
        clearHighlight() {
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
            if (thread.notEq(message.thread)) {
                return;
            }
            await thread.loadAround(message.id);
            if (message.isEmpty) {
                notification.add(_t("The message has been deleted."));
                return;
            }
            const lastHighlightedMessageId = state.highlightedMessageId;
            this.clearHighlight();
            if (lastHighlightedMessageId === message.id) {
                // Give some time for the state to update.
                await new Promise(setTimeout);
            }
            thread.scrollTop = undefined;
            state.highlightedMessageId = message.id;
            timeout = browser.setTimeout(() => this.clearHighlight(), duration);
        },
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

export function useSelection({ refName, model, preserveOnClickAwayPredicate = () => false }) {
    const ui = useState(useService("ui"));
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
            if (!ui.isSmall) {
                // In mobile, selection seems to adjust correctly.
                // Don't programmatically adjust, otherwise it shows soft keyboard!
                ref.el.selectionStart = ref.el.selectionEnd = position;
            }
        },
    };
}

export function useMessageEdition() {
    const state = useState({
        /** @type {import('@mail/core/common/composer').Composer} */
        composerOfThread: null,
        /** @type {import('@mail/core/common/message_model').Message} */
        editingMessage: null,
        exitEditMode() {
            state.editingMessage = null;
            if (state.composerOfThread) {
                state.composerOfThread.props.composer.autofocus++;
            }
        },
    });
    return state;
}

/**
 * @typedef {Object} MessageToReplyTo
 * @property {function} cancel
 * @property {function} isNotSelected
 * @property {function} isSelected
 * @property {import("models").Message|null} message
 * @property {import("models").Thread|null} thread
 * @property {function} toggle
 * @returns {MessageToReplyTo}
 */
export function useMessageToReplyTo() {
    return useState({
        cancel() {
            Object.assign(this, { message: null, thread: null });
        },
        /**
         * @param {import("models").Thread} thread
         * @param {import("models").Message} message
         * @returns {boolean}
         */
        isNotSelected(thread, message) {
            return thread.eq(this.thread) && message.notEq(this.message);
        },
        /**
         * @param {import("models").Thread} thread
         * @param {import("models").Message} message
         * @returns {boolean}
         */
        isSelected(thread, message) {
            return thread.eq(this.thread) && message.eq(this.message);
        },
        /** @type {import("models").Message|null} */
        message: null,
        /** @type {import("models").Thread|null} */
        thread: null,
        /**
         * @param {import("models").Thread} thread
         * @param {import("models").Message} message
         */
        toggle(thread, message) {
            if (message.eq(this.message)) {
                this.cancel();
            } else {
                Object.assign(this, { message, thread });
            }
        },
    });
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
    const ui = useState(useService("ui"));
    return {
        class: "o-mail-DiscussSystray-class",
        get contentClass() {
            return `d-flex flex-column flex-grow-1 ${
                ui.isSmall ? "overflow-auto w-100 mh-100" : ""
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
        const { height } = getRect(ctx.current.element);
        ctx.current.container = document.createElement("div");
        addStyle(ctx.current.container, {
            position: "fixed",
            top: 0,
            bottom: `${height}px`,
            left: 0,
            right: 0,
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop({ ctx, getRect }) {
        const { top, left } = getRect(ctx.current.element);
        return { top, left };
    },
});
