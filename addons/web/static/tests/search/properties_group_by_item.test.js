// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, useSubEnv, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";

/**
 * @param {Record<string, any>[]} searchItems
 * @param {{definitionsLoaded?: boolean, fill?: () => Promise<void>}} [options]
 * @returns {any}
 */
function makeItem(searchItems, { definitionsLoaded = false, fill } = {}) {
    const component = Object.create(PropertiesGroupByItem.prototype);
    component.props = { item: { fieldName: "props" }, onGroup: () => {} };
    component.state = { definitionsLoaded };
    component.env = {
        searchModel: {
            getSearchItems: (
                /** @type {(item: Record<string, any>) => boolean} */ predicate,
            ) => searchItems.filter(predicate),
            updateSearchViewItemsProperty: fill || (async () => {}),
        },
    };
    return component;
}

/** @param {Record<string, any>} overrides */
const propertyGroupBy = (overrides = {}) => ({
    type: "groupBy",
    isProperty: true,
    propertyFieldName: "props",
    definitionRecordId: 1,
    isActive: false,
    ...overrides,
});

describe("groupByItems", () => {
    describe.current.tags("headless");

    test("is empty until the definitions have been loaded", () => {
        const component = makeItem([propertyGroupBy()]);
        expect(component.groupByItems).toEqual([]);
    });

    test("selects only this field's property group-bys once loaded", () => {
        const component = makeItem(
            [
                propertyGroupBy({ id: 1 }),
                propertyGroupBy({ id: 2, propertyFieldName: "other" }),
                propertyGroupBy({ id: 3, isProperty: false }),
                propertyGroupBy({ id: 4, type: "filter" }),
                propertyGroupBy({ id: 5, type: "dateGroupBy" }),
            ],
            { definitionsLoaded: true },
        );
        expect(component.groupByItems.map((/** @type {any} */ i) => i.id)).toEqual([
            1, 5,
        ]);
    });
});

describe("isActive", () => {
    describe.current.tags("headless");

    test("an active property group-by shows the accordion as selected", () => {
        const component = makeItem([propertyGroupBy({ isActive: true })], {
            definitionsLoaded: true,
        });
        expect(component.isActive).toBe(true);
    });

    test("...and still does before this component has loaded definitions", () => {
        const component = makeItem([propertyGroupBy({ isActive: true })], {
            definitionsLoaded: false,
        });
        expect(component.isActive).toBe(true);
    });

    test("no active property group-by leaves it unselected", () => {
        const component = makeItem([propertyGroupBy({ isActive: false })], {
            definitionsLoaded: false,
        });
        expect(component.isActive).toBe(false);
    });

    test("another field's active property does not select this one", () => {
        const component = makeItem(
            [propertyGroupBy({ isActive: true, propertyFieldName: "other" })],
            { definitionsLoaded: false },
        );
        expect(component.isActive).toBe(false);
    });

    test("a model with no property items at all is unselected", () => {
        expect(makeItem([]).isActive).toBe(false);
    });
});

describe("isSingleParent", () => {
    describe.current.tags("headless");

    test("true when every property comes from one definition record", () => {
        const component = makeItem(
            [
                propertyGroupBy({ definitionRecordId: 7 }),
                propertyGroupBy({ definitionRecordId: 7 }),
            ],
            { definitionsLoaded: true },
        );
        expect(component.isSingleParent).toBe(true);
    });

    test("false when two definition records contribute", () => {
        const component = makeItem(
            [
                propertyGroupBy({ definitionRecordId: 7 }),
                propertyGroupBy({ definitionRecordId: 8 }),
            ],
            { definitionsLoaded: true },
        );
        expect(component.isSingleParent).toBe(false);
    });
});

describe("loadDefinitions", () => {
    describe.current.tags("headless");

    test("fetches once and records that it has", async () => {
        let calls = 0;
        const component = makeItem([], {
            fill: async () => {
                calls++;
            },
        });
        await component.loadDefinitions();
        expect(component.state.definitionsLoaded).toBe(true);
        await component.loadDefinitions();
        expect(calls).toBe(1);
    });

    test("two overlapping opens issue one fetch", async () => {
        let calls = 0;
        /** @type {() => void} */
        /** @type {(() => void) | undefined} */
        let release;
        const component = makeItem([], {
            fill: () => {
                calls++;
                return new Promise((resolve) => (release = resolve));
            },
        });
        const first = component.loadDefinitions();
        const second = component.loadDefinitions();
        expect(calls).toBe(1);
        release?.();
        await Promise.all([first, second]);
        expect(component.state.definitionsLoaded).toBe(true);
    });

    test("a failed fetch leaves it retryable rather than stuck", async () => {
        let calls = 0;
        const component = makeItem([], {
            fill: async () => {
                calls++;
                throw new Error("boom");
            },
        });
        await expect(component.loadDefinitions()).rejects.toThrow(/boom/);
        expect(component.state.definitionsLoaded).toBe(false);

        await expect(component.loadDefinitions()).rejects.toThrow(/boom/);
        expect(calls).toBe(2);
    });
});

describe("what triggers the fetch", () => {
    /** @param {() => Promise<void>} fill */
    async function mountItem(fill) {
        class Parent extends Component {
            static components = { PropertiesGroupByItem };
            static template = xml`
                <t t-out="this.state.tick"/>
                <PropertiesGroupByItem item="this.item" onGroup="() => {}"/>`;
            static props = ["*"];
            setup() {
                this.item = { fieldName: "props", description: "Properties" };
                this.state = useState({ tick: 0 });
                useSubEnv({
                    searchModel: {
                        getSearchItems: () => /** @type {any[]} */ ([]),
                        updateSearchViewItemsProperty: fill,
                    },
                });
            }
        }
        return mountWithCleanup(Parent);
    }

    test("a render the accordion did not cause does not fetch", async () => {
        const parent = /** @type {any} */ (
            await mountItem(async () => expect.step("fetch"))
        );
        expect(".o_accordion_toggle").toHaveCount(1);
        expect.verifySteps([]);

        parent.state.tick++;
        await animationFrame();
        expect.verifySteps([]);
    });

    test("expanding the accordion fetches once, collapsing it does not", async () => {
        await mountItem(async () => expect.step("fetch"));

        await click(".o_accordion_toggle");
        await animationFrame();
        expect.verifySteps(["fetch"]);

        await click(".o_accordion_toggle");
        await animationFrame();
        expect.verifySteps([]);

        await click(".o_accordion_toggle");
        await animationFrame();
        expect.verifySteps([]);
    });
});
