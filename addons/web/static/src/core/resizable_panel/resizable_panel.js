import {
    Component,
    computed,
    onWillPatch,
    signal,
    t,
    useEffect,
    useListener,
    useProps,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";

function useResizablePanel({ props, containerRef, handleRef, foldedRef }) {
    const initialWidth = props.initialWidth ?? 0;
    let isChangingSize = false;
    let grabOffset = 0;
    let isFolded = false;
    let docDirection;
    let currentWidth;

    useEffect(() => {
        const el = containerRef();
        if (!el || !handleRef()) {
            return;
        }
        if (currentWidth === undefined) {
            resize(getMountWidth());
        } else {
            el.style.setProperty("width", `${currentWidth}px`);
        }
    });

    let wasFolded;
    let lastWidth;
    let sizeAnimation;
    let sizeAnimationFrom;
    const getSizeKeyframes = (to) => ({ width: [`${sizeAnimationFrom}px`, `${to}px`] });
    onWillPatch(() => {
        lastWidth = (containerRef() || foldedRef())?.offsetWidth;
    });
    useEffect(() => {
        const el = containerRef() || foldedRef();
        if (!el) {
            return;
        }
        const folded = !containerRef();
        if (
            wasFolded !== undefined &&
            folded !== wasFolded &&
            !browser.matchMedia("(prefers-reduced-motion: reduce)").matches
        ) {
            sizeAnimationFrom = lastWidth;
            sizeAnimation = el.animate(getSizeKeyframes(el.offsetWidth), {
                duration: 125,
                easing: "ease-out",
            });
            el.animate({ opacity: [0, 1] }, { duration: 200, easing: "ease-out" });
            el.style.setProperty("overflow", "hidden", "important");
            sizeAnimation.addEventListener("finish", () => el.style.removeProperty("overflow"));
        }
        wasFolded = folded;
    });

    useListener(document, "mouseup", () => stopChangingSize());
    useListener(document, "mousemove", (ev) => onMouseMove(ev));

    useListener(window, "resize", () => {
        if (!containerRef() || !handleRef()) {
            return;
        }
        const limit = getLimitWidth();
        if (getContainerRect().width >= limit) {
            resize(computeFinalWidth(limit));
        }
    });

    useListener(handleRef, "mousedown", onMouseDown);
    // Only once the grip is reached: the content, and so its scrollbar, changes meanwhile.
    useListener(handleRef, "pointerenter", updateGripOnScrollbar);

    function getMaxWidth() {
        return props.maxWidth ?? (props.onToggle ? 0.5 * window.innerWidth : Infinity);
    }

    function getMountWidth() {
        return Math.max(initialWidth, props.minWidth);
    }

    function setChangingSize(value) {
        isChangingSize = value;
        handleRef().classList.toggle("o_resizable_panel_resizing", value);
    }

    function onMouseDown(ev) {
        if (ev.button !== 0) {
            return;
        }
        setChangingSize(true);
        isFolded = !containerRef();
        docDirection = getComputedStyle(handleRef()).direction;
        const el = containerRef() || foldedRef();
        grabOffset = getContainerRect(el).width - getPointerWidth(ev, el);
        document.body.classList.add("pe-none", "user-select-none");
        document.documentElement.style.cursor = "col-resize";
    }

    function stopChangingSize() {
        if (!isChangingSize) {
            return;
        }
        setChangingSize(false);
        document.body.classList.remove("pe-none", "user-select-none");
        document.documentElement.style.cursor = "";
        updateGripOnScrollbar();
    }

    function onMouseMove(ev) {
        const container = containerRef();
        const foldedEl = foldedRef();
        if (!isChangingSize || !(container || foldedEl)) {
            return;
        }
        // The mouseup is missed when released outside the window or swallowed by a context menu.
        if (!(ev.buttons & 1)) {
            stopChangingSize();
            return;
        }
        const el = container || foldedEl;
        const newWidth = getPointerWidth(ev, el) + grabOffset;
        const minWidth = props.minWidth;
        if (isFolded) {
            const unfoldWidth = Math.max(
                0.75 * minWidth,
                foldedEl ? getContainerRect(foldedEl).width : 0
            );
            if (newWidth >= unfoldWidth) {
                isFolded = false;
                props.onToggle();
            }
            return;
        }
        if (props.onToggle && newWidth <= minWidth / 2) {
            isFolded = true;
            props.onToggle();
            return;
        }
        if (container) {
            resize(computeFinalWidth(newWidth));
        }
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} el
     */
    function getPointerWidth(ev, el) {
        const resizeSide = props.handleSide;
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        return (ev.clientX - getContainerRect(el)[fixedSide]) * direction;
    }

    function computeFinalWidth(targetContainerWidth) {
        const w = Math.max(props.minWidth, targetContainerWidth);
        const limit = Math.min(getLimitWidth(), getMaxWidth());
        return Math.min(w, limit);
    }

    /**
     * Moves the grip off the scrollbar along the edge of the panel, if any, to leave it free to
     * grab. Scrollbars are on the inline end.
     */
    function updateGripOnScrollbar() {
        if (sizeAnimation?.playState === "running") {
            sizeAnimation.addEventListener("finish", updateGripOnScrollbar, { once: true });
            return;
        }
        handleRef().classList.toggle(
            "o_resizable_panel_over_scrollbar",
            props.handleSide === "end" && Boolean(containerRef()) && isGripOnScrollbar()
        );
    }

    /**
     * Whether the grip is on a scrollbar, at the edge of the panel or a bit in: off the client
     * box of what scrolls there, not in its borders nor in the space kept for a scrollbar it
     * doesn't have.
     */
    function isGripOnScrollbar() {
        const rect = containerRef().getBoundingClientRect();
        const isRtl = getComputedStyle(containerRef()).direction === "rtl";
        const y = rect.top + rect.height / 2;
        return [4, 8, 12].some((offset) => {
            const x = isRtl ? rect.left + offset : rect.right - offset;
            const el = document
                .elementsFromPoint(x, y)
                .find((el) => !handleRef().contains(el));
            const clientLeft = el.getBoundingClientRect().left + el.clientLeft;
            return (
                el.scrollHeight > el.clientHeight &&
                (x < clientLeft || x >= clientLeft + el.clientWidth)
            );
        });
    }

    function getContainerRect(container = containerRef()) {
        const offsetParent = container.offsetParent;
        let containerRect = {};
        if (!offsetParent) {
            containerRect = container.getBoundingClientRect();
        } else {
            containerRect.left = container.offsetLeft;
            containerRect.right = container.offsetLeft + container.offsetWidth;
            containerRect.width = container.offsetWidth;
        }
        return containerRect;
    }

    function getLimitWidth() {
        const offsetParent = containerRef().offsetParent;
        return offsetParent ? offsetParent.offsetWidth : window.innerWidth;
    }

    function resize(width) {
        if (sizeAnimation?.playState === "running") {
            sizeAnimation.effect.setKeyframes(getSizeKeyframes(width));
        }
        currentWidth = width;
        containerRef().style.setProperty("width", `${width}px`);
        props.onResize(width);
    }
}

/**
 * A panel resized by dragging the handle on its `handleSide` edge.
 *
 * Given `onToggle`, it is a side panel next to the content, by default at most half as wide as the
 * window: it also folds, into a strip showing the `folded` slot, by dragging its handle or with a
 * toggle on its outer edge.
 */
export class ResizablePanel extends Component {
    static template = "web.ResizablePanel";

    props = useProps({
        onResize: t.function().optional(() => () => {}),
        initialWidth: t.number().optional(),
        minWidth: t.number().optional(400),
        maxWidth: t.number().optional(),
        class: t.string().optional(""),
        handleSide: t.selection(["start", "end"]).optional("end"),
        resizable: t.boolean().optional(true),
        folded: t.boolean().optional(false),
        onToggle: t.function().optional(),
        slots: t.object().optional(),
    });

    containerRef = signal.ref();
    foldedRef = signal.ref();
    handleRef = signal.ref();

    class = computed(() => {
        const classes = this.props.class.split(" ");
        if (!classes.some((cls) => cls.startsWith("position-"))) {
            classes.push("position-relative");
        }
        return classes.join(" ");
    });
    edgeClass = computed(() => {
        const side = this.props.handleSide === "start" ? "start-0" : "end-0";
        return this.props.onToggle
            ? "o_resizable_panel_edge"
            : `position-absolute top-0 bottom-0 ${side}`;
    });
    toggleSide = computed(() => (this.props.handleSide === "end" ? "start" : "end"));
    toggleLabel = computed(() =>
        this.props.folded ? _t("Expand side panel") : _t("Collapse side panel")
    );

    setup() {
        useResizablePanel({
            props: this.props,
            containerRef: this.containerRef,
            handleRef: this.handleRef,
            foldedRef: this.foldedRef,
        });
    }
}
