/* @odoo-module */

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
        if (ref.el && !ref.el.contains(ev.target)) {
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

export function useHover(refName, callback = () => {}) {
    const ref = useRef(refName);
    const state = useState({ isHover: false });
    function onHover(hovered) {
        state.isHover = hovered;
        callback(hovered);
    }
    useLazyExternalListener(
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
    useLazyExternalListener(
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

/**
 * @param {string} refName
 * @param {function} cb
 */
export function useVisible(refName, cb, { init = false, ready = true } = {}) {
    const ref = useRef(refName);
    const state = useState({
        isVisible: init,
        ready,
    });
    function setValue(value) {
        state.isVisible = value;
        cb();
    }
    const observer = new IntersectionObserver((entries) => {
        setValue(entries.at(-1).isIntersecting);
    });
    useEffect(
        (el, ready) => {
            if (el && ready) {
                observer.observe(el);
                return () => {
                    setValue(false);
                    observer.unobserve(el);
                };
            }
        },
        () => [ref.el, state.ready]
    );
    return state;
}

/**
 * @typedef {Object} MessageHighlight
 * @property {function} clearHighlight
 * @property {function} highlightMessage
 * @property {number|null} highlightedMessageId
 * @returns {MessageHighlight}
 */
export function useMessageHighlight(duration = 2000) {
    let timeout;
    const threadService = useService("mail.thread");
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
            if (thread.notEq(message.originThread)) {
                return;
            }
            await threadService.loadAround(thread, message.id);
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
        highlightedMessageId: null,
    });
    return state;
}

export function useSelection({ refName, model, preserveOnClickAwayPredicate = () => false }) {
    const ui = useState(useService("ui"));
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
            return `d-flex flex-column flex-grow-1 bg-view ${
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
