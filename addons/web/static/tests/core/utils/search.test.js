import { describe, expect, test } from "@odoo/hoot";

import { fuzzyLevenshteinLookup, fuzzyLookup, fuzzyTest } from "@web/core/utils/search";

describe.current.tags("headless");

test("fuzzyLookup", () => {
    const data = [
        { name: "Abby White" },
        { name: "Robert Black" },
        { name: "Jane Yellow" },
        { name: "Brandon Green" },
        { name: "Jérémy Red" },
        { name: "สมศรี จู่โจม" },
    ];
    expect(fuzzyLookup("ba", data, (d) => d.name)).toEqual([
        { name: "Brandon Green" },
        { name: "Robert Black" },
    ]);
    expect(fuzzyLookup("g", data, (d) => d.name)).toEqual([{ name: "Brandon Green" }]);
    expect(fuzzyLookup("z", data, (d) => d.name)).toEqual([]);
    expect(fuzzyLookup("brand", data, (d) => d.name)).toEqual([{ name: "Brandon Green" }]);
    expect(fuzzyLookup("jâ", data, (d) => d.name)).toEqual([{ name: "Jane Yellow" }]);
    expect(fuzzyLookup("je", data, (d) => d.name)).toEqual([
        { name: "Jérémy Red" },
        { name: "Jane Yellow" },
    ]);
    expect(fuzzyLookup("", data, (d) => d.name)).toEqual([]);
    expect(fuzzyLookup("สมศ", data, (d) => d.name)).toEqual([{ name: "สมศรี จู่โจม" }]);
});

test("fuzzyLevenshteinLookup", () => {
    const words = ["café", "cafétéria", "restaurant", "boulangerie"];

    // A word containing the pattern is a perfect match: the word is returned,
    // not the pattern itself.
    expect(fuzzyLevenshteinLookup("cafe", words)).toEqual(["café", "cafétéria"]);
    expect(fuzzyLevenshteinLookup("boulangerie", words)).toEqual(["boulangerie"]);

    // Misspelled words are corrected within the error margin.
    expect(fuzzyLevenshteinLookup("resturant", words)).toEqual(["restaurant"]);
    expect(fuzzyLevenshteinLookup("zzzz", words)).toEqual([]);

    // Perfect matches come before corrected ones.
    expect(fuzzyLevenshteinLookup("restaurant", ["restaurants", "restaurent"])).toEqual([
        "restaurants",
        "restaurent",
    ]);
});

test("fuzzyTest", () => {
    expect(fuzzyTest("a", "Abby White")).toBe(true);
    expect(fuzzyTest("ba", "Brandon Green")).toBe(true);
    expect(fuzzyTest("je", "Jérémy red")).toBe(true);
    expect(fuzzyTest("jé", "Jeremy red")).toBe(true);
    expect(fuzzyTest("z", "Abby White")).toBe(false);
    expect(fuzzyTest("ba", "Abby White")).toBe(false);
});
