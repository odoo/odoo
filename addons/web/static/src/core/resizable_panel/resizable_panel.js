import { useComponent, useLayoutEffect, useRef } from "@web/owl2/utils";
import {
    Component,
    onMounted,
    onWillUpdateProps,
    onWillUnmount,
    props,
    t,
    useListener,
} from "@odoo/owl";

function useResizable({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth = () => 400,
    onResize = () => {},
    getResizeSide = () => "end",
}) {
    containerRef = typeof containerRef == "string" ? useRef(containerRef) : containerRef;
    handleRef = typeof handleRef == "string" ? useRef(handleRef) : handleRef;
    const props = useComponent().props;

    let minWidth = getMinWidth(props);
    let resizeSide = getResizeSide(props);
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
        () => [containerRef.el]
    );

    onMounted(() => {
        if (handleRef.el) {
            resize(Math.max(initialWidth, getMinWidth(props) || 0));
            handleRef.el.addEventListener("mousedown", onMouseDown);
        }
    });

    onWillUpdateProps((nextProps) => {
        minWidth = getMinWidth(nextProps);
        resizeSide = getResizeSide(nextProps);
    });

    onWillUnmount(() => {
        if (handleRef.el) {
            handleRef.el.removeEventListener("mousedown", onMouseDown);
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
        if (!isChangingSize || !containerRef.el) {
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
        const handlerSpacing = handleRef.el ? handleRef.el.offsetWidth / 2 : 10;
        const w = Math.max(minWidth, targetContainerWidth + handlerSpacing);
        const limit = getLimitWidth();
        return Math.min(w, limit - handlerSpacing);
    }

    function getContainerRect() {
        const container = containerRef.el;
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
        const offsetParent = containerRef.el.offsetParent;
        return offsetParent ? offsetParent.offsetWidth : window.innerWidth;
    }

    function resize(width) {
        containerRef.el.style.setProperty("width", `${width}px`);
        onResize(width);
    }
}

export const resizablePanelProps = {
    onResize: t.function().optional(() => () => {}),
    initialWidth: t.number().optional(),
    minWidth: t.number().optional(400),
    class: t.string().optional(""),
    slots: t.object(),
    handleSide: t.selection(["start", "end"]).optional("end"),
};

export class ResizablePanel extends Component {
    static template = "web_studio.ResizablePanel";

    static components = {};
    props = props(resizablePanelProps);

    setup() {
        useResizable({
            containerRef: "containerRef",
            handleRef: "handleRef",
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
