import { describe, expect, test } from "@odoo/hoot";
import { trackOccurrences, trackOccurrencesPair } from "@html_editor/utils/tracking";

describe("trackOccurrences", () => {
    test("should return true only the first occurrence of each key", () => {
        const isFirstOccurrence = trackOccurrences();
        expect(isFirstOccurrence("a")).toEqual(true);
        expect(isFirstOccurrence("b")).toEqual(true);

        expect(isFirstOccurrence("a")).toEqual(false);
        expect(isFirstOccurrence("b")).toEqual(false);

        expect(isFirstOccurrence("a")).toEqual(false);
        expect(isFirstOccurrence("b")).toEqual(false);

        expect(isFirstOccurrence("c")).toEqual(true);
        expect(isFirstOccurrence("c")).toEqual(false);
    });
});

describe("trackOccurrencesPair", () => {
    test("should return true only the first occurrence of each tuple", () => {
        const isFirstOccurrence = trackOccurrencesPair();
        expect(isFirstOccurrence("a", "b")).toEqual(true);
        expect(isFirstOccurrence("b", "a")).toEqual(true);
        expect(isFirstOccurrence("b", "c")).toEqual(true);

        expect(isFirstOccurrence("a", "b")).toEqual(false);
        expect(isFirstOccurrence("b", "a")).toEqual(false);
        expect(isFirstOccurrence("b", "c")).toEqual(false);

        expect(isFirstOccurrence("d", "e")).toEqual(true);

        expect(isFirstOccurrence("a", "b")).toEqual(false);
        expect(isFirstOccurrence("b", "a")).toEqual(false);
        expect(isFirstOccurrence("b", "c")).toEqual(false);
        expect(isFirstOccurrence("d", "e")).toEqual(false);
    });
});
