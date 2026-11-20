import {
    Component,
    computed,
    onWillDestroy,
    signal,
    t,
    useEffect,
    useOnChange,
    useProps,
    useListener,
} from "@odoo/owl";

import { HierarchyCard } from "./hierarchy_card";
import { buildStructure, placeForest } from "./hierarchy_graph_layout";

const DRAG_THRESHOLD = 4;
const INITIAL_MIN_SCALE = 0.7;
const MIN_SCALE = 0.25;
const MAX_SCALE = 2;
const FIT_MARGIN = 48;
const ZOOM_SPEED = 1.2;
const PAN_SPEED = 20;
const GRID_SIZE = 20;
const WHEEL_ZOOM_SENSITIVITY = 0.002;

/**
 * @typedef {Object} HierarchyGraphNode
 * @property {Object} record
 * @property {boolean} hasHiddenParent whether the parent of the record exists but is not displayed
 * @property {boolean} hasHiddenChildren whether some children of the record are not displayed
 */

/**
 * @typedef {Object} HierarchyGraphLayout
 * @property {() => boolean} allNodesMeasured (computed) whether all the displayed nodes have
 *   been measured, i.e. whether the layout uses their real size
 * @property {() => HierarchyGraphNode[]} nodes (computed) the displayed nodes, without their
 *   position: stable while a node is moved
 * @property {() => { key: string, source: number, target: number }[]} edges (computed) the edges
 *   between displayed nodes, without their path: stable while a node is moved
 * @property {{ add: (el: HTMLElement) => void, delete: (el: HTMLElement) => void }} nodeRefs
 *   `t-ref` to set on the container of each node (with a `data-id`), to measure it
 * @property {(id: number) => { x: number, y: number }} getNodePosition top-left corner of the
 *   node, in the graph space (the position set by the user if the node has been moved)
 * @property {() => { x: number, y: number, width: number, height: number }[]} getNodesBoundaries
 *   the box of each displayed node, in the graph space
 * @property {(edge: { source: number, target: number }) => string} getEdgePath SVG path of the
 *   edge, from the bottom center of the parent to the top center of the child
 * @property {(id: number, position: { x: number, y: number }) => void} moveNode sets the position
 *   of a node moved by the user
 */

/**
 * Lays out the displayed records as a graph: one node per record, linked to its parent.
 *
 * The layout depends on the size of the nodes, only known once they are rendered: each node
 * container is measured by a ResizeObserver (see `nodeRefs`), until then a default size is used.
 * The position of each node is tracked separately, so that moving a node only notifies the
 * readers of that node (and of its edges).
 *
 * When other records are displayed (search, pager...), the moves of the user are discarded and
 * the sizes of the nodes that are no longer displayed are forgotten.
 *
 * @param {() => Object[]} records (signal or computed) the displayed records
 * @param {string} parentFieldName
 * @param {string} childFieldName
 * @param {() => HTMLElement | null} editor (ref) the editor, whose aspect ratio is used to pack the trees of the graph
 * @returns {HierarchyGraphLayout}
 */
function useGraphLayout(records, parentFieldName, childFieldName, editor) {
    const nodeSizes = signal({});
    const movedPositions = signal.Object({});

    const resizeObserver = new ResizeObserver((entries) => {
        const previous = nodeSizes();
        let sizes;
        for (const { target, borderBoxSize: [box] } of entries) {
            const { id } = target.dataset;
            const size = previous[id];
            if (size?.width !== box.inlineSize || size?.height !== box.blockSize) {
                sizes ??= { ...previous };
                sizes[id] = { width: box.inlineSize, height: box.blockSize };
            }
        }
        if (sizes) {
            nodeSizes.set(sizes);
        }
    });

    onWillDestroy(() => resizeObserver.disconnect());

    const nodeRefs = {
        add: (el) => resizeObserver.observe(el, { box: "border-box" }),
        delete: (el) => resizeObserver.unobserve(el),
    };

    const allNodesMeasured = computed(() => {
        const sizes = nodeSizes();
        return records().every((record) => record.resId in sizes);
    });

    const structure = computed(() => {
        return buildStructure(records().map((record) => ({
            id: record.resId,
            parentId: record.data[parentFieldName]?.id || false,
        })));
    });

    const positioning = computed(() => {
        const el = editor();
        const targetRatio = el?.clientHeight ? el.clientWidth / el.clientHeight : 16 / 9;
        const { roots, children } = structure();
        return placeForest(roots, children, getNodeSize, targetRatio);
    });

    const nodes = computed(() => {
        const recordList = records();
        const ids = new Set(recordList.map((record) => record.resId));
        return recordList.map((record) => {
            const parentId = record.data[parentFieldName]?.id || false;
            const childIds = record.data[childFieldName]?.currentIds || [];
            return {
                record,
                hasHiddenParent: Boolean(parentId) && !ids.has(parentId),
                hasHiddenChildren: childIds.some((id) => !ids.has(id)),
            };
        });
    });

    const edges = computed(() =>
        structure().edges.map(({ source, target }) => ({ key: `${source}_${target}`, source, target }))
    );

    function getNodeSize(id) {
        return nodeSizes()[id] || { width: 250, height: 130 };
    }

    function getNodePosition(id) {
        return movedPositions()[id] || positioning().get(id);
    }

    function getNodeBoundaries(id) {
        return { ...getNodePosition(id), ...getNodeSize(id) };
    }

    function getNodesBoundaries() {
        return records().map((record) => getNodeBoundaries(record.resId));
    }

    function moveNode(id, position) {
        movedPositions()[id] = position;
    }

    function getEdgePath({ source, target }) {
        const sourceBox = getNodeBoundaries(source);
        const targetBox = getNodeBoundaries(target);
        const a = { x: sourceBox.x + sourceBox.width / 2, y: sourceBox.y + sourceBox.height };
        const b = { x: targetBox.x + targetBox.width / 2, y: targetBox.y };
        const midY = (a.y + b.y) / 2;
        return `M ${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
    }

    useOnChange(
        () => records().map((record) => record.resId),
        (...ids) => {
            movedPositions.set({});
            const displayed = new Set(ids.map(String));
            nodeSizes.set(Object.fromEntries(
                Object.entries(nodeSizes()).filter(([id]) => displayed.has(id))
            ));
        },
        { initialRun: false },
    );

    return {
        allNodesMeasured,
        nodes,
        edges,
        nodeRefs,
        getNodePosition,
        getNodesBoundaries,
        getEdgePath,
        moveNode,
    };

}

/**
 * @typedef {Object} HierarchyPanAndZoom
 * @property {() => number} scale (signal) the current zoom level
 * @property {(minScale?: number) => void} fitGraphToView frames the whole graph, centered in the
 *   editor, without zooming in nor zooming out below `minScale`. A graph too large to fit is
 *   displayed from its top, centered on the root of its largest tree.
 * @property {(scale: number) => void} zoom sets the zoom level, keeping the center of the editor fixed
 * @property {() => void} zoomIn
 * @property {() => void} zoomOut
 */

/**
 * Lets the user move around the graph: pan by dragging the background, the wheel or the arrow
 * keys, zoom with ctrl + wheel (or pinch), the +/- keys and the returned functions, frame the
 * whole graph with the space key.
 *
 * The camera (pan and zoom) is applied as a transform on the canvas, written directly in the DOM
 * by an effect, outside of the rendering: moving around does not re-render the graph.
 * The screen position of a point of the graph is `scale * point + origin`.
 *
 * @param {() => HTMLElement | null} editor (ref) the editor: the visible area, which receives the
 *   pointer and wheel events
 * @param {() => HTMLElement | null} canvas (ref) the element containing the nodes and edges, to
 *   which the camera is applied
 * @param {() => { x: number, y: number, width: number, height: number }[]} getNodesBoundaries
 *   the box of each displayed node in the graph space, to frame the graph
 * @returns {HierarchyPanAndZoom}
 */
function usePanAndZoom(editor, canvas, getNodesBoundaries) {
    const scale = signal(1);
    const dragging = signal(false);
    const origin = signal.Object({ x: 0, y: 0 });

    function zoomAt(x, y, targetScale) {
        targetScale = Math.max(MIN_SCALE, Math.min(targetScale, MAX_SCALE));
        const ratio = 1 - targetScale / scale();
        const o = origin();
        o.x += (x - o.x) * ratio;
        o.y += (y - o.y) * ratio;
        scale.set(targetScale);
    }

    function zoom(targetScale) {
        const el = editor();
        const x = (el?.offsetWidth || 0) / 2;
        const y = (el?.offsetHeight || 0) / 2;
        zoomAt(x, y, targetScale);
    }

    function zoomIn() {
        zoom(scale() * ZOOM_SPEED);
    }

    function zoomOut() {
        zoom(scale() / ZOOM_SPEED);
    }

    function fitGraphToView(minScale = MIN_SCALE) {
        const el = editor();
        const nodesBoundaries = getNodesBoundaries();
        if (!el || !nodesBoundaries.length) {
            return;
        }

        const { minX, minY, maxX, maxY } = nodesBoundaries.reduce((acc, node) => ({
            minX: Math.min(acc.minX, node.x),
            minY: Math.min(acc.minY, node.y),
            maxX: Math.max(acc.maxX, node.x + node.width),
            maxY: Math.max(acc.maxY, node.y + node.height),
        }), { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity });

        const width = maxX - minX;
        const height = maxY - minY;
        const scaleOnWidth = (el.offsetWidth - 2 * FIT_MARGIN) / width;
        const scaleOnHeight = (el.offsetHeight - 2 * FIT_MARGIN) / height;
        const fitScale = Math.max(minScale, Math.min(1, scaleOnWidth, scaleOnHeight));
        scale.set(fitScale);

        if (fitScale <= scaleOnWidth) {
            origin().x = (el.offsetWidth - fitScale * width) / 2 - minX * fitScale;
        } else {
            const anchor = nodesBoundaries.reduce((a, b) => a.y < b.y || (a.y === b.y && a.x < b.x) ? a : b);
            origin().x = el.offsetWidth / 2 - (anchor.x + anchor.width / 2) * fitScale;
        }
        origin().y = Math.max(FIT_MARGIN, (el.offsetHeight - fitScale * height) / 2) - minY * fitScale;
    }

    useListener(editor, "pointerdown", (ev) => {
        if (ev.button !== 0 || ev.target.closest(".o_hierarchy_node_container, .o_hierarchy_controls")) {
            return;
        }

        const el = editor();
        const { pointerId } = ev;
        const startX = ev.clientX - origin().x;
        const startY = ev.clientY - origin().y;

        dragging.set(true);
        el.setPointerCapture(pointerId);

        const onPointerMove = (moveEv) => {
            if (moveEv.pointerId === pointerId) {
                origin.set({ x: moveEv.clientX - startX, y: moveEv.clientY - startY });
            }
        };

        const stopPanning = () => {
            dragging.set(false);
            el.removeEventListener("pointermove", onPointerMove);
            el.removeEventListener("lostpointercapture", stopPanning);
        };

        el.addEventListener("pointermove", onPointerMove);
        el.addEventListener("lostpointercapture", stopPanning);
    }, { capture: true });

    useListener(editor, "wheel", (ev) => {
        ev.preventDefault();
        if (ev.ctrlKey) {
            const { left, top } = editor().getBoundingClientRect();
            zoomAt(ev.clientX - left, ev.clientY - top, Math.exp(-WHEEL_ZOOM_SENSITIVITY * ev.deltaY) * scale());
        } else {
            origin().x -= ev.deltaX;
            origin().y -= ev.deltaY;
        }
    }, { passive: false });

    useListener(document, "keydown", (ev) => {
        const el = editor();
        if (!el || !ev.target.contains(el)) {
            return;
        }

        switch (ev.key) {
            case "ArrowRight":
                origin().x -= PAN_SPEED;
                break;
            case "ArrowLeft":
                origin().x += PAN_SPEED;
                break;
            case "ArrowDown":
                origin().y -= PAN_SPEED;
                break;
            case "ArrowUp":
                origin().y += PAN_SPEED;
                break;
            case "+":
                zoomIn();
                break;
            case "-":
                zoomOut();
                break;
            case " ":
                fitGraphToView();
                break;
            default:
                return;
        }
        ev.preventDefault();
    });

    useEffect(() => {
        const elEditor = editor();
        const elCanvas = canvas();
        if (!elEditor || !elCanvas) {
            return;
        }
        elCanvas.style.transform = `translate(${origin().x}px, ${origin().y}px) scale(${scale()})`;
        elEditor.style.backgroundSize = `${GRID_SIZE * scale()}px ${GRID_SIZE * scale()}px`;
        elEditor.style.backgroundPosition = `${origin().x}px ${origin().y}px`;
        elEditor.style.cursor = dragging() ? "grabbing" : "grab";
    });

    return {
        scale,
        fitGraphToView,
        zoom,
        zoomIn,
        zoomOut,
    };
}

class HierarchyZoomController extends Component {
    static template = "web_hierarchy.HierarchyZoomController";

    props = useProps({ panAndZoom: t.object() });
}

class HierarchyNode extends Component {
    static template = "web_hierarchy.HierarchyNode";
    static components = { HierarchyCard };

    props = useProps({
        node: t.object(),
        layout: t.object(),
        scale: t.signal(t.number()),
        cardArchInfo: t.object(),
        openRecord: t.function(),
    });

    dragging = signal(false);

    id() {
        return this.props.node.record.resId;
    }

    style() {
        const { x, y } = this.props.layout.getNodePosition(this.id());
        return `transform: translate(${x}px, ${y}px)`;
    }

    onPointerDown(ev) {
        if (ev.button !== 0 || ev.target.closest("button, a, input, select, textarea")) {
            return;
        }

        ev.preventDefault();
        const el = ev.currentTarget;
        const { pointerId, clientX: startX, clientY: startY } = ev;
        const { x, y } = this.props.layout.getNodePosition(this.id());

        let moved = false;
        const onPointerMove = (moveEv) => {
            if (moveEv.pointerId !== pointerId) {
                return;
            }
            if (!(moveEv.buttons & 1)) {
                stopDrag();
                return;
            }

            const dx = moveEv.clientX - startX;
            const dy = moveEv.clientY - startY;
            if (!moved) {
                if (Math.hypot(dx, dy) < DRAG_THRESHOLD) {
                    return;
                }
                moved = true;
                el.setPointerCapture(pointerId);
                this.dragging.set(true);
            }
            const scale = this.props.scale();
            this.props.layout.moveNode(this.id(), { x: x + dx / scale, y: y + dy / scale });
        };

        const stopDrag = () => {
            el.removeEventListener("pointermove", onPointerMove);
            el.removeEventListener("pointerup", stopDrag);
            el.removeEventListener("pointercancel", stopDrag);
            el.removeEventListener("lostpointercapture", stopDrag);
            this.dragging.set(false);

            if (moved) {
                // The browser may dispatch a click when the pointer is released on the
                // element it was pressed on, even if it moved in between: dropping a
                // card would then open its record. When the card has actually been
                // moved, swallow that click before it reaches the card. The click
                // immediately follows the pointerup, while the timeout runs in a later
                // task: it removes the listener when no click came (e.g. pointer released
                // outside the card), so that the next genuine click is not swallowed.
                const swallow = (evClick) => {
                    evClick.stopPropagation();
                    evClick.preventDefault();
                };
                el.addEventListener("click", swallow, { capture: true, once: true });
                setTimeout(() => el.removeEventListener("click", swallow, { capture: true }));
            }
        };

        el.addEventListener("pointermove", onPointerMove);
        el.addEventListener("pointerup", stopDrag);
        el.addEventListener("pointercancel", stopDrag);
        el.addEventListener("lostpointercapture", stopDrag);
    }
}

class HierarchyEdge extends Component {
    static template = "web_hierarchy.HierarchyEdge";

    props = useProps({
        edge: t.object(),
        layout: t.object(),
    });
}

export class HierarchyRenderer extends Component {
    static template = "web_hierarchy.HierarchyRenderer";
    static components = { HierarchyNode, HierarchyEdge, HierarchyZoomController };

    props = useProps({
        model: t.object(),
        list: t.any(),
        openRecord: t.function(),
        archInfo: t.object(),
    });

    editor = signal.ref();
    canvas = signal.ref();

    fittedIds = signal(null);

    displayedIds = computed(() => this.records().map((record) => record.resId).join(","));
    isFitted = computed(() => this.fittedIds() === this.displayedIds());
    records = computed(() => this.props.list?.records || []);

    graphLayout = useGraphLayout(
        this.records,
        this.props.archInfo.parentFieldName,
        this.props.archInfo.childFieldName,
        this.editor
    );

    panAndZoom = usePanAndZoom(
        this.editor,
        this.canvas,
        this.graphLayout.getNodesBoundaries
    );

    setup() {
        useOnChange(
            () => [this.graphLayout.allNodesMeasured(), this.displayedIds()],
            (allNodesMeasured, displayedIds) => {
                if (allNodesMeasured) {
                    this.panAndZoom.fitGraphToView(INITIAL_MIN_SCALE);
                    this.fittedIds.set(displayedIds);
                }
            },
            { initialRun: false }
        );
    }

}
