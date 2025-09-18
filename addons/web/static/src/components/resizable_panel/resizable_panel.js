// @ts-check

/** @module @web/components/resizable_panel/resizable_panel - Side panel component with drag handle for interactive width resizing */

import {
    Component,
    onMounted,
    onWillUnmount,
    onWillUpdateProps,
    useComponent,
    useEffect,
    useExternalListener,
    useRef,
} from "@odoo/owl";

/**
 * @typedef {"start" | "end"} ResizeSide
 *
 * @typedef {Object} UseResizableParams
 * @property {string | import("@odoo/owl").Ref<HTMLElement>} containerRef - Ref name or ref object for the resizable container
 * @property {string | import("@odoo/owl").Ref<HTMLElement>} handleRef - Ref name or ref object for the drag handle
 * @property {number} [initialWidth=400] - Starting width in pixels
 * @property {(props: Object) => number} [getMinWidth] - Returns minimum width from current props
 * @property {(width: number) => void} [onResize] - Callback invoked after each resize with the new width
 * @property {(props: Object) => ResizeSide} [getResizeSide] - Returns which side the handle is on from current props
 */

/**
 * OWL composable hook that makes a container element resizable via a drag handle.
 * Handles mouse interactions, respects RTL/LTR direction, and clamps width
 * between a minimum and the available parent width.
 *
 * @param {UseResizableParams} params
 */
function useResizable({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth = (_props) => 400,
    onResize = (_width) => {},
    getResizeSide = (_props) => "end",
}) {
    containerRef =
        typeof containerRef == "string" ? useRef(containerRef) : containerRef;
    handleRef = typeof handleRef == "string" ? useRef(handleRef) : handleRef;
    const props = useComponent().props;

    let minWidth = getMinWidth(props);
    let resizeSide = getResizeSide(props);
    let isChangingSize = false;

    useExternalListener(document, "mouseup", () => onMouseUp());
    useExternalListener(document, "mousemove", (ev) => onMouseMove(ev));

    useExternalListener(window, "resize", () => {
        const limit = getLimitWidth();
        if (getContainerRect().width >= limit) {
            resize(computeFinalWidth(limit));
        }
    });

    let docDirection;
    useEffect(
        (container) => {
            if (container) {
                docDirection = getComputedStyle(container).direction;
            }
        },
        () => [containerRef.el],
    );

    onMounted(() => {
        if (handleRef.el) {
            resize(initialWidth);
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

    /** Begin drag — disable pointer events and text selection on body. */
    function onMouseDown() {
        isChangingSize = true;
        document.body.classList.add("pe-none", "user-select-none");
    }

    /** End drag — restore pointer events and text selection on body. */
    function onMouseUp() {
        isChangingSize = false;
        document.body.classList.remove("pe-none", "user-select-none");
    }

    /**
     * Handle drag movement — compute new width from cursor position,
     * accounting for RTL/LTR direction and resize side.
     *
     * @param {MouseEvent} ev
     */
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

    /**
     * Clamp target width between minimum width and available parent space,
     * accounting for handle spacing.
     *
     * @param {number} targetContainerWidth - desired container width in pixels
     * @returns {number} clamped width in pixels
     */
    function computeFinalWidth(targetContainerWidth) {
        const handlerSpacing = handleRef.el ? handleRef.el.offsetWidth / 2 : 10;
        const w = Math.max(minWidth, targetContainerWidth + handlerSpacing);
        const limit = getLimitWidth();
        return Math.min(w, limit - handlerSpacing);
    }

    /**
     * Get the container's positional rect, using offset-based values when
     * an offsetParent exists (more stable during drag), falling back to
     * getBoundingClientRect otherwise.
     *
     * @returns {{ left: number, right: number, width: number }}
     */
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

    /**
     * Get the maximum available width from the offset parent, or the window.
     *
     * @returns {number} maximum width in pixels
     */
    function getLimitWidth() {
        const offsetParent = containerRef.el.offsetParent;
        return offsetParent ? offsetParent.offsetWidth : window.innerWidth;
    }

    /**
     * Apply the given width to the container element and notify via callback.
     *
     * @param {number} width - new width in pixels
     */
    function resize(width) {
        containerRef.el.style.setProperty("width", `${width}px`);
        onResize(width);
    }
}

/**
 * Side panel OWL component with a drag handle for interactive width resizing.
 * Wraps the `useResizable` hook with declarative props.
 */
export class ResizablePanel extends Component {
    static template = "web_studio.ResizablePanel";

    static components = {};
    static props = {
        onResize: { type: Function, optional: true },
        initialWidth: { type: Number, optional: true },
        minWidth: { type: Number, optional: true },
        class: { type: String, optional: true },
        slots: { type: Object },
        handleSide: {
            validate: (val) => ["start", "end"].includes(val),
            optional: true,
        },
    };
    static defaultProps = {
        onResize: () => {},
        width: 400,
        minWidth: 400,
        class: "",
        handleSide: "end",
    };

    /** Wire up the resizable hook with prop-driven configuration. */
    setup() {
        useResizable({
            containerRef: "containerRef",
            handleRef: "handleRef",
            onResize: this.props.onResize,
            initialWidth: this.props.initialWidth,
            getMinWidth: (props) => props.minWidth,
            getResizeSide: (props) => props.handleSide,
        });
    }

    /**
     * Compute CSS classes, adding `position-relative` if no position class is present.
     *
     * @returns {string} space-separated class string
     */
    get class() {
        const classes = this.props.class.split(" ");
        if (!classes.some((cls) => cls.startsWith("position-"))) {
            classes.push("position-relative");
        }
        return classes.join(" ");
    }
}
