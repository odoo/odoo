import {
    Component,
    onMounted,
    onWillPatch,
    signal,
    t,
    useEffect,
    useListener,
    useProps,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";

export function useResizablePanel({
    containerRef,
    handleRef,
    foldedRef = () => null,
    initialWidth = 400,
    getMinWidth,
    getMaxWidth = () => Infinity,
    onFold,
    onUnfold = () => {},
    onResize = () => {},
    getResizeSide = () => "end",
    resizeOnMount = true,
    getHandlerSpacing = (handleEl) => (handleEl ? handleEl.offsetWidth / 2 : 10),
}) {
    const resizeableProps = useProps(resizablePanelProps);

    const isChangingSize = signal(false);
    let grabOffset = 0;
    let isFolded = false;
    let docDirection;
    let currentWidth;
    let pendingMountResize = false;

    let cssWidth;
    useEffect(() => {
        const el = containerRef();
        if (!el) {
            return;
        }
        if (cssWidth === undefined) {
            cssWidth = el.offsetWidth;
        }
        if (pendingMountResize) {
            pendingMountResize = false;
            resize(getMountWidth());
        } else if (currentWidth !== undefined) {
            el.style.setProperty("width", `${currentWidth}px`);
        }
    });
    const resolveMinWidth = getMinWidth || (() => cssWidth ?? 0);

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
        if (!containerRef()) {
            return;
        }
        const limit = getLimitWidth();
        if (getContainerRect().width >= limit) {
            resize(computeFinalWidth(limit));
        }
    });

    onMounted(() => {
        if (resizeOnMount && handleRef()) {
            if (containerRef()) {
                resize(getMountWidth());
            } else {
                pendingMountResize = true;
            }
        }
    });

    useListener(handleRef, "mousedown", onMouseDown);

    function getMountWidth() {
        return Math.max(initialWidth, resolveMinWidth(resizeableProps) || 0);
    }

    function onMouseDown(ev) {
        isChangingSize.set(true);
        isFolded = !containerRef();
        docDirection = getComputedStyle(handleRef()).direction;
        const el = containerRef() || foldedRef();
        grabOffset = getContainerRect(el).width - getPointerWidth(ev, el);
        document.body.classList.add("pe-none", "user-select-none");
        document.documentElement.style.cursor = "col-resize";
    }

    function stopChangingSize() {
        isChangingSize.set(false);
        document.body.classList.remove("pe-none", "user-select-none");
        document.documentElement.style.cursor = "";
    }

    function onMouseMove(ev) {
        const container = containerRef();
        const foldedEl = foldedRef();
        if (!isChangingSize() || !(container || foldedEl)) {
            return;
        }
        const el = container || foldedEl;
        const newWidth = getPointerWidth(ev, el) + grabOffset;
        const minWidth = resolveMinWidth(resizeableProps) || 0;
        if (isFolded) {
            const unfoldWidth = Math.max(
                0.75 * minWidth,
                foldedEl ? getContainerRect(foldedEl).width : 0
            );
            if (newWidth >= unfoldWidth) {
                isFolded = false;
                onUnfold();
            }
            return;
        }
        if (onFold && newWidth <= minWidth / 2) {
            isFolded = true;
            onFold();
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
        const resizeSide = getResizeSide(resizeableProps);
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        return (ev.clientX - getContainerRect(el)[fixedSide]) * direction;
    }

    function computeFinalWidth(targetContainerWidth) {
        const handlerSpacing = getHandlerSpacing(handleRef());
        const w = Math.max(resolveMinWidth(resizeableProps), targetContainerWidth);
        const limit = Math.min(getLimitWidth(), getMaxWidth(resizeableProps));
        return Math.min(w, limit - handlerSpacing);
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
        onResize(width);
    }

    return { isChangingSize };
}

export const resizablePanelProps = {
    onResize: t.function().optional(() => () => {}),
    initialWidth: t.number().optional(),
    minWidth: t.number().optional(400),
    class: t.string().optional(""),
    handleSide: t.selection(["start", "end"]).optional("end"),
    outerHandle: t.boolean().optional(false),
};

export class ResizablePanel extends Component {
    static template = "web.ResizablePanel";

    static components = {};
    props = useProps(resizablePanelProps);

    containerRef = signal.ref();
    handleRef = signal.ref();

    setup() {
        this.resizable = useResizablePanel({
            containerRef: this.containerRef,
            handleRef: this.handleRef,
            onResize: this.props.onResize,
            initialWidth: Math.max(this.props.minWidth, this.props.initialWidth || 400),
            getMinWidth: (props) => props.minWidth,
            getResizeSide: (props) => props.handleSide,
        });
    }

    get class() {
        const classes = this.props.class.split(" ");
        if (!classes.some((cls) => cls.startsWith("position-"))) {
            classes.push("position-relative");
        }
        return classes.join(" ");
    }

    handleClass() {
        const side = this.props.handleSide;
        const outerHandle = this.props.outerHandle;
        return {
            "start-0": !outerHandle && side === "start",
            "end-0": !outerHandle && side === "end",
            [`o_resizable_panel_outer_handle o_resizable_panel_outer_handle_${side} d-flex justify-content-center`]:
                outerHandle,
            "opacity-0 opacity-100-hover": outerHandle && !this.resizable.isChangingSize(),
        };
    }
}
