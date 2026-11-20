/**
 * @typedef {{ id: number, parentId: number | false }} HierarchyNode
 * @typedef {{ source: number, target: number }} HierarchyEdge
 */

/**
 * @typedef {Object} TreeLayoutContext
 * @property {Map<number, number[]>} children ids of the children of each node, without cycle
 * @property {(id: number) => { width: number, height: number }} getNodeSize
 * @property {number} rowHeight height of a level of the tree (the tallest node)
 * @property {number} nodeGap gap between two sibling subtrees, and between two levels
 * @property {Map<number, { x: number, y: number }>} nodePositions top-left corner of the nodes already placed,
 *   filled by this function
 * @property {number[]} placed ids in placement order (post-order): the descendants of a node are contiguous,
 *   which allows to shift a whole subtree
 */

/**
 * Places the node `id` and its whole subtree in the space starting at (x, y). The children are laid out side by
 * side, from left to right, on the next level. The node is then centered over them (from the left edge of its
 * first child to the right edge of its last one). If the node is wider than its children and would overflow on
 * the left of its space, its whole subtree is shifted to the right.
 *
 * @param {number} id
 * @param {{ x: number, y: number }} position top-left corner of the space allocated to the subtree
 *   (x: left bound, y: top of the node's level)
 * @param {TreeLayoutContext} tree
 * @returns {{ cursor: number, bottom: number }} `cursor`: the x where the next sibling subtree can start
 *   (right edge of this subtree + nodeGap); `bottom`: the bottom of this subtree
 */
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

/**
 * Lays out a single tree, independently of the others, with its top-left corner at (0, 0).
 *
 * @param {number} rootId
 * @param {Map<number, number[]>} children ids of the children of each node, without cycle
 * @param {(id: number) => { width: number, height: number }} getNodeSize
 * @param {number} rowHeight height of a level of the tree (the tallest node of the whole graph, so that the
 *   levels are aligned across the trees)
 * @param {number} nodeGap gap between two sibling subtrees, and between two levels
 * @returns {{ nodePositions: Map<number, { x: number, y: number }>, width: number, height: number }}
 *   the top-left corner of each node of the tree (relative to the tree), and
 *   the size of the bounding box of the tree
 */
function placeTree(rootId, children, getNodeSize, rowHeight, nodeGap) {
    const tree = { children, getNodeSize, rowHeight, nodeGap, nodePositions: new Map(), placed: [] };
    const { cursor, bottom } = placeNode(rootId, { x: 0, y: 0 }, tree);
    return { nodePositions: tree.nodePositions, width: cursor - nodeGap, height: bottom };
}

/**
 * Lays out all the trees of the forest. Each tree is laid out independently, then the trees are packed in rows
 * (aligned on their top), so that the whole graph roughly has the aspect ratio `targetRatio`. The largest trees
 * (in number of nodes) come first, at the top left.
 *
 * @param {number[]} roots ids of the root of each tree, in display order (used to order trees of the same size)
 * @param {Map<number, number[]>} children ids of the children of each node, without cycle
 * @param {(id: number) => { width: number, height: number }} getNodeSize
 * @param {number} targetRatio aspect ratio (width / height) the packed graph should roughly have, typically the
 *   one of the editor
 * @param {{ treeGap: number, nodeGap: number }} gaps `treeGap` (default 100): gap between two trees (horizontally
 *   and between two rows); `nodeGap` (default 40): gap between two sibling subtrees and between two levels of a tree
 * @returns {Map<number, { x: number, y: number }>} top-left corner of each node, in the graph space
 */
export function placeForest(roots, children, getNodeSize, targetRatio, { treeGap = 100, nodeGap = 40 } = {}) {
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

/**
 * Builds the structure of the graph from the parent of each node, regardless of the size or position of the nodes:
 * the forest of trees to lay out.
 *
 * A node is a root when it has no parent, is its own parent, or when its parent is not displayed. The nodes of a cycle
 * without root (e.g. A parent of B, B parent of A) are not reachable from any root: each such cycle is broken by
 * taking its first node (in display order) as an additional root.
 *
 * @param {HierarchyNode[]} nodes displayed nodes, in display order
 * @returns {{
 *   roots: number[],
 *   children: Map<number, number[]>,
 *   edges: HierarchyEdge[],
 * }}
 *   - `roots`: the root of each tree: first the true roots in display order, then the roots chosen to break the cycles;
 *   - `children`: the children of each node, in display order, without the link closing a cycle, so that the placement
 *     only sees true trees;
 *   - `edges`: one edge from each node to each of its displayed children, including the ones closing a cycle (to
 *     display the loop)
 */
export function buildStructure(nodes) {
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

    // Traverses each tree starting from its root. A child that has already been
    // processed can only come from a cycle: it is removed from `children` so
    // that the placement process sees only valid trees.
    const reached = new Set();
    const visit = (id) => {
        reached.add(id);
        const kept = [];
        for (const childId of children.get(id)) {
            if (!reached.has(childId)) {
                kept.push(childId);
                visit(childId);
            }
        }
        children.set(id, kept);
    };
    roots.forEach(visit);

    // Nodes that have not been reached belong to cycles without a root: we break
    // each cycle by taking its first node (in display order) as the root.
    for (const { id } of nodes) {
        if (!reached.has(id)) {
            roots.push(id);
            visit(id);
        }
    }

    return { roots, children, edges };
}
