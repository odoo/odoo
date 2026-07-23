import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    signal,
    t,
    useListener,
    useProps,
} from "@odoo/owl";
import { useLayoutEffect } from "@web/owl2/utils";
import { resolveRefEl } from "@web/core/utils/ref_utils";

function useResizable({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth = () => 400,
    onResize = () => {},
    getResizeSide = () => "end",
}) {
    const resizeableProps = useProps(resizablePanelProps);

    let minWidth = getMinWidth(resizeableProps);
    let resizeSide = getResizeSide(resizeableProps);
    let isChangingSize = false;

    useListener(document, "mouseup", () => onMouseUp());
    useListener(document, "mousemove", (ev) => onMouseMove(ev));

    useListener(window, "resize", () => {
        const limit = getLimitWidth();
        if (getContainerRect().width >= limit) {
            resize(computeFinalWidth(limit));
        }
    });

    let docDirection;
    useLayoutEffect(
        (container) => {
            if (container) {
                docDirection = getComputedStyle(container).direction;
            }
        },
        () => [resolveRefEl(containerRef)]
    );

    onMounted(() => {
        const handleEl = resolveRefEl(handleRef);
        if (handleEl) {
            resize(Math.max(initialWidth, getMinWidth(resizeableProps) || 0));
            handleEl.addEventListener("mousedown", onMouseDown);
        }
    });

    onWillUpdateProps((nextProps) => {
        minWidth = getMinWidth(nextProps);
        resizeSide = getResizeSide(nextProps);
    });

    onWillUnmount(() => {
        const handleEl = resolveRefEl(handleRef);
        if (handleEl) {
            handleEl.removeEventListener("mousedown", onMouseDown);
        }
    });

    function onMouseDown() {
        isChangingSize = true;
        document.body.classList.add("pe-none", "user-select-none");
    }

    function onMouseUp() {
        isChangingSize = false;
        document.body.classList.remove("pe-none", "user-select-none");
    }

    function onMouseMove(ev) {
        if (!isChangingSize || !resolveRefEl(containerRef)) {
            return;
        }
        const direction =
            (docDirection === "ltr" && resizeSide === "end") ||
            (docDirection === "rtl" && resizeSide === "start")
                ? 1
                : -1;
        const fixedSide = direction === 1 ? "left" : "right";
        const containerRect = getContainerRect();
        const newWidth = (ev.clientX - containerRect[fixedSide]) * direction;
        resize(computeFinalWidth(newWidth));
    }

    function computeFinalWidth(targetContainerWidth) {
        const handleEl = resolveRefEl(handleRef);
        const handlerSpacing = handleEl ? handleEl.offsetWidth / 2 : 10;
        const w = Math.max(minWidth, targetContainerWidth + handlerSpacing);
        const limit = getLimitWidth();
        return Math.min(w, limit - handlerSpacing);
    }

    function getContainerRect() {
        const container = resolveRefEl(containerRef);
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
        const offsetParent = resolveRefEl(containerRef).offsetParent;
        return offsetParent ? offsetParent.offsetWidth : window.innerWidth;
    }

    function resize(width) {
        resolveRefEl(containerRef).style.setProperty("width", `${width}px`);
        onResize(width);
    }
}

export const resizablePanelProps = {
    onResize: t.function().optional(() => () => {}),
    initialWidth: t.number().optional(),
    minWidth: t.number().optional(400),
    class: t.string().optional(""),
    handleSide: t.selection(["start", "end"]).optional("end"),
};

export class ResizablePanel extends Component {
    static template = "web_studio.ResizablePanel";

    static components = {};
    props = useProps(resizablePanelProps);

    containerRef = signal.ref();
    handleRef = signal.ref();

    setup() {
        useResizable({
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
