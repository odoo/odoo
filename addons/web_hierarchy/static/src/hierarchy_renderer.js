import {
    Component,
    computed,
    onMounted,
    onPatched,
    proxy,
    signal,
    t,
    useEffect,
    useOnChange,
    useProps,
} from "@odoo/owl";

import { HierarchyCard } from "./hierarchy_card";
import { computeHierarchyLayout, DEFAULT_NODE_SIZE } from "./hierarchy_layout";

const MIN_SCALE = 0.25;
const MAX_SCALE = 2;
const FIT_MARGIN = 48;
// minimum scale when opening the view, for the cards to remain readable
const INITIAL_MIN_SCALE = 0.7;
// distance (px) from which a pointer move on a card is a drag, not a click
const DRAG_THRESHOLD = 4;

/**
 * Renders the records as a graph: each record is a node, and a record whose
 * parent is also displayed is linked to it. The graph can be panned (drag,
 * wheel, arrows) and zoomed (ctrl + wheel, +/-, controls).
 */
export class HierarchyRenderer extends Component {
    static template = "web_hierarchy.HierarchyRenderer";
    static components = { HierarchyCard };

    props = useProps({
        model: t.object(),
        list: t.any(),
        openRecord: t.function(),
        archInfo: t.object(),
    });

    editor = signal.ref();
    /** measured size of the nodes, by record id */
    nodeSizes = signal({});
    /** whether the click following a drag of a card must be ignored */
    preventNextClick = false;
    /** positions of the nodes moved by the user (graph space), by record id */
    movedPositions = signal({});
    state = proxy({
        origin: { x: 0, y: 0 },
        scale: 1,
        dragging: false,
        draggedId: null,
        ready: false,
    });

    /** computed positions of the nodes, independent of the user moves */
    layout = computed(() => {
        const { parentFieldName } = this.props.archInfo;
        const nodes = (this.props.list?.records || []).map((record) => ({
            id: record.resId,
            parentId: record.data[parentFieldName]?.id || false,
        }));
        return computeHierarchyLayout(nodes, (id) => this.getNodeSize(id));
    });

    graph = computed(() => {
        const { parentFieldName, childFieldName } = this.props.archInfo;
        const records = this.props.list?.records || [];
        const ids = new Set(records.map((record) => record.resId));
        const { positions, edges } = this.layout();
        const movedPositions = this.movedPositions();
        const getPosition = (id) => movedPositions[id] || positions.get(id);
        return {
            nodes: records.map((record) => {
                const parentId = record.data[parentFieldName]?.id || false;
                const childIds = record.data[childFieldName]?.currentIds || [];
                return {
                    record,
                    position: getPosition(record.resId),
                    hasHiddenParent: Boolean(parentId) && !ids.has(parentId),
                    hasHiddenChildren: childIds.some((id) => !ids.has(id)),
                };
            }),
            // from the bottom of the parent to the top of the child
            edges: edges.map(({ source, target }) => {
                const sourcePosition = getPosition(source);
                const targetPosition = getPosition(target);
                return {
                    key: `${source}_${target}`,
                    source: {
                        x: sourcePosition.x,
                        y: sourcePosition.y + this.getNodeSize(source).height / 2,
                    },
                    target: {
                        x: targetPosition.x,
                        y: targetPosition.y - this.getNodeSize(target).height / 2,
                    },
                };
            }),
        };
    });

    displayedIds = computed(() =>
        (this.props.list?.records || []).map((record) => record.resId).join(",")
    );

    setup() {
        // refit the graph when other records are displayed (search, pager...)
        useOnChange(
            () => [this.displayedIds()],
            () => {
                this.state.ready = false;
                this.movedPositions.set({});
            },
            { initialRun: false }
        );
        useEffect(() => {
            const editor = this.editor();
            if (!editor) {
                return;
            }
            const onPointerDown = (ev) => {
                this.preventNextClick = false;
                this.startPanning(ev);
            };
            const onWheel = (ev) => this.onWheel(ev);
            const onKeyDown = (ev) => this.onKeyDown(ev);
            // a drag of a card must not be considered as a click on it
            const onClick = (ev) => {
                if (this.preventNextClick) {
                    ev.stopPropagation();
                    ev.preventDefault();
                }
            };
            editor.addEventListener("click", onClick, { capture: true });
            // capture: also reset the click prevention before a drag of a card
            editor.addEventListener("pointerdown", onPointerDown, { capture: true });
            editor.addEventListener("wheel", onWheel, { passive: false });
            document.addEventListener("keydown", onKeyDown);
            return () => {
                editor.removeEventListener("click", onClick, { capture: true });
                editor.removeEventListener("pointerdown", onPointerDown, { capture: true });
                editor.removeEventListener("wheel", onWheel);
                document.removeEventListener("keydown", onKeyDown);
            };
        });
        onMounted(() => this.afterRender());
        onPatched(() => this.afterRender());
    }

    /**
     * The layout depends on the size of the nodes, which is only known once
     * they are rendered: measure them (the graph is then rendered again with
     * the right layout), and fit the graph on the first rendering of records.
     */
    afterRender() {
        this.measureNodes();
        if (!this.state.ready) {
            this.fitGraphToView({ minScale: INITIAL_MIN_SCALE });
            this.state.ready = true;
        }
    }

    measureNodes() {
        const editor = this.editor();
        if (!editor) {
            return;
        }
        const sizes = {};
        for (const el of editor.querySelectorAll(".o_hierarchy_node_container")) {
            sizes[el.dataset.id] = { width: el.offsetWidth, height: el.offsetHeight };
        }
        const previousSizes = this.nodeSizes();
        const changed =
            Object.keys(sizes).length !== Object.keys(previousSizes).length ||
            Object.entries(sizes).some(
                ([id, { width, height }]) =>
                    previousSizes[id]?.width !== width || previousSizes[id]?.height !== height
            );
        if (changed) {
            this.nodeSizes.set(sizes);
        }
    }

    /**
     * @param {number} id
     * @returns {{ width: number, height: number }}
     */
    getNodeSize(id) {
        return this.nodeSizes()[id] || DEFAULT_NODE_SIZE;
    }

    // -------------------------------------------------------------------------
    // Coordinates
    // -------------------------------------------------------------------------

    /**
     * Converts a point of the graph space to the screen (editor) space.
     * @param {{ x: number, y: number }} point
     */
    transform({ x, y }) {
        const { scale, origin } = this.state;
        return { x: scale * x + origin.x, y: scale * y + origin.y };
    }

    /**
     * Converts a point of the screen (editor) space to the graph space.
     * @param {number} x
     * @param {number} y
     */
    untransform(x, y) {
        const { scale, origin } = this.state;
        return { x: (x - origin.x) / scale, y: (y - origin.y) / scale };
    }

    /**
     * @param {{ x: number, y: number }} position center of the node, in the graph space
     */
    getNodeStyle(position) {
        const { x, y } = this.transform(position);
        return `transform: translate(${x}px, ${y}px) scale(${this.state.scale}) translate(-50%, -50%)`;
    }

    /**
     * @param {{ source: { x: number, y: number }, target: { x: number, y: number } }} edge
     */
    getEdgePath({ source, target }) {
        const a = this.transform(source);
        const b = this.transform(target);
        const midY = (a.y + b.y) / 2;
        return `M ${a.x} ${a.y} C ${a.x} ${midY}, ${b.x} ${midY}, ${b.x} ${b.y}`;
    }

    get editorStyle() {
        const { ready, scale, origin, dragging } = this.state;
        return [
            // hide the graph until it is fitted to the view, without hiding it
            // from the accessibility tree
            `--o-hierarchy-opacity: ${ready ? 1 : 0}`,
            `background-size: ${20 * scale}px ${20 * scale}px`,
            `background-position: ${origin.x}px ${origin.y}px`,
            `cursor: ${dragging ? "grabbing" : "grab"}`,
        ].join("; ");
    }

    // -------------------------------------------------------------------------
    // Move nodes
    // -------------------------------------------------------------------------

    /**
     * Moves the node of the record `id` with the pointer. Without move, the
     * pointer events are left to the card (click to open the record).
     * @param {PointerEvent} ev
     * @param {number} id
     */
    startNodeDrag(ev, id) {
        if (ev.button !== 0 || ev.target.closest("button, a, input, select, textarea")) {
            return;
        }
        // prevent the native drag and drop of the images of the card
        ev.preventDefault();
        const editor = this.editor();
        const startX = ev.clientX;
        const startY = ev.clientY;
        const { x, y } = this.graph().nodes.find((node) => node.record.resId === id).position;
        let moved = false;
        const onPointerMove = (moveEv) => {
            const dx = moveEv.clientX - startX;
            const dy = moveEv.clientY - startY;
            if (!moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) {
                return;
            }
            moved = true;
            this.state.draggedId = id;
            const { scale } = this.state;
            this.movedPositions.set({
                ...this.movedPositions(),
                [id]: { x: x + dx / scale, y: y + dy / scale },
            });
        };
        const stopDrag = () => {
            editor.removeEventListener("pointermove", onPointerMove);
            editor.removeEventListener("pointerup", stopDrag);
            editor.removeEventListener("pointerleave", stopDrag);
            editor.removeEventListener("pointercancel", stopDrag);
            this.state.draggedId = null;
            // the click possibly dispatched after the pointerup ends the drag
            this.preventNextClick = moved;
        };
        editor.addEventListener("pointermove", onPointerMove);
        editor.addEventListener("pointerup", stopDrag);
        editor.addEventListener("pointerleave", stopDrag);
        editor.addEventListener("pointercancel", stopDrag);
    }

    // -------------------------------------------------------------------------
    // Pan & zoom
    // -------------------------------------------------------------------------

    /**
     * @param {PointerEvent} ev
     */
    startPanning(ev) {
        if (ev.button !== 0 || ev.target.closest(".o_hierarchy_node_container, .o_hierarchy_controls")) {
            return;
        }
        const editor = this.editor();
        const startX = ev.clientX - this.state.origin.x;
        const startY = ev.clientY - this.state.origin.y;
        this.state.dragging = true;
        const onPointerMove = (moveEv) => {
            this.state.origin.x = moveEv.clientX - startX;
            this.state.origin.y = moveEv.clientY - startY;
        };
        const stopPanning = () => {
            this.state.dragging = false;
            editor.removeEventListener("pointermove", onPointerMove);
            editor.removeEventListener("pointerup", stopPanning);
            editor.removeEventListener("pointerleave", stopPanning);
        };
        editor.addEventListener("pointermove", onPointerMove);
        editor.addEventListener("pointerup", stopPanning);
        editor.addEventListener("pointerleave", stopPanning);
    }

    /**
     * @param {WheelEvent} ev
     */
    onWheel(ev) {
        ev.preventDefault();
        if (ev.ctrlKey) {
            const bounds = this.editor().getBoundingClientRect();
            const scale = (1 - 0.002 * ev.deltaY) * this.state.scale;
            this.zoomAt(ev.clientX - bounds.left, ev.clientY - bounds.top, scale);
        } else {
            this.state.origin.x -= ev.deltaX;
            this.state.origin.y -= ev.deltaY;
        }
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeyDown(ev) {
        const editor = this.editor();
        // only react when nothing else has the focus (e.g. the search input)
        if (!editor || !ev.target.contains(editor)) {
            return;
        }
        const speed = 20;
        switch (ev.key) {
            case "ArrowRight":
                this.state.origin.x -= speed;
                break;
            case "ArrowLeft":
                this.state.origin.x += speed;
                break;
            case "ArrowDown":
                this.state.origin.y -= speed;
                break;
            case "ArrowUp":
                this.state.origin.y += speed;
                break;
            case "+":
                this.zoomIn();
                break;
            case "-":
                this.zoomOut();
                break;
            case " ":
                this.fitGraphToView();
                break;
            default:
                return;
        }
        ev.preventDefault();
    }

    /**
     * Zooms keeping the point (x, y) of the screen (editor) space fixed.
     * @param {number} x
     * @param {number} y
     * @param {number} scale
     */
    zoomAt(x, y, scale) {
        scale = Math.max(MIN_SCALE, Math.min(scale, MAX_SCALE));
        const ratio = 1 - scale / this.state.scale;
        this.state.origin.x += (x - this.state.origin.x) * ratio;
        this.state.origin.y += (y - this.state.origin.y) * ratio;
        this.state.scale = scale;
    }

    /**
     * @param {number} scale
     */
    zoom(scale) {
        const editor = this.editor();
        this.zoomAt(editor.offsetWidth / 2, editor.offsetHeight / 2, scale);
    }

    zoomIn() {
        this.zoom(this.state.scale + 0.1);
    }

    zoomOut() {
        this.zoom(this.state.scale - 0.1);
    }

    /**
     * Frames the whole graph, centered in the editor, without zooming in nor
     * zooming out below `minScale`. A graph too large to fit is displayed from
     * its top, centered on the root of its largest tree.
     * @param {{ minScale?: number }} [options]
     */
    fitGraphToView({ minScale = MIN_SCALE } = {}) {
        const editor = this.editor();
        const { nodes } = this.graph();
        if (!editor || !nodes.length) {
            return;
        }
        let minX = Infinity;
        let minY = Infinity;
        let maxX = -Infinity;
        let maxY = -Infinity;
        for (const { record, position } of nodes) {
            const { width, height } = this.getNodeSize(record.resId);
            minX = Math.min(minX, position.x - width / 2);
            minY = Math.min(minY, position.y - height / 2);
            maxX = Math.max(maxX, position.x + width / 2);
            maxY = Math.max(maxY, position.y + height / 2);
        }
        const width = maxX - minX;
        const height = maxY - minY;
        const scale = Math.max(
            minScale,
            Math.min(
                1,
                (editor.offsetWidth - 2 * FIT_MARGIN) / width,
                (editor.offsetHeight - 2 * FIT_MARGIN) / height
            )
        );
        this.state.scale = scale;
        if (scale * width <= editor.offsetWidth - 2 * FIT_MARGIN) {
            this.state.origin.x = (editor.offsetWidth - scale * width) / 2 - minX * scale;
        } else {
            // the root of the largest tree, which is laid out first (top left)
            const anchor = nodes
                .map((node) => node.position)
                .reduce((a, b) => (b.y < a.y || (b.y === a.y && b.x < a.x) ? b : a));
            this.state.origin.x = editor.offsetWidth / 2 - anchor.x * scale;
        }
        this.state.origin.y = Math.max(FIT_MARGIN, (editor.offsetHeight - scale * height) / 2) - minY * scale;
    }
}
