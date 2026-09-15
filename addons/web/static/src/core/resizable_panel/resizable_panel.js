import {
    Component,
    onMounted,
    signal,
    t,
    useEffect,
    useListener,
    useOnChange,
    useProps,
} from "@odoo/owl";

export function useResizablePanel({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth,
    getMaxWidth = () => Infinity,
    getFoldWidth = () => null,
    onFold = () => {},
    onResize = () => {},
    getResizeSide = () => "end",
    resizeOnMount = true,
    getHandlerSpacing = (handleEl) => (handleEl ? handleEl.offsetWidth / 2 : 10),
}) {
    const resizeableProps = useProps(resizablePanelProps);

    let isChangingSize = false;

    let cssWidth;
    useEffect(() => {
        const el = containerRef();
        if (el && cssWidth === undefined) {
            cssWidth = el.offsetWidth;
        }
    });
    const resolveMinWidth = getMinWidth || (() => cssWidth ?? 0);

    useListener(document, "mouseup", () => onMouseUp());
    useListener(document, "mousemove", (ev) => onMouseMove(ev));

    useListener(window, "resize", () => {
        const limit = getLimitWidth();
        if (getContainerRect().width >= limit) {
            resize(computeFinalWidth(limit));
        }
    });

    let docDirection;
    useOnChange(
        () => [containerRef()],
        (container) => {
            if (container) {
                docDirection = getComputedStyle(container).direction;
            }
        }
    );

    onMounted(() => {
        if (resizeOnMount && handleRef()) {
            resize(Math.max(initialWidth, resolveMinWidth(resizeableProps) || 0));
        }
    });

    useListener(handleRef, "mousedown", onMouseDown);

    function onMouseDown() {
        isChangingSize = true;
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
        if (!isChangingSize || !containerRef()) {
            return;
        }
        const resizeSide = getResizeSide(resizeableProps);
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        const containerRect = getContainerRect();
        const newWidth = (ev.clientX - containerRect[fixedSide]) * direction;
        const foldWidth = getFoldWidth(resizeableProps);
        if (foldWidth != null && newWidth <= foldWidth) {
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

    function getContainerRect() {
        const container = containerRef();
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
