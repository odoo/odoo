import { Component, onMounted, signal, t, useEffect, useListener, useProps } from "@odoo/owl";

export function useResizablePanel({
    containerRef,
    handleRef,
    foldedRef = () => null,
    initialWidth = 400,
    getMinWidth,
    getMaxWidth = () => Infinity,
    getFoldWidth = () => null,
    onFold = () => {},
    onUnfold = () => {},
    onResize = () => {},
    getResizeSide = () => "end",
    resizeOnMount = true,
    getHandlerSpacing = (handleEl) => (handleEl ? handleEl.offsetWidth / 2 : 10),
}) {
    const resizeableProps = useProps(resizablePanelProps);

    let isChangingSize = false;
    let hasToggledFold = false;
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

    useListener(document, "mouseup", () => onMouseUp());
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

    function onMouseDown() {
        isChangingSize = true;
        hasToggledFold = false;
        docDirection = getComputedStyle(handleRef()).direction;
        document.body.classList.add("pe-none", "user-select-none");
        document.documentElement.style.cursor = "col-resize";
    }

    function onMouseUp() {
        stopChangingSize();
    }

    function stopChangingSize() {
        isChangingSize = false;
        document.body.classList.remove("pe-none", "user-select-none");
        document.documentElement.style.cursor = "";
    }

    function onMouseMove(ev) {
        const container = containerRef();
        const foldedEl = foldedRef();
        if (!isChangingSize || !(container || foldedEl)) {
            return;
        }
        const resizeSide = getResizeSide(resizeableProps);
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        const containerRect = getContainerRect(container || foldedEl);
        const newWidth = (ev.clientX - containerRect[fixedSide]) * direction;
        const foldWidth = getFoldWidth(resizeableProps);
        if (!container) {
            const unfoldWidth = Number.isFinite(foldWidth) ? foldWidth : containerRect.width;
            if (!hasToggledFold && newWidth > unfoldWidth) {
                hasToggledFold = true;
                onUnfold();
            }
            return;
        }
        if (!hasToggledFold && foldWidth != null && newWidth <= foldWidth) {
            stopChangingSize();
            onFold();
            return;
        }
        resize(computeFinalWidth(newWidth));
    }

    function computeFinalWidth(targetContainerWidth) {
        const handlerSpacing = getHandlerSpacing(handleRef());
        const w = Math.max(resolveMinWidth(resizeableProps), targetContainerWidth + handlerSpacing);
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
        currentWidth = width;
        containerRef().style.setProperty("width", `${width}px`);
        onResize(width);
    }

    return {
        getCssWidth: () => cssWidth,
    };
}

export const resizablePanelProps = {
    onResize: t.function().optional(() => () => {}),
    initialWidth: t.number().optional(),
    minWidth: t.number().optional(400),
    class: t.string().optional(""),
    handleSide: t.selection(["start", "end"]).optional("end"),
};

export class ResizablePanel extends Component {
    static template = "web.ResizablePanel";

    static components = {};
    props = useProps(resizablePanelProps);

    containerRef = signal.ref();
    handleRef = signal.ref();

    setup() {
        useResizablePanel({
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
}
