import { onRpc } from "@web/../tests/web_test_helpers";

onRpc("cycles_in_hierarchy_read", function findCyclesInHierarchy({ model, args }) {
    const [domain] = args;
    const result = this.env[model].search(domain);
    const records = result._records || [];

    // Build parent map: {id: parent_id}
    const parentMap = { null: null };
    for (const record of records) {
        parentMap[record.id] =
            record["parent_id"] && record["parent_id"] !== false ? record["parent_id"] : null;
    }

    const visited = new Set();
    const inCycle = new Set();

    for (const record of records) {
        const recordId = record.id;
        if (visited.has(recordId)) {
            continue;
        }

        // Floyd's Tortoise and Hare
        let parent = recordId;
        let grandParent = recordId;
        const firstIteration = true;
        while (firstIteration) {
            parent = parentMap[parent];
            grandParent = parentMap[parentMap[grandParent]];
            if (parent == null || grandParent == null) {
                break;
            }
            if (parent === grandParent || inCycle.has(parent) || inCycle.has(grandParent)) {
                // Found a cycle, mark all nodes in the cycle
                let cycleNode = recordId;
                while (!inCycle.has(cycleNode)) {
                    inCycle.add(cycleNode);
                    visited.add(cycleNode);
                    cycleNode = parentMap[cycleNode];
                }
                break;
            }
            if (visited.has(grandParent) || visited.has(parent)) {
                break;
            }
        }
        // Mark the current traversal as visited
        let current = recordId;
        while (current != null && !visited.has(current)) {
            visited.add(current);
            current = parentMap[current];
        }
    }
    // Return records that are part of a cycle
    return Array.from(inCycle);
});
