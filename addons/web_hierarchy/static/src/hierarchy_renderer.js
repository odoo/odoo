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

const DRAG_THRESHOLD = 4;
const INITIAL_MIN_SCALE = 0.7;
const MIN_SCALE = 0.25;
const MAX_SCALE = 2;
const FIT_MARGIN = 48;
const ZOOM_SPEED = 1.2;
const PAN_SPEED = 20;
const GRID_SIZE = 20;
const WHEEL_ZOOM_SENSITIVITY = 0.002;

function useGraphLayout(list, parentFieldName, childFieldName, editor) {
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

    const records = computed(() => list()?.records || []);

    const allNodesMeasured = computed(() => {
        const sizes = nodeSizes();
        return records().every((record) => record.resId in sizes);
    });

    const structure = computed(() => {
        const children = new Map(records().map((record) => [record.resId, []]));
        const edges = [];
        let roots = [];
        for (const [parentId, ids] of list()?.children ?? []) {
            if (parentId) {
                children.set(parentId, ids);
                edges.push(...ids.map((id) => ({ source: parentId, target: id })));
            } else {
                roots = ids;
            }
        }
        return { roots, children, edges };
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

    function placeNode(id, { x, y }, tree) {
        const { children, getNodeSize, rowHeight, nodeGap, nodePositions, placed } = tree;
        const nodeSize = getNodeSize(id);
        const firstDescendant = placed.length;
        const childIds = children.get(id);

        let childBottom;
        let cursor = x;
        let bottom = y + rowHeight;
        for (const childId of childIds) {
            ({ cursor, bottom: childBottom } = placeNode(childId, { x: cursor, y: y + rowHeight + nodeGap }, tree));
            bottom = Math.max(bottom, childBottom);
        }

        let left = x;
        if (childIds.length) {
            const first = childIds[0];
            const last = childIds.at(-1);
            const startX = nodePositions.get(first).x;
            const endX = nodePositions.get(last).x + getNodeSize(last).width;
            left = (startX + endX - nodeSize.width) / 2;
        }

        const overflow = x - left;
        if (overflow > 0) {
            for (let index = firstDescendant; index < placed.length; index++) {
                nodePositions.get(placed[index]).x += overflow;
            }
            left += overflow;
            cursor += overflow;
        }

        placed.push(id);
        nodePositions.set(id, { x: left, y: y + (rowHeight - nodeSize.height) / 2 });
        return { cursor: Math.max(cursor, left + nodeSize.width + nodeGap), bottom };
    }

    function placeTree(rootId, children, getNodeSize, rowHeight, nodeGap) {
        const tree = { children, getNodeSize, rowHeight, nodeGap, nodePositions: new Map(), placed: [] };
        const { cursor, bottom } = placeNode(rootId, { x: 0, y: 0 }, tree);
        return { nodePositions: tree.nodePositions, width: cursor - nodeGap, height: bottom };
    }

    function placeForest(roots, children, getNodeSize, targetRatio, { treeGap = 100, nodeGap = 40 } = {}) {
        const rowHeight = Math.max(0, ...children.keys().map((id) => getNodeSize(id).height));
        const trees = roots.map((rootId) => placeTree(rootId, children, getNodeSize, rowHeight, nodeGap));

        trees.sort((a, b) => b.nodePositions.size - a.nodePositions.size);
        const totalArea = trees.reduce((sum, tree) => sum + tree.width * tree.height, 0);
        const maxRowWidth = Math.max(...trees.map((tree) => tree.width), Math.sqrt(totalArea * targetRatio));

        const positions = new Map();
        const offset = { x: 0, y: 0 };
        let treeRowHeight = 0;
        for (const tree of trees) {
            if (offset.x > 0 && offset.x + tree.width > maxRowWidth) {
                offset.x = 0;
                offset.y += treeRowHeight + treeGap;
                treeRowHeight = 0;
            }
            for (const [id, { x, y }] of tree.nodePositions) {
                positions.set(id, { x: x + offset.x, y: y + offset.y });
            }
            offset.x += tree.width + treeGap;
            treeRowHeight = Math.max(treeRowHeight, tree.height);
        }

        return positions;
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
        records,
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

        const stopDrag = (endEv) => {
            if (endEv?.pointerId !== undefined && endEv.pointerId !== pointerId) {
                return;
            }
            window.removeEventListener("pointermove", onPointerMove);
            window.removeEventListener("pointerup", stopDrag);
            window.removeEventListener("pointercancel", stopDrag);
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

        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", stopDrag);
        window.addEventListener("pointercancel", stopDrag);
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

    graphLayout = useGraphLayout(
        () => this.props.list,
        this.props.archInfo.parentFieldName,
        this.props.archInfo.childFieldName,
        this.editor
    );

    panAndZoom = usePanAndZoom(
        this.editor,
        this.canvas,
        this.graphLayout.getNodesBoundaries
    );

    displayedIds = computed(() => this.graphLayout.records().map((record) => record.resId).join(","));
    isFitted = computed(() => this.fittedIds() === this.displayedIds());

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
