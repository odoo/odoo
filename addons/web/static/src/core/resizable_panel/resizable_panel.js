import {
    Component,
    onMounted,
    onWillUnmount,
    signal,
    t,
    useListener,
    useOnChange,
    useProps,
} from "@odoo/owl";

function useResizable({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth = () => 400,
    onResize = () => {},
    getResizeSide = () => "end",
}) {
    const resizeableProps = useProps(resizablePanelProps);

    const isChangingSize = signal(false);
    let grabOffset = 0;

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
        const handleEl = handleRef();
        if (handleEl) {
            resize(Math.max(initialWidth, getMinWidth(resizeableProps) || 0));
            handleEl.addEventListener("mousedown", onMouseDown);
        }
    });

    onWillUnmount(() => {
        handleRef()?.removeEventListener("mousedown", onMouseDown);
    });

    function onMouseDown(ev) {
        isChangingSize.set(true);
        grabOffset = getContainerRect().width - getPointerWidth(ev);
        document.body.classList.add("pe-none", "user-select-none");
    }

    function onMouseUp() {
        isChangingSize.set(false);
        document.body.classList.remove("pe-none", "user-select-none");
    }

    function onMouseMove(ev) {
        if (!isChangingSize() || !containerRef()) {
            return;
        }
        resize(computeFinalWidth(getPointerWidth(ev) + grabOffset));
    }

    /** @param {MouseEvent} ev */
    function getPointerWidth(ev) {
        const resizeSide = getResizeSide(resizeableProps);
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        return (ev.clientX - getContainerRect()[fixedSide]) * direction;
    }

    function computeFinalWidth(targetContainerWidth) {
        const handleEl = handleRef();
        const handlerSpacing = handleEl ? handleEl.offsetWidth / 2 : 10;
        const w = Math.max(getMinWidth(resizeableProps), targetContainerWidth);
        const limit = getLimitWidth();
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
    static template = "web_studio.ResizablePanel";

    static components = {};
    props = useProps(resizablePanelProps);

    containerRef = signal.ref();
    handleRef = signal.ref();

    setup() {
        this.resizable = useResizable({
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
