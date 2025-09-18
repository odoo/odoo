// @ts-check

/** @module @web/core/utils/dependency_graph - Iterative DFS cycle detection for directed dependency graphs */

/**
 * Dependency graph cycle detection.
 *
 * Pure utility for detecting circular dependencies in directed acyclic graphs.
 * Used by the service launcher to detect circular service dependencies at
 * startup (which would otherwise silently hang).
 *
 * This is a pure utility with no OWL or DOM dependencies.
 *
 * @see env.js for the integration point
 */

/**
 * Find a cycle in a dependency graph, if one exists.
 *
 * Uses iterative DFS with explicit stack to avoid call-stack overflow on
 * pathologically deep graphs.
 *
 * @param {Map<string, string[]>} graph
 *     Map from node name to its dependency names.
 *     Nodes not present as keys are treated as external (no outgoing edges).
 * @returns {string[] | null}
 *     The cycle path (e.g. ["a", "b", "c", "a"]) or null if acyclic.
 */
export function findDependencyCycle(graph) {
    const NOT_VISITED = 0;
    const IN_STACK = 1;
    const DONE = 2;

    /** @type {Map<string, number>} */
    const state = new Map();
    for (const name of graph.keys()) {
        state.set(name, NOT_VISITED);
    }

    /** @type {Map<string, string | null>} parent pointers for path reconstruction */
    const parent = new Map();

    for (const startNode of graph.keys()) {
        if (state.get(startNode) === DONE) {
            continue;
        }

        // Iterative DFS using an explicit stack.
        // Each frame is [node, depIndex] — depIndex tracks which dependency
        // to visit next, avoiding re-processing already-visited deps.
        /** @type {Array<[string, number]>} */
        const stack = [[startNode, 0]];
        state.set(startNode, IN_STACK);
        parent.set(startNode, null);

        while (stack.length > 0) {
            const frame = stack[stack.length - 1];
            const node = frame[0];
            const deps = graph.get(node) || [];

            if (frame[1] >= deps.length) {
                // All deps processed — mark done and backtrack
                state.set(node, DONE);
                stack.pop();
                continue;
            }

            const dep = deps[frame[1]++];

            // Skip nodes not in the graph (external dependencies)
            if (!graph.has(dep)) {
                continue;
            }

            const depState = state.get(dep);
            if (depState === IN_STACK) {
                // Found a cycle — reconstruct the path
                return _reconstructCycle(parent, node, dep);
            }
            if (depState === DONE) {
                continue;
            }

            // Visit unvisited dep
            state.set(dep, IN_STACK);
            parent.set(dep, node);
            stack.push([dep, 0]);
        }
    }

    return null;
}

/**
 * Reconstruct a cycle path from parent pointers.
 *
 * @param {Map<string, string | null>} parent
 * @param {string} from - Node whose dependency closes the cycle
 * @param {string} to - The dependency that was already in the stack
 * @returns {string[]} The cycle path, e.g. ["a", "b", "c", "a"]
 */
function _reconstructCycle(parent, from, to) {
    // Walk backwards from `from` to `to` via parent pointers.
    // The cycle is: to → ... → from → to
    const path = [from];
    let current = from;
    while (current !== to) {
        current = /** @type {string} */ (parent.get(current));
        path.push(current);
    }
    path.reverse(); // Now: [to, ..., from]
    path.push(to); // Close the cycle
    return path;
}
