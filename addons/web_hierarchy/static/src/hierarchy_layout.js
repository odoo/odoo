/**
 * Layout of the hierarchy graph.
 *
 * The nodes are laid out from top to bottom (or from left to right): a node is
 * placed in the level following the one of its parent, centered on its
 * children. Each connected component (i.e. a tree) is laid out independently,
 * then the components are packed so that unrelated records do not end up in a
 * single endless line.
 *
 * All the coordinates are expressed in the graph space and designate the
 * center of the nodes.
 */

export const DEFAULT_NODE_SIZE = { width: 250, height: 130 };

// the algorithm works from left to right: "column" is a level of the tree, the
// vertical layout is obtained by transposing the horizontal one
const COLUMN_GAP = 80;
const NODE_GAP = 40;
const COMPONENT_GAP = 100;
// aspect ratio (width / height) of the screen targeted when packing the components
const TARGET_RATIO = 16 / 9;
// a row can be that much wider than the widest component
const WIDEST_COMPONENT_RATIO = 1.5;

/**
 * @typedef {{ id: number, parentId: number | false }} HierarchyNode
 * @typedef {{ x: number, y: number }} Point
 * @typedef {{ source: number, target: number }} HierarchyEdge
 */

/**
 * @param {HierarchyNode[]} nodes nodes in display order
 * @param {(id: number) => { width: number, height: number }} getSize
 * @param {{ direction?: "vertical" | "horizontal" }} [options]
 * @returns {{ positions: Map<number, Point>, edges: HierarchyEdge[] }}
 */
export function computeHierarchyLayout(nodes, getSize, { direction = "vertical" } = {}) {
    if (direction === "horizontal") {
        const { components, edges } = layoutTrees(nodes, getSize);
        return { positions: packComponents(components), edges };
    }
    const transposedSize = (id) => {
        const { width, height } = getSize(id);
        return { width: height, height: width };
    };
    const { components, edges } = layoutTrees(nodes, transposedSize);
    for (const component of components) {
        for (const position of component.positions.values()) {
            [position.x, position.y] = [position.y, position.x];
        }
        [component.width, component.height] = [component.height, component.width];
    }
    return { positions: packComponents(components), edges };
}

/**
 * Lays out each tree from left to right, with its top-left corner at (0, 0).
 * @param {HierarchyNode[]} nodes
 * @param {(id: number) => { width: number, height: number }} getSize
 */
function layoutTrees(nodes, getSize) {
    const ids = new Set(nodes.map((node) => node.id));
    const children = new Map(nodes.map((node) => [node.id, []]));
    const edges = [];
    const roots = [];
    for (const { id, parentId } of nodes) {
        if (parentId && parentId !== id && ids.has(parentId)) {
            children.get(parentId).push(id);
            edges.push({ source: parentId, target: id });
        } else {
            roots.push(id);
        }
    }

    const columnWidth = Math.max(0, ...nodes.map((node) => getSize(node.id).width));
    const visited = new Set();

    /**
     * Lays out the tree under `rootId` with its top-left corner at (0, 0).
     * @param {number} rootId
     */
    const layoutTree = (rootId) => {
        const positions = new Map();
        const placed = []; // ids in placement order, to shift whole subtrees
        let maxDepth = 0;

        /**
         * Places the subtree of `id` below `top` and returns its bottom.
         * @param {number} id
         * @param {number} depth
         * @param {number} top
         */
        const place = (id, depth, top) => {
            visited.add(id);
            maxDepth = Math.max(maxDepth, depth);
            const { height } = getSize(id);
            const x = depth * (columnWidth + COLUMN_GAP) + columnWidth / 2;
            const firstDescendant = placed.length;
            const placedChildren = [];
            let cursor = top;
            for (const childId of children.get(id)) {
                // visited children only exist in case of cycle
                if (!visited.has(childId)) {
                    cursor = place(childId, depth + 1, cursor) + NODE_GAP;
                    placedChildren.push(childId);
                }
            }
            placed.push(id);
            if (!placedChildren.length) {
                positions.set(id, { x, y: top + height / 2 });
                return top + height;
            }
            let bottom = cursor - NODE_GAP;
            const firstY = positions.get(placedChildren[0]).y;
            const lastY = positions.get(placedChildren.at(-1)).y;
            let y = (firstY + lastY) / 2;
            const overflow = top - (y - height / 2);
            if (overflow > 0) {
                // the node is taller than the span of its children: move
                // them down so that the node does not overlap its upper sibling
                for (const descendantId of placed.slice(firstDescendant, -1)) {
                    positions.get(descendantId).y += overflow;
                }
                y += overflow;
                bottom += overflow;
            }
            positions.set(id, { x, y });
            return Math.max(bottom, y + height / 2);
        };

        const height = place(rootId, 0, 0);
        const width = (maxDepth + 1) * columnWidth + maxDepth * COLUMN_GAP;
        return { positions, width, height };
    };

    const components = roots.map(layoutTree);
    // remaining nodes belong to cycles without root: break them arbitrarily
    for (const { id } of nodes) {
        if (!visited.has(id)) {
            components.push(layoutTree(id));
        }
    }

    return { components, edges };
}

/**
 * Packs the components in rows (aligned on their top), so that the whole graph
 * roughly has the aspect ratio of a screen. The largest trees come first, and
 * a few small components may be placed next to the widest one.
 * @param {{ positions: Map<number, Point>, width: number, height: number }[]} components
 * @returns {Map<number, Point>}
 */
function packComponents(components) {
    components = components.toSorted((a, b) => b.positions.size - a.positions.size);
    const area = components.reduce((sum, c) => sum + c.width * c.height, 0);
    const maxRowWidth = Math.max(
        WIDEST_COMPONENT_RATIO * Math.max(...components.map((c) => c.width)),
        Math.sqrt(area * TARGET_RATIO)
    );
    const positions = new Map();
    let rowX = 0;
    let rowY = 0;
    let rowHeight = 0;
    for (const component of components) {
        if (rowX > 0 && rowX + component.width > maxRowWidth) {
            rowX = 0;
            rowY += rowHeight + COMPONENT_GAP;
            rowHeight = 0;
        }
        for (const [id, { x, y }] of component.positions) {
            positions.set(id, { x: x + rowX, y: y + rowY });
        }
        rowX += component.width + COMPONENT_GAP;
        rowHeight = Math.max(rowHeight, component.height);
    }
    return positions;
}
