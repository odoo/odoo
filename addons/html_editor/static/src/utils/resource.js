//number
export const resourceSequenceObject = Symbol("resourceSequenceObject");
export const sequenceNumber = Symbol("resourceSequenceNumber");
export const sequenceId = Symbol("resourceSequenceId");
export const sequenceBefore = Symbol("resourceSequenceBefore");
export const sequenceAfter = Symbol("resourceSequenceAfter");

export function withSequence(seqObj, object) {
    if (typeof seqObj === "number") {
        seqObj = {
            sequenceNumber: seqObj,
        };
    }
    return {
        [resourceSequenceObject]: seqObj,
        object,
    };
}

export function sortListWithSequence(list) {
    const idMap = new Map();

    // 1. Normalize all items and prepare the graph nodes.
    const nodes = list.map((item, index) => {
        const isSequenceObject =
            typeof item === "object" && item !== null && item[resourceSequenceObject];
        const object = isSequenceObject ? item.object : item;
        const seqObj = isSequenceObject ? item[resourceSequenceObject] : {};

        const getValue = (symbol, key) => seqObj[key] || object?.[symbol] || object?.[key];

        const node = {
            object: object,

            originalIndex: index,
            sequenceNumber: getValue(sequenceNumber, "sequenceNumber") ?? 10,
            sequenceBefore: getValue(sequenceBefore, "sequenceBefore"),
            sequenceAfter: getValue(sequenceAfter, "sequenceAfter"),

            childrenBefore: [], // Nodes that must come before this one
            childrenAfter: [], // Nodes that must come after this one
        };

        const id = getValue(sequenceId, "id");
        if (id) {
            idMap.set(id, node);
        }

        return node;
    });

    // 2. Build the graph by linking nodes and identifying the roots.
    const roots = [];
    for (const node of nodes) {
        const { sequenceBefore, sequenceAfter } = node;
        if (sequenceBefore) {
            idMap.get(sequenceBefore).childrenBefore.push(node);
        } else if (sequenceAfter) {
            idMap.get(sequenceAfter).childrenAfter.push(node);
        }
        if (!sequenceAfter && !sequenceBefore) {
            roots.push(node);
        }
    }

    // 3. Sort the root nodes to establish the main order.
    roots.sort(
        (a, b) =>
            a.sequenceNumber - b.sequenceNumber ||
            // Maintain original order for nodes with the same sequence number
            a.originalIndex - b.originalIndex
    );

    // 4. Traverse the graph from the roots to build the final sorted list.
    const result = [];
    const visited = new Set();
    const visit = (node) => {
        if (!node || visited.has(node)) {
            return;
        }
        visited.add(node);
        node.childrenBefore.forEach(visit);
        result.push(node.object);
        node.childrenAfter.forEach(visit);
    };
    roots.forEach(visit);
    return result;
}
