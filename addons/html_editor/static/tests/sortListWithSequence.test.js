import {
    sequenceAfter,
    sequenceBefore,
    sequenceNumber,
    sortListWithSequence,
    withSequence,
} from "@html_editor/utils/resource";
import { test, describe, expect } from "@odoo/hoot";

describe("sortListWithSequence", () => {
    test("Should handle empty list", () => {
        expect(sortListWithSequence([])).toEqual([]);
    });
    test("Should handle single element", () => {
        expect(sortListWithSequence(["A"])).toEqual(["A"]);
    });
    test("Should handle elements with no sequence", () => {
        expect(sortListWithSequence(["A", "B", "C"])).toEqual(["A", "B", "C"]);
    });
    test("Should handle elements with sequenceBefore", () => {
        expect(
            sortListWithSequence([
                withSequence({ id: "A" }, "A"),
                withSequence({ sequenceBefore: "A" }, "C"),
                "B",
            ])
        ).toEqual(["C", "A", "B"]);
    });
    test("Should handle elements with sequenceAfter", () => {
        expect(
            sortListWithSequence([
                "A",
                withSequence({ sequenceAfter: "B" }, "C"),
                withSequence({ id: "B" }, "B"),
            ])
        ).toEqual(["A", "B", "C"]);
    });
    test("Should handle elements with sequenceNumber", () => {
        expect(
            sortListWithSequence([
                "A",
                withSequence(5, "B"),
                withSequence({ sequenceNumber: 3 }, "C"),
            ])
        ).toEqual(["C", "B", "A"]);
    });
    test("Should handle complex sequences", () => {
        expect(
            sortListWithSequence([
                "A",
                withSequence(5, "B"),
                "C",
                withSequence({ id: "foo1" }, "D"),
                withSequence({ sequenceBefore: "foo1", id: "foo2" }, "E"),
                withSequence({ sequenceAfter: "foo2" }, "F"),
                withSequence({ sequenceNumber: 4 }, "G"),
            ])
        ).toEqual(["G", "B", "A", "C", "E", "F", "D"]);
    });
    test("Should handle with property sequenceNumber on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { sequenceNumber: 5, id: "B" },
                { sequenceNumber: 3, id: "C" },
            ])
        ).toEqual([
            //
            { id: "C", sequenceNumber: 3 },
            { id: "B", sequenceNumber: 5 },
            { id: "A" },
        ]);
    });
    test("Should handle with property sequenceBefore on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { sequenceBefore: "A", id: "B" },
            ])
        ).toEqual([
            //
            { id: "B", sequenceBefore: "A" },
            { id: "A" },
        ]);
    });
    test("Should handle with property sequenceAfter on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { sequenceAfter: "C", id: "B" },
                { id: "C" },
            ])
        ).toEqual([
            //
            { id: "A" },
            { id: "C" },
            { id: "B", sequenceAfter: "C" },
        ]);
    });
    test("Should handle with symbol property sequenceNumber on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { id: "B", [sequenceNumber]: 5, sequenceNumber: 15 },
                { id: "C", [sequenceNumber]: 3, sequenceNumber: 20 },
            ])
        ).toEqual([
            //
            { id: "C", [sequenceNumber]: 3, sequenceNumber: 20 },
            { id: "B", [sequenceNumber]: 5, sequenceNumber: 15 },
            { id: "A" },
        ]);
    });
    test("Should handle with symbol property sequenceBefore on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { id: "B" },
                { id: "C", [sequenceBefore]: "A", sequenceBefore: "B" },
            ])
        ).toEqual([
            //
            { id: "C", [sequenceBefore]: "A", sequenceBefore: "B" },
            { id: "A" },
            { id: "B" },
        ]);
    });
    test("Should handle with symbol property sequenceAfter on the object", () => {
        expect(
            sortListWithSequence([
                //
                { id: "A" },
                { id: "B" },
                { id: "C", [sequenceAfter]: "B", sequenceAfter: "A" },
            ])
        ).toEqual([
            //
            { id: "A" },
            { id: "B" },
            { id: "C", [sequenceAfter]: "B", sequenceAfter: "A" },
        ]);
    });
});
