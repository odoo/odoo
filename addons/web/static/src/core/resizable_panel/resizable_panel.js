import {
    Component,
    computed,
    onPatched,
    onWillUnmount,
    signal,
    t,
    useListener,
    useProps,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/** How far in from the edge of the panel, in px, the grip covers what is under it. */
const GRIP_REACH = 12;

let scrollbarWidth;
let scrollbarWidthPixelRatio;

/**
 * The space the browser keeps for a vertical scrollbar: none for an overlay one (e.g. Firefox,
 * macOS). The same for every element, it only changes with the zoom, which changes the device
 * pixel ratio.
 */
function getScrollbarWidth() {
    if (scrollbarWidthPixelRatio !== window.devicePixelRatio) {
        scrollbarWidthPixelRatio = window.devicePixelRatio;
        const probe = document.createElement("div");
        probe.style.cssText =
            "position: absolute; visibility: hidden; overflow-y: scroll; width: 100px;";
        document.body.append(probe);
        scrollbarWidth = probe.offsetWidth - probe.clientWidth;
        probe.remove();
    }
    return scrollbarWidth;
}

function useResizablePanel({ props, folded, containerRef, handleRef, foldedRef }) {
    let isChangingSize = false;
    let grabOffset = 0;
    let docDirection;
    let currentWidth = getBoundedWidth(props.initialWidth ?? 0);

    let isToggling = false;
    let sizeAnimation;
    let sizeAnimationFrom;
    const getSizeKeyframes = (to) => ({ width: [`${sizeAnimationFrom}px`, `${to}px`] });
    const isFolded = computed(() => props.foldable && folded());

    function toggleFold() {
        sizeAnimationFrom = (containerRef() || foldedRef()).offsetWidth;
        isToggling = true;
        folded.set(!folded());
        if (!folded()) {
            applyWidthBounds();
        }
        props.onToggle(folded());
    }

    // Once rendered, the panel or its folded strip grows or shrinks from the former width.
    onPatched(() => {
        if (!isToggling) {
            return;
        }
        isToggling = false;
        // Web animations ignore the reduced motion media queries of the stylesheets.
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const el = containerRef() || foldedRef();
        sizeAnimation = el.animate(getSizeKeyframes(el.offsetWidth), {
            duration: 125,
            easing: "ease-out",
        });
        el.animate({ opacity: [0, 1] }, { duration: 200, easing: "ease-out" });
        el.style.setProperty("overflow", "hidden", "important");
        sizeAnimation.addEventListener("finish", () => el.style.removeProperty("overflow"));
    });
    onWillUnmount(() => sizeAnimation?.cancel());

    useListener(document, "mouseup", () => stopChangingSize());
    useListener(document, "mousemove", (ev) => onMouseMove(ev));

    useListener(window, "resize", () => {
        const container = containerRef();
        if (!container) {
            applyWidthBounds();
            return;
        }
        container.style.setProperty(
            "--o-resizable-panel-scrollbar-width",
            `${getScrollbarWidth()}px`
        );
        const width = computeFinalWidth(currentWidth);
        if (width !== currentWidth) {
            resize(width);
        }
    });

    useListener(handleRef, "mousedown", onMouseDown);
    // Only once the grip is reached: the content, and so its scrollbar, changes meanwhile.
    useListener(handleRef, "pointerenter", updateGripOnScrollbar);

    function getMaxWidth() {
        return props.maxWidth ?? (props.foldable ? 0.5 * window.innerWidth : Infinity);
    }

    /** Within the bounds that do not depend on its surroundings. */
    function getBoundedWidth(width) {
        return Math.max(props.minWidth, Math.min(width, getMaxWidth()));
    }

    /** Brings the width back within its bounds, e.g. on a window narrower than when it was set. */
    function applyWidthBounds() {
        const width = getBoundedWidth(currentWidth);
        if (width !== currentWidth) {
            currentWidth = width;
            props.onResize(width);
        }
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
        if (isFolded()) {
            const unfoldWidth = Math.max(
                0.75 * minWidth,
                foldedEl ? getContainerRect(foldedEl).width : 0
            );
            if (newWidth >= unfoldWidth) {
                toggleFold();
            }
            return;
        }
        if (props.foldable && newWidth <= minWidth / 2) {
            toggleFold();
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
     * Whether the grip is on a scrollbar. A scrollbar is at the inline end of what scrolls, in the
     * space it keeps or over the content for an overlay one: the grip is on it when what is under
     * the grip scrolls.
     */
    function isGripOnScrollbar() {
        const rect = containerRef().getBoundingClientRect();
        const isRtl = getComputedStyle(containerRef()).direction === "rtl";
        const x = isRtl ? rect.left + GRIP_REACH : rect.right - GRIP_REACH;
        const y = rect.top + rect.height / 2;
        return document
            .elementsFromPoint(x, y)
            .some(
                (el) =>
                    containerRef().contains(el) &&
                    !handleRef().contains(el) &&
                    el.scrollHeight > el.clientHeight &&
                    ["auto", "scroll"].includes(getComputedStyle(el).overflowY)
            );
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

    return {
        toggleFold,
        getWidth: () => currentWidth,
    };
}

/**
 * A panel resized by dragging the handle on its `handleSide` edge.
 *
 * When `foldable`, it is a side panel next to the content, by default at most half as wide as the
 * window: it also folds, into a strip showing the `folded` slot, by dragging its handle or with a
 * toggle on its outer edge. Its content can fold it too, with the `toggleFold` of its slot scope,
 * in place of that toggle when `hasToggle` is false. It owns its fold state: it starts as
 * `initialFolded` and `onToggle` reports each change. The panel and its strip fade in as they
 * replace each other.
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
        foldable: t.boolean().optional(false),
        initialFolded: t.boolean().optional(false),
        onToggle: t.function().optional(() => () => {}),
        hasToggle: t.boolean().optional(true),
        foldedClass: t.string().optional("o_resizable_panel_folded_text px-3 pt-2 pb-5"),
        slots: t.object().optional(),
    });

    folded = signal(this.props.initialFolded);
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
        return this.props.foldable
            ? "o_resizable_panel_edge"
            : `position-absolute top-0 bottom-0 ${side}`;
    });
    toggleSide = computed(() => (this.props.handleSide === "end" ? "start" : "end"));
    toggleLabel = computed(() =>
        this.folded() ? _t("Expand side panel") : _t("Collapse side panel")
    );

    setup() {
        this.resizablePanel = useResizablePanel({
            props: this.props,
            folded: this.folded,
            containerRef: this.containerRef,
            handleRef: this.handleRef,
            foldedRef: this.foldedRef,
        });
    }

    /**
     * Rendered on each new panel element: it is at its width before anything measures it. The
     * content can keep the space of its scrollbar with `--o-resizable-panel-scrollbar-width`.
     */
    getStyle() {
        return [
            `width: ${this.resizablePanel.getWidth()}px`,
            `--o-resizable-panel-scrollbar-width: ${getScrollbarWidth()}px`,
        ].join("; ");
    }
}
