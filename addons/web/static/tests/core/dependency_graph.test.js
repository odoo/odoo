// @ts-check

/**
 * Pure unit tests for dependency_graph.js.
 *
 * Tests cycle detection without OWL, DOM, or services.
 */

import { describe, expect, test } from "@odoo/hoot";
import { findDependencyCycle } from "@web/core/utils/dependency_graph";

describe("findDependencyCycle", () => {
    test("returns null for empty graph", () => {
        const graph = new Map();
        expect(findDependencyCycle(graph)).toBe(null);
    });

    test("returns null for single node with no deps", () => {
        const graph = new Map([["a", []]]);
        expect(findDependencyCycle(graph)).toBe(null);
    });

    test("returns null for acyclic graph", () => {
        const graph = new Map([
            ["a", ["b", "c"]],
            ["b", ["c"]],
            ["c", []],
        ]);
        expect(findDependencyCycle(graph)).toBe(null);
    });

    test("detects self-loop", () => {
        const graph = new Map([["a", ["a"]]]);
        const cycle = findDependencyCycle(graph);
        expect(cycle).toEqual(["a", "a"]);
    });

    test("detects two-node cycle", () => {
        const graph = new Map([
            ["a", ["b"]],
            ["b", ["a"]],
        ]);
        const cycle = findDependencyCycle(graph);
        expect(cycle).not.toBe(null);
        expect(cycle.length).toBe(3); // ["a", "b", "a"] or ["b", "a", "b"]
        // First and last element must be the same (closed cycle)
        expect(cycle[0]).toBe(cycle[cycle.length - 1]);
    });

    test("detects three-node cycle", () => {
        const graph = new Map([
            ["a", ["b"]],
            ["b", ["c"]],
            ["c", ["a"]],
        ]);
        const cycle = findDependencyCycle(graph);
        expect(cycle).not.toBe(null);
        expect(cycle.length).toBe(4); // e.g. ["a", "b", "c", "a"]
        expect(cycle[0]).toBe(cycle[cycle.length - 1]);
    });

    test("ignores external dependencies not in graph", () => {
        const graph = new Map([
            ["a", ["b", "external"]],
            ["b", []],
        ]);
        expect(findDependencyCycle(graph)).toBe(null);
    });

    test("detects cycle in subgraph (not all nodes involved)", () => {
        const graph = new Map([
            ["a", []],
            ["b", ["c"]],
            ["c", ["d"]],
            ["d", ["b"]],
        ]);
        const cycle = findDependencyCycle(graph);
        expect(cycle).not.toBe(null);
        // Cycle must involve b, c, d but not a
        expect(cycle).not.toInclude("a");
        expect(cycle[0]).toBe(cycle[cycle.length - 1]);
    });

    test("works with diamond dependency (no cycle)", () => {
        const graph = new Map([
            ["a", ["b", "c"]],
            ["b", ["d"]],
            ["c", ["d"]],
            ["d", []],
        ]);
        expect(findDependencyCycle(graph)).toBe(null);
    });

    test("works with complex graph containing one cycle", () => {
        // a -> b -> c -> d (acyclic)
        //           c -> e -> f -> c (cycle)
        const graph = new Map([
            ["a", ["b"]],
            ["b", ["c"]],
            ["c", ["d", "e"]],
            ["d", []],
            ["e", ["f"]],
            ["f", ["c"]],
        ]);
        const cycle = findDependencyCycle(graph);
        expect(cycle).not.toBe(null);
        expect(cycle[0]).toBe(cycle[cycle.length - 1]);
        // Cycle must be within {c, e, f}
        for (const node of cycle) {
            expect(["c", "e", "f"]).toInclude(node);
        }
    });

    test("handles nodes with undefined deps (treated as empty)", () => {
        const graph = new Map([
            ["a", ["b"]],
            ["b", undefined],
        ]);
        expect(findDependencyCycle(graph)).toBe(null);
    });
});
