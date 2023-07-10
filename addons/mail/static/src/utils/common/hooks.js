/* @odoo-module */

import {
    onMounted,
    onPatched,
    onWillPatch,
    onWillUnmount,
    useComponent,
    useRef,
    useState,
} from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

function useExternalListener(target, eventName, handler, eventParams) {
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
        if (ref.el && !ref.el.contains(ev.target)) {
            cb(ev, { downTarget, upTarget });
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

export function useHover(refName, callback = () => {}) {
    const ref = useRef(refName);
    const state = useState({ isHover: false });
    function onHover(hovered) {
        state.isHover = hovered;
        callback(hovered);
    }
    useExternalListener(
        () => ref.el,
        "mouseenter",
        (ev) => {
            if (ref.el.contains(ev.relatedTarget)) {
                return;
            }
            onHover(true);
        },
        true
    );
    useExternalListener(
        () => ref.el,
        "mouseleave",
        (ev) => {
            if (ref.el.contains(ev.relatedTarget)) {
                return;
            }
            onHover(false);
        },
        true
    );
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

export function useAutoScroll(refName, shouldScrollPredicate = () => true) {
    const ref = useRef(refName);
    let el = null;
    let isScrolled = true;
    const observer = new ResizeObserver(applyScroll);

    function onScroll() {
        isScrolled = Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) < 1;
    }
    function applyScroll() {
        if (isScrolled && shouldScrollPredicate()) {
            ref.el.scrollTop = ref.el.scrollHeight;
        }
    }
    onMounted(() => {
        el = ref.el;
        el.scrollTop = el.scrollHeight;
        observer.observe(el);
        el.addEventListener("scroll", onScroll);
    });
    onWillUnmount(() => {
        observer.unobserve(el);
        el.removeEventListener("scroll", onScroll);
    });
    onPatched(applyScroll);
}

export function useVisible(refName, cb, { init = false } = {}) {
    const ref = useRef(refName);
    const state = { isVisible: init };
    const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
            const newVal = entry.isIntersecting;
            if (state.isVisible !== newVal) {
                state.isVisible = newVal;
                cb();
            }
        }
    });
    let el;
    onMounted(observe);
    onWillUnmount(() => {
        if (!el) {
            return;
        }
        observer.unobserve(el);
    });
    onPatched(observe);

    function observe() {
        if (ref.el !== el) {
            if (el) {
                observer.unobserve(el);
                state.isVisible = false;
            }
            if (ref.el) {
                observer.observe(ref.el);
            }
        }
        el = ref.el;
    }
    return state;
}

/**
 * This hook eases adjusting scroll position by snapshotting scroll
 * properties of scrollable in onWillPatch / onPatched hooks.
 *
 * @param {string} refName
 * @param {function} param1.onWillPatch
 * @param {function} param1.onPatched
 */
export function useScrollSnapshot(refName, { onWillPatch: p_onWillPatch, onPatched: p_onPatched }) {
    const ref = useRef(refName);
    const snapshot = {
        scrollHeight: null,
        scrollTop: null,
        clientHeight: null,
    };
    onMounted(() => {
        const el = ref.el;
        Object.assign(snapshot, {
            scrollHeight: el.scrollHeight,
            scrollTop: el.scrollTop,
            clientHeight: el.clientHeight,
        });
    });
    onWillPatch(() => {
        const el = ref.el;
        Object.assign(snapshot, {
            scrollHeight: el.scrollHeight,
            scrollTop: el.scrollTop,
            clientHeight: el.clientHeight,
            ...p_onWillPatch(),
        });
    });
    onPatched(() => {
        const el = ref.el;
        Object.assign(snapshot, {
            scrollHeight: el.scrollHeight,
            scrollTop: el.scrollTop,
            clientHeight: el.clientHeight,
            ...p_onPatched(snapshot),
        });
    });
}

/**
 * @typedef {Object} MessageHighlight
 * @property {function} highlightMessage
 * @property {number|null} highlightedMessageId
 * @returns {MessageHighlight}
 */
export function useMessageHighlight(duration = 2000) {
    let timeout;
    /** @type {import("@mail/core/common/thread_service").ThreadService} */
    const threadService = useService("mail.thread");
    const state = useState({
        async highlightMessage(msgId, thread) {
            await threadService.loadAround(thread, msgId);
            const lastHighlightedMessageId = state.highlightedMessageId;
            clearHighlight();
            if (lastHighlightedMessageId === msgId) {
                // Give some time for the state to update.
                await new Promise(setTimeout);
            }
            state.highlightedMessageId = msgId;
            timeout = setTimeout(clearHighlight, duration);
        },
        highlightedMessageId: null,
    });
    function clearHighlight() {
        clearTimeout(timeout);
        timeout = null;
        state.highlightedMessageId = null;
    }
    return state;
}

export function useSelection({ refName, model, preserveOnClickAwayPredicate = () => false }) {
    const ref = useRef(refName);
    function onSelectionChange() {
        if (document.activeElement && document.activeElement === ref.el) {
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
    });
    onWillUnmount(() => {
        document.removeEventListener("selectionchange", onSelectionChange);
    });
    return {
        restore() {
            ref.el?.setSelectionRange(model.start, model.end, model.direction);
        },
        moveCursor(position) {
            model.start = model.end = position;
            ref.el.selectionStart = ref.el.selectionEnd = position;
        },
    };
}

/**
 * @param {string} refName
 * @param {ScrollPosition} [model] Model to store saved position.
 * @param {'bottom' | 'top'} [clearOn] Whether scroll
 * position should be cleared when reaching bottom or top.
 */
export function useScrollPosition(refName, model, clearOn) {
    const ref = useRef(refName);
    const self = {
        ref,
        model,
        restore() {
            if (!self.model) {
                return;
            }
            ref.el?.scrollTo({
                left: self.model.left,
                top: self.model.top,
            });
        },
    };
    function isScrolledToBottom() {
        if (!ref.el) {
            return false;
        }
        return Math.abs(ref.el.scrollTop + ref.el.clientHeight - ref.el.scrollHeight) < 1;
    }

    function onScrolled() {
        if (!self.model) {
            return;
        }
        if (
            (clearOn === "bottom" && isScrolledToBottom()) ||
            (clearOn === "top" && ref.el.scrollTop === 0)
        ) {
            return self.model.clear();
        }
        Object.assign(self.model, {
            top: ref.el.scrollTop,
            left: ref.el.scrollLeft,
        });
    }

    onMounted(() => {
        ref.el.addEventListener("scroll", onScrolled);
    });

    onWillUnmount(() => {
        ref.el.removeEventListener("scroll", onScrolled);
    });
    return self;
}

/**
 * @typedef {Object} MessageEdition
 * @property {composerOfThread} composerOfThread
 * @property {editingMessage} editingMessage
 * @property {function} exitEditMode
 * @returns {MessageEdition}
 */
export function useMessageEdition() {
    const state = useState({
        composerOfThread: null,
        editingMessage: null,
        exitEditMode() {
            state.editingMessage = null;
            if (state.composerOfThread) {
                state.composerOfThread.state.autofocus++;
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
 * @property {import("@mail/core/common/message_model").Message|null} message
 * @property {import("@mail/core/common/thread_model").Thread|null} thread
 * @property {function} toggle
 * @returns {MessageToReplyTo}
 */
export function useMessageToReplyTo() {
    return useState({
        cancel() {
            Object.assign(this, { message: null, thread: null });
        },
        /**
         * @param {import("@mail/core/common/thread_model").Thread} thread
         * @param {import("@mail/core/common/message_model").Message} message
         * @returns {boolean}
         */
        isNotSelected(thread, message) {
            return this.thread === thread && this.message !== message;
        },
        /**
         * @param {import("@mail/core/common/thread_model").Thread} thread
         * @param {import("@mail/core/common/message_model").Message} message
         * @returns {boolean}
         */
        isSelected(thread, message) {
            return this.thread === thread && this.message === message;
        },
        /** @type {import("@mail/core/common/message_model").Message|null} */
        message: null,
        /** @type {import("@mail/core/common/thread_model").Thread|null} */
        thread: null,
        /**
         * @param {import("@mail/core/common/thread_model").Thread} thread
         * @param {import("@mail/core/common/message_model").Message} message
         */
        toggle(thread, message) {
            if (this.message === message) {
                this.cancel();
            } else {
                Object.assign(this, { message, thread });
            }
        },
    });
}
