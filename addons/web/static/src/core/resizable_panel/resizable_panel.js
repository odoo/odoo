import {
    Component,
    onMounted,
    onWillUpdateProps,
    onWillUnmount,
    useEffect,
    useExternalListener,
    useRef,
    useComponent,
} from "@odoo/owl";

function useResizable({
    containerRef,
    handleRef,
    initialWidth = 400,
    getMinWidth = () => 400,
    initialHeight = 400,
    getMinHeight = () => 400,
    onResize = () => {},
    getResizeSide = () => "end",
}) {
    containerRef = typeof containerRef == "string" ? useRef(containerRef) : containerRef;
    handleRef = typeof handleRef == "string" ? useRef(handleRef) : handleRef;
    const props = useComponent().props;

    let minWidth = getMinWidth(props);
    let minHeight = getMinHeight(props);
    /**
     * @param {Object} props
     * @returns {String} "start"|"end"|"top"|"bottom"
     */
    let resizeSide = getResizeSide(props);
    const resizeAxis = resizeSide === "start" || resizeSide === "end" ? "x" : "y";
    let isChangingSize = false;

    useExternalListener(document, "mouseup", () => onMouseUp());
    useExternalListener(document, "mousemove", (ev) => onMouseMove(ev));

    useExternalListener(window, "resize", () => {
        const limit = getLimit();
        if (
            (resizeAxis === "x" && getContainerRect().width >= limit.width) ||
            (resizeAxis === "y" && getContainerRect().height >= limit.height)
        ) {
            resize(computeFinal(limit));
        }
    });

    let docDirection;
    useEffect(
        (container) => {
            if (container) {
                docDirection = getComputedStyle(container).direction;
            }
        },
        () => [containerRef.el]
    );

    onMounted(() => {
        if (handleRef.el) {
            resize({
                width: initialWidth,
                height: initialHeight,
            });
            handleRef.el.addEventListener("mousedown", onMouseDown);
        }
    });

    onWillUpdateProps((nextProps) => {
        minWidth = getMinWidth(nextProps);
        minHeight = getMinHeight(nextProps);
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
        const newDimensions = {};
        if (resizeAxis === "x") {
            const direction =
                (docDirection === "ltr" && resizeSide === "end") ||
                (docDirection === "rtl" && resizeSide === "start")
                    ? 1
                    : -1;
            const fixedSide = direction === 1 ? "left" : "right";
            const containerRect = getContainerRect();
            newDimensions.width = (ev.clientX - containerRect[fixedSide]) * direction;
            newDimensions.height = containerRect.height;
        }
        if (resizeAxis === "y") {
            const direction = resizeSide === "bottom" ? 1 : -1;
            const fixedSide = direction === 1 ? "top" : "bottom";
            const containerRect = getContainerRect();
            newDimensions.width = containerRect.width;
            newDimensions.height = (ev.clientY - containerRect[fixedSide]) * direction;
        }
        resize(computeFinal(newDimensions));
    }

    function computeFinal({ width, height }) {
        const handlerSpacingWidth = handleRef.el ? handleRef.el.offsetWidth / 2 : 10;
        const handlerSpacingHeight = handleRef.el ? handleRef.el.offsetHeight / 2 : 10;
        const w = Math.max(minWidth, width + handlerSpacingWidth);
        const h = Math.max(minHeight, height + handlerSpacingHeight);
        const limit = getLimit();
        return {
            width: Math.min(w, limit.width - handlerSpacingWidth),
            height: Math.min(h, limit.height - handlerSpacingHeight),
        };
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
            containerRect.top = container.offsetTop;
            containerRect.bottom = container.offsetTop + container.offsetHeight;
            containerRect.height = container.offsetHeight;
        }
        return containerRect;
    }

    function getLimit() {
        const offsetParent = containerRef.el.offsetParent;
        return offsetParent
            ? {
                  width: offsetParent.offsetWidth,
                  height: offsetParent.offsetHeight,
              }
            : {
                  width: window.innerWidth,
                  height: window.innerHeight,
              };
    }

    function resize({ width, height }) {
        if (resizeAxis === "y") {
            containerRef.el.style.setProperty("height", `${height}px`);
        }
        if (resizeAxis === "x") {
            containerRef.el.style.setProperty("width", `${width}px`);
        }
        onResize({ width, height });
    }
}

export class ResizablePanel extends Component {
    static template = "web_studio.ResizablePanel";

    static components = {};
    static props = {
        onResize: { type: Function, optional: true },
        initialWidth: { type: Number, optional: true },
        minWidth: { type: Number, optional: true },
        initialHeight: { type: Number, optional: true },
        minHeight: { type: Number, optional: true },
        class: { type: String, optional: true },
        slots: { type: Object },
        handleSide: {
            validate: (val) => ["start", "end", "top", "bottom"].includes(val),
            optional: true,
        },
    };
    static defaultProps = {
        onResize: () => {},
        initialWidth: 400,
        minWidth: 400,
        initialHeight: 200,
        minHeight: 200,
        class: "",
        handleSide: "end",
    };

    setup() {
        useResizable({
            containerRef: "containerRef",
            handleRef: "handleRef",
            onResize: this.props.onResize,
            initialWidth: this.props.initialWidth,
            initialHeight: this.props.initialHeight,
            getMinWidth: (props) => props.minWidth,
            getMinHeight: (props) => props.minHeight,
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
