import { describe, expect, test } from "@odoo/hoot";

import { computeAggregatedValue } from "@web/views/utils";

describe.current.tags("headless");

describe("computeAggregatedValue", () => {
    test("sum", () => {
        expect(computeAggregatedValue([], "sum")).toBe(0);
        expect(computeAggregatedValue([7], "sum")).toBe(7);
        expect(computeAggregatedValue([7, 3], "sum")).toBe(10);
        expect(computeAggregatedValue([7.23, 3.1], "sum")).toBe(10.33);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "sum")).toBe(35);
    });

    test("min", () => {
        expect(computeAggregatedValue([], "min")).toBe(Infinity);
        expect(computeAggregatedValue([7], "min")).toBe(7);
        expect(computeAggregatedValue([7, 3], "min")).toBe(3);
        expect(computeAggregatedValue([7.23, 3.1], "min")).toBe(3.1);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "min")).toBe(-5);
    });

    test("max", () => {
        expect(computeAggregatedValue([], "max")).toBe(-Infinity);
        expect(computeAggregatedValue([7], "max")).toBe(7);
        expect(computeAggregatedValue([7, 3], "max")).toBe(7);
        expect(computeAggregatedValue([7.23, 3.1], "max")).toBe(7.23);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "max")).toBe(27);
    });

    test("avg", () => {
        expect(computeAggregatedValue([], "avg")).toBe(NaN);
        expect(computeAggregatedValue([7], "avg")).toBe(7);
        expect(computeAggregatedValue([7, 3], "avg")).toBe(5);
        expect(computeAggregatedValue([7.23, 3.1], "avg")).toBe(5.165);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "avg")).toBe(5);
    });

    test("count", () => {
        expect(computeAggregatedValue([], "count")).toBe(0);
        expect(computeAggregatedValue([7], "count")).toBe(1);
        expect(computeAggregatedValue([7, 3], "count")).toBe(2);
        expect(computeAggregatedValue([7.23, 3.1], "count")).toBe(2);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "count")).toBe(7);
    });

    test("count_distinct", () => {
        expect(computeAggregatedValue([], "count_distinct")).toBe(0);
        expect(computeAggregatedValue([7], "count_distinct")).toBe(1);
        expect(computeAggregatedValue([7, 3], "count_distinct")).toBe(2);
        expect(computeAggregatedValue([7.23, 3.1], "count_distinct")).toBe(2);
        expect(computeAggregatedValue([10, 2, -3, 2, -5, 27, 2], "count_distinct")).toBe(5);
    });

    test("invalid aggregator", () => {
        expect(() => computeAggregatedValue([])).toThrow("Invalid aggregator 'undefined'");
        expect(() => computeAggregatedValue([], "oups")).toThrow("Invalid aggregator 'oups'");
    });
});
