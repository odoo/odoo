// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { makeLogger } from "@web/core/debug/debug_logger";

const auditLog = makeLogger("web.search.audit");
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    isInvisible,
    itemsFromState,
    itemsToState,
    panelFromState,
    panelToState,
    propertiesFromState,
    propertiesToState,
    queryFromState,
    queryToState,
} from "@web/search/search_state";

describe.current.tags("headless");

/** @returns {Record<string, any>} */
function makeSource() {
    const value = { id: 10, checked: false, display_name: "Tag A" };
    const group = { id: "g1", name: "Group", values: new Map([[10, value]]) };
    const filter = {
        id: 1,
        type: "filter",
        values: new Map([[10, value]]),
        groups: new Map([["g1", group]]),
    };
    return {
        query: [{ searchItemId: 3 }],
        nextId: 4,
        nextGroupId: 2,
        nextGroupNumber: 2,
        orderByCount: false,
        searchItems: { 3: { id: 3, type: "filter" } },
        searchPanelInfo: { loaded: true, shouldReload: false },
        sections: new Map([[1, filter]]),
        searchViewFields: {},
    };
}

/**
 * @param {Record<string, any>} source
 * @returns {Record<string, any>}
 */
function exportSource(source) {
    return {
        ...queryToState(source),
        ...itemsToState(source),
        ...panelToState(source),
        ...propertiesToState(source),
    };
}

/**
 * @param {Record<string, any>} state
 * @param {Record<string, any>} [target]
 * @returns {Record<string, any>}
 */
function importState(state, target = {}) {
    queryFromState(state, target);
    itemsFromState(state, target);
    panelFromState(state, target);
    propertiesFromState(state, target);
    return target;
}

describe("state export/import", () => {
    test("the export does not alias the live model", () => {
        const source = makeSource();
        const exported = exportSource(source);

        source.query.push({ searchItemId: 99 });
        /** @type {any} */ (source.sections.get(1)).values.get(10).checked = true;

        expect(exported.query).toEqual([{ searchItemId: 3 }]);
        const [, section] = exported.sections[0];
        const [, value] = section.values[0];
        expect(value.checked).toBe(false);
    });

    test("import re-aliases group values with filter values", () => {
        const source = makeSource();
        const exported = exportSource(source);

        const state = JSON.parse(JSON.stringify(exported));
        const target = importState(state);

        const section = target.sections.get(1);
        const group = section.groups.get("g1");
        expect(group.values.get(10)).toBe(section.values.get(10));

        section.values.get(10).checked = true;
        expect(group.values.get(10).checked).toBe(true);
    });

    test("import leaves the state object it was handed untouched", () => {
        const source = makeSource();
        const exported = exportSource(source);
        const state = JSON.parse(JSON.stringify(exported));
        const before = JSON.parse(JSON.stringify(state));

        const target = importState(state);

        expect(state).toEqual(before);
        expect(Array.isArray(state.sections[0][1].values)).toBe(true);

        target.sections.get(1).values.get(10).checked = true;
        expect(state.sections[0][1].values[0][1].checked).toBe(false);
    });

    test("the export survives a JSON round-trip and imports identically", () => {
        const source = makeSource();
        const exported = exportSource(source);

        const direct = importState(exported);
        const roundTripped = importState(JSON.parse(JSON.stringify(exported)));

        expect(roundTripped.query).toEqual(direct.query);
        expect(roundTripped.searchItems).toEqual(direct.searchItems);
        expect([...roundTripped.sections.keys()]).toEqual([...direct.sections.keys()]);
    });
});

test("a state written before the sort flag existed imports as unsorted", () => {
    const target = /** @type {any} */ ({});
    queryFromState(/** @type {any} */ ({ query: [] }), target);
    expect(target.orderByCount).toBe(false);
    expect(target.defaultGroupByRemoved).toBe(false);
});

describe("isInvisible", () => {
    test("an absent or falsy expression is not invisible", () => {
        expect(isInvisible(undefined, {})).toBe(false);
        expect(isInvisible("", {})).toBe(false);
        expect(isInvisible("False", {})).toBe(false);
        expect(isInvisible("0", {})).toBe(false);
    });

    test("a truthy expression is invisible, and the context is used", () => {
        expect(isInvisible("True", {})).toBe(true);
        expect(isInvisible("uid == 2", { uid: 2 })).toBe(true);
        expect(isInvisible("uid == 2", { uid: 7 })).toBe(false);
    });

    test("a malformed expression shows the item and names itself", () => {
        /** @type {string[]} */
        const warnings = [];
        patchWithCleanup(console, {
            warn: (/** @type {string} */ msg) => warnings.push(msg),
        });

        expect(isInvisible("uid ==", {})).toBe(false);

        expect(warnings.length).toBe(1);
        expect(warnings[0]).toInclude("uid ==");
    });

    test("an unknown name in the context is malformed too, not silently false", () => {
        /** @type {string[]} */
        const warnings = [];
        patchWithCleanup(console, {
            warn: (/** @type {string} */ msg) => warnings.push(msg),
        });

        expect(isInvisible("nope", {})).toBe(false);

        expect(warnings.length).toBe(1);
        expect(warnings[0]).toInclude("nope");
    });
});

describe("panel concern", () => {
    test("searchDomain is exported and restored", () => {
        const source = makeSource();
        source.searchDomain = [["foo", "=", "a"]];

        const exported = /** @type {Record<string, any>} */ (panelToState(source));
        expect(exported.searchDomain).toEqual([["foo", "=", "a"]]);
        expect(exported.searchDomain).not.toBe(source.searchDomain);

        /** @type {Record<string, any>} */
        const target = {};
        panelFromState(JSON.parse(JSON.stringify(exported)), target);
        expect(target.searchDomain).toEqual([["foo", "=", "a"]]);
    });

    test("a source without a searchDomain exports none, and a legacy state restores none", () => {
        const source = makeSource();
        const exported = /** @type {Record<string, any>} */ (panelToState(source));
        expect("searchDomain" in exported).toBe(false);

        const target = {};
        panelFromState(exported, target);
        expect("searchDomain" in target).toBe(false);
    });

    test("a state with no searchPanelInfo restores without throwing", () => {
        /** @type {Record<string, any>} */
        const target = {};
        panelFromState({ sections: [] }, target);
        expect(target.searchPanelInfo).toBe(undefined);
    });

    test("searchPanelInfo is normalised, not structurally cloned", () => {
        const source = makeSource();
        source.searchPanelInfo = {
            className: "",
            stamp: new Date("2026-01-01T00:00:00Z"),
            lookup: new Map([["a", 1]]),
        };

        const exported = /** @type {Record<string, any>} */ (panelToState(source));
        expect(typeof exported.searchPanelInfo.stamp).toBe("string");
        expect(exported.searchPanelInfo.lookup).toEqual({});
    });
});

describe("grouped sections carry value ids, not the values again", () => {
    test("a group exports ids and the values appear once", () => {
        const source = makeSource();
        const exported = /** @type {Record<string, any>} */ (panelToState(source));
        const [, section] = exported.sections[0];
        const [, group] = section.groups[0];

        expect(group.valueIds).toEqual([10]);
        expect("values" in group).toBe(false, {
            message: "the value objects are not written a second time",
        });
        expect(section.values.map((/** @type {any[]} */ [id]) => id)).toEqual([10]);
    });

    test("restoring rebuilds the group values as the SAME objects", () => {
        const source = makeSource();
        const wire = JSON.parse(JSON.stringify(panelToState(source)));
        /** @type {Record<string, any>} */
        const target = {};
        panelFromState(wire, target);

        const section = target.sections.get(1);
        const group = section.groups.get("g1");
        expect(group.values.get(10)).toBe(section.values.get(10));

        section.values.get(10).checked = true;
        expect(group.values.get(10).checked).toBe(true);
    });

    test("a version-2 state, which carried the values, still restores", () => {
        /** @type {any} */
        const legacy = {
            searchPanelInfo: { loaded: true },
            sections: [
                [
                    1,
                    {
                        id: 1,
                        type: "filter",
                        values: [
                            [10, { id: 10, checked: false, display_name: "Tag A" }],
                        ],
                        groups: [
                            [
                                "g1",
                                {
                                    id: "g1",
                                    name: "Group",
                                    values: [
                                        [
                                            10,
                                            {
                                                id: 10,
                                                checked: false,
                                                display_name: "Tag A",
                                            },
                                        ],
                                    ],
                                },
                            ],
                        ],
                    },
                ],
            ],
        };
        /** @type {Record<string, any>} */
        const target = {};
        panelFromState(legacy, target);

        const section = target.sections.get(1);
        const group = section.groups.get("g1");
        expect([...group.values.keys()]).toEqual([10]);
        expect(group.values.get(10)).toBe(section.values.get(10), {
            message: "and the aliasing is established even from the old shape",
        });
    });

    test("the wire is shorter for it", () => {
        const source = makeSource();
        const exported = panelToState(source);
        const wire = JSON.stringify(exported);
        const withDuplicates = JSON.parse(JSON.stringify(exported));
        for (const [, section] of withDuplicates.sections) {
            for (const [, group] of section.groups) {
                group.values = group.valueIds.map((/** @type {any} */ id) => [
                    id,
                    section.values.find((/** @type {any[]} */ [vid]) => vid === id)[1],
                ]);
                delete group.valueIds;
            }
        }
        expect(wire.length).toBeLessThan(JSON.stringify(withDuplicates).length);
    });
});

describe("properties concern", () => {
    function makePropertySource() {
        const parent = { name: "properties", type: "properties", string: "Properties" };
        return {
            searchViewFields: {
                properties: parent,
                "properties.my_char": {
                    name: "properties.my_char",
                    string: "My Char",
                    type: "char",
                    relatedPropertyField: parent,
                },
                foo: { name: "foo", type: "char", string: "Foo" },
            },
        };
    }

    test("only property-derived searchViewFields entries are exported", () => {
        const { propertySearchViewFields } = /** @type {Record<string, any>} */ (
            propertiesToState(makePropertySource())
        );
        expect(Object.keys(propertySearchViewFields)).toEqual(["properties.my_char"]);
        expect(propertySearchViewFields["properties.my_char"].string).toBe("My Char");
    });

    test("import merges the entries and re-aliases the parent field", () => {
        const state = JSON.parse(
            JSON.stringify(propertiesToState(makePropertySource())),
        );
        const liveParent = {
            name: "properties",
            type: "properties",
            string: "Properties",
        };
        /** @type {Record<string, any>} */
        const target = { searchViewFields: { properties: liveParent } };

        propertiesFromState(state, target);

        const restored = target.searchViewFields["properties.my_char"];
        expect(restored.string).toBe("My Char");
        expect(restored.relatedPropertyField).toBe(liveParent);
    });

    test("import never overwrites a live entry, and tolerates legacy states", () => {
        const live = { name: "properties.my_char", string: "Fresh", type: "char" };
        const target = { searchViewFields: { "properties.my_char": live } };
        propertiesFromState(
            {
                propertySearchViewFields: {
                    "properties.my_char": {
                        name: "properties.my_char",
                        string: "Stale",
                    },
                },
            },
            target,
        );
        expect(target.searchViewFields["properties.my_char"]).toBe(live);

        propertiesFromState({}, target);
        expect(target.searchViewFields["properties.my_char"]).toBe(live);
    });
});

test("panel snapshots isolate nested hierarchy and group arrays in both directions", () => {
    const source = makeSource();
    const section = source.sections.get(1);
    section.rootIds = [false, 10];
    section.sortedGroupIds = ["g1"];
    section.values.get(10).childrenIds = [11];
    const exported = panelToState(source);
    const target = /** @type {Record<string, any>} */ ({});
    panelFromState(exported, target);
    const restored = target.sections.get(1);
    restored.rootIds.push(20);
    restored.sortedGroupIds.push("g2");
    restored.values.get(10).childrenIds.push(12);
    auditLog.logic("snapshot-isolation", () => ({
        liveRoots: section.rootIds,
        savedRoots: exported.sections[0][1].rootIds,
        restoredRoots: restored.rootIds,
    }));
    expect(section.rootIds).toEqual([false, 10]);
    expect(section.sortedGroupIds).toEqual(["g1"]);
    expect(section.values.get(10).childrenIds).toEqual([11]);
    expect(exported.sections[0][1].rootIds).toEqual([false, 10]);
    expect(exported.sections[0][1].values[0][1].childrenIds).toEqual([11]);
    section.rootIds.push(30);
    expect(exported.sections[0][1].rootIds).toEqual([false, 10]);
});
