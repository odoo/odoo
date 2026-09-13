// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { makeCompositionDouble } from "@web/../tests/search/search_doubles";
import { Mutex } from "@web/core/utils/concurrency";
import { SearchPanelMixin } from "@web/search/search_panel/search_panel_mixin";
import { hasValues } from "@web/search/search_state";

const PanelModel = SearchPanelMixin(class {});

/**
 * @param {Map<number,Object>} sections
 * @param {Object} [overrides]
 */
function makeSearchModel(sections, overrides = {}) {
    const model = new PanelModel();
    Object.assign(
        model,
        makeCompositionDouble("search/search_panel/search_panel_mixin.js", {
            sections,
            ...overrides,
        }),
    );
    return model;
}

/**
 * @param {any} id
 * @param {Record<string, any>} [overrides]
 * @returns {any}
 */
function makeCategory(id, overrides = {}) {
    return {
        id,
        type: "category",
        activeValueId: false,
        values: new Map(),
        index: id,
        expand: false,
        enableCounters: false,
        ...overrides,
    };
}

/**
 * @param {any} id
 * @param {any[][]} [valueEntries]
 * @param {Record<string, any>} [overrides]
 * @returns {any}
 */
function makeFilter(id, valueEntries = [], overrides = {}) {
    const values = new Map(
        valueEntries.map(([vid, checked]) => [vid, { id: vid, checked }]),
    );
    return {
        id,
        type: "filter",
        values,
        index: id,
        domain: "[]",
        expand: false,
        enableCounters: false,
        ...overrides,
    };
}

describe("toggleCategoryValue", () => {
    test("sets activeValueId on the category", () => {
        const cat = makeCategory(1, { activeValueId: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model.toggleCategoryValue(1, 42);

        expect(cat.activeValueId).toBe(42);
    });

    test("replaces an existing activeValueId", () => {
        const cat = makeCategory(1, { activeValueId: 10 });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model.toggleCategoryValue(1, 20);

        expect(cat.activeValueId).toBe(20);
    });

    test("calls _notify", () => {
        const sections = new Map([[1, makeCategory(1)]]);
        const model = makeSearchModel(sections);

        model.toggleCategoryValue(1, 5);

        expect(model._notifications.length).toBe(1);
    });
});

describe("toggleFilterValues", () => {
    test("toggles checked state of given value IDs", () => {
        const filter = makeFilter(1, [
            [10, false],
            [20, true],
        ]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model.toggleFilterValues(1, [10, 20]);

        expect(filter.values.get(10).checked).toBe(true);
        expect(filter.values.get(20).checked).toBe(false);
    });

    test("forceTo=true sets all values to checked", () => {
        const filter = makeFilter(1, [
            [1, false],
            [2, false],
            [3, true],
        ]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model.toggleFilterValues(1, [1, 2, 3], true);

        expect(filter.values.get(1).checked).toBe(true);
        expect(filter.values.get(2).checked).toBe(true);
        expect(filter.values.get(3).checked).toBe(true);
    });

    test("forceTo=false clears all values", () => {
        const filter = makeFilter(1, [
            [1, true],
            [2, true],
        ]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model.toggleFilterValues(1, [1, 2], false);

        expect(filter.values.get(1).checked).toBe(false);
        expect(filter.values.get(2).checked).toBe(false);
    });

    test("calls _notify", () => {
        const filter = makeFilter(1, [[1, false]]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model.toggleFilterValues(1, [1]);

        expect(model._notifications.length).toBe(1);
    });

    test("ignores ids that no longer exist (refetch between render and click)", () => {
        const filter = makeFilter(1, [[10, false]]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model.toggleFilterValues(1, [10, 20]);

        expect(filter.values.get(10).checked).toBe(true);
        expect(filter.values.has(20)).toBe(false);
        expect(model._notifications.length).toBe(1);
    });
});

describe("clearSections", () => {
    test("resets category activeValueId to false", () => {
        const cat = makeCategory(1, { activeValueId: 7 });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model.clearSections([1]);

        expect(cat.activeValueId).toBe(false);
    });

    test("unchecks all filter values", () => {
        const filter = makeFilter(2, [
            [10, true],
            [20, true],
        ]);
        const sections = new Map([[2, filter]]);
        const model = makeSearchModel(sections);

        model.clearSections([2]);

        expect(filter.values.get(10).checked).toBe(false);
        expect(filter.values.get(20).checked).toBe(false);
    });

    test("clears multiple sections in one call", () => {
        const cat = makeCategory(1, { activeValueId: 5 });
        const filter = makeFilter(2, [[1, true]]);
        const sections = new Map([
            [1, cat],
            [2, filter],
        ]);
        const model = makeSearchModel(sections);

        model.clearSections([1, 2]);

        expect(cat.activeValueId).toBe(false);
        expect(filter.values.get(1).checked).toBe(false);
    });
});

describe("getSections", () => {
    test("returns sections in Map insertion order (arch order)", () => {
        const sections = new Map([
            [3, makeCategory(3)],
            [1, makeCategory(1)],
            [2, makeCategory(2)],
        ]);
        const model = makeSearchModel(sections);

        const result = model.getSections();

        expect(result.map((s) => s.id)).toEqual([3, 1, 2]);
    });

    test("marks category as empty when values.size <= 1", () => {
        const cat = makeCategory(1);
        cat.values.set(false, { id: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        const result = model.getSections();

        expect(result[0].empty).toBe(true);
    });

    test("marks filter as empty when values.size is 0", () => {
        const filter = makeFilter(1, []);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        const result = model.getSections();

        expect(result[0].empty).toBe(true);
    });

    test("marks filter as non-empty when it has values", () => {
        const filter = makeFilter(1, [[1, false]]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        const result = model.getSections();

        expect(result[0].empty).toBe(false);
    });

    test("applies predicate filter", () => {
        const sections = new Map([
            [1, makeCategory(1)],
            [2, makeFilter(2)],
        ]);
        const model = makeSearchModel(sections);

        const result = model.getSections((s) => s.type === "filter");

        expect(result.length).toBe(1);
        expect(result[0].type).toBe("filter");
    });

    test("returns shallow copies — mutations do not affect originals", () => {
        const cat = makeCategory(1, { activeValueId: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        const result = model.getSections();
        result[0].activeValueId = 999;

        expect(cat.activeValueId).toBe(false);
    });

    test("memoizes the list until a tree rebuild invalidates it", () => {
        const cat = makeCategory(1, { hierarchize: false });
        cat.values.set(false, { id: false, childrenIds: [], parentId: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        const first = model.getSections();
        expect(model.getSections()).toBe(first);
        expect(first[0].empty).toBe(true);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [{ id: 10, parent_id: false }],
        });

        const second = model.getSections();
        expect(second).not.toBe(first);
        expect(second[0].empty).toBe(false);
    });
});

describe("_updateCategoryValue", () => {
    test("keeps activeValueId when it is in valueIds", () => {
        const cat = makeCategory(1, { activeValueId: 5 });
        const model = makeSearchModel(new Map());

        model._updateCategoryValue(cat, [false, 5, 10]);

        expect(cat.activeValueId).toBe(5);
    });

    test("resets activeValueId to first valueId when current is absent", () => {
        const cat = makeCategory(1, { activeValueId: 99 });
        const model = makeSearchModel(new Map());

        model._updateCategoryValue(cat, [false, 5, 10]);

        expect(cat.activeValueId).toBe(false);
    });

    test("resets to false when valueIds contains only [false]", () => {
        const cat = makeCategory(1, { activeValueId: 7 });
        const model = makeSearchModel(new Map());

        model._updateCategoryValue(cat, [false]);

        expect(cat.activeValueId).toBe(false);
    });
});

describe("_createCategoryTree", () => {
    test("populates values Map from server result", () => {
        const cat = makeCategory(1, { hierarchize: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [
                { id: 10, display_name: "Apple", parent_id: false },
                { id: 20, display_name: "Banana", parent_id: false },
            ],
        });

        expect(cat.values.has(10)).toBe(true);
        expect(cat.values.has(20)).toBe(true);
    });

    test("builds correct rootIds list (false + top-level ids)", () => {
        const cat = makeCategory(1, { hierarchize: true });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [
                { id: 10, parent_id: false },
                { id: 20, parent_id: false },
                { id: 30, parent_id: 10 },
            ],
        });

        expect(cat.rootIds).toEqual([false, 10, 20]);
    });

    test("sets childrenIds on parent values", () => {
        const cat = makeCategory(1, { hierarchize: true });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [
                { id: 10, parent_id: false },
                { id: 20, parent_id: 10 },
            ],
        });

        expect(cat.values.get(10).childrenIds).toInclude(20);
    });

    test("sets errorMsg and empty values on server error", () => {
        const cat = makeCategory(1, { hierarchize: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [],
            error_msg: "Access denied",
        });

        expect(cat.errorMsg).toBe("Access denied");
        expect(cat.values.size).toBe(0);
    });

    test("recovers from a failed fetch: a successful rebuild clears errorMsg", () => {
        const cat = makeCategory(1, { hierarchize: false });
        cat.values.set(false, { id: false, childrenIds: [], parentId: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, { values: [], error_msg: "Network error" });
        expect(cat.errorMsg).toBe("Network error");
        expect(hasValues(cat)).toBe(true);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [{ id: 10, parent_id: false }],
        });

        expect("errorMsg" in cat).toBe(false);
        expect(cat.values.has(10)).toBe(true);
        expect(hasValues(cat)).toBe(true);
    });

    test("drops values removed server-side on a subsequent fetch", () => {
        const cat = makeCategory(1, { hierarchize: false });
        cat.values.set(false, { id: false, childrenIds: [], parentId: false });
        const sections = new Map([[1, cat]]);
        const model = makeSearchModel(sections);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [
                { id: 10, parent_id: false },
                { id: 20, parent_id: false },
            ],
        });
        expect(cat.values.has(10)).toBe(true);
        expect(cat.values.has(20)).toBe(true);

        model._createCategoryTree(1, {
            parent_field: "parent_id",
            values: [{ id: 10, parent_id: false }],
        });

        expect(cat.values.has(20)).toBe(false);
        expect(cat.values.has(10)).toBe(true);
        expect(cat.values.has(false)).toBe(true);
        expect(cat.rootIds).toEqual([false, 10]);
    });
});

describe("_createFilterTree", () => {
    test("populates values from flat server result", () => {
        const filter = makeFilter(1);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model._createFilterTree(1, {
            values: [
                { id: 10, display_name: "Tag A" },
                { id: 20, display_name: "Tag B" },
            ],
        });

        expect(filter.values.has(10)).toBe(true);
        expect(filter.values.has(20)).toBe(true);
    });

    test("restores checked state for values that were previously checked", () => {
        const filter = makeFilter(1, [[10, true]]);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model._createFilterTree(1, {
            values: [
                { id: 10, display_name: "Tag A" },
                { id: 20, display_name: "Tag B" },
            ],
        });

        expect(filter.values.get(10).checked).toBe(true);
        expect(filter.values.get(20).checked).toBe(false);
    });

    test("sets errorMsg on server error", () => {
        const filter = makeFilter(1);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model._createFilterTree(1, {
            values: [],
            error_msg: "Server error",
        });

        expect(filter.errorMsg).toBe("Server error");
    });

    test("recovers from a failed fetch: a successful rebuild clears errorMsg", () => {
        const filter = makeFilter(1);
        const sections = new Map([[1, filter]]);
        const model = makeSearchModel(sections);

        model._createFilterTree(1, { values: [], error_msg: "Network error" });
        expect(filter.errorMsg).toBe("Network error");
        expect(hasValues(filter)).toBe(true);

        model._createFilterTree(1, {
            values: [{ id: 10, display_name: "Tag A" }],
        });

        expect("errorMsg" in filter).toBe(false);
        expect(filter.values.has(10)).toBe(true);
        expect(hasValues(filter)).toBe(true);
    });
});

describe("_fetchCategories per-section stale guard", () => {
    function makeDeferred() {
        let resolve;
        const promise = new Promise((r) => {
            resolve = r;
        });
        return { promise, resolve };
    }

    function makeMockOrm() {
        const deferredsByField = new Map();
        const orm = {
            cache() {
                return this;
            },
            call(_resModel, _method, args) {
                const fieldName = args[0];
                const list = deferredsByField.get(fieldName) || [];
                const deferred = makeDeferred();
                list.push(deferred);
                deferredsByField.set(fieldName, list);
                return deferred.promise;
            },
        };
        return { orm, deferredsByField };
    }

    test("a later fetch of one section does not drop another section's in-flight response", async () => {
        const catA = makeCategory(1, { fieldName: "a" });
        const catB = makeCategory(2, { fieldName: "b" });
        const sections = new Map([
            [1, catA],
            [2, catB],
        ]);
        /** @type {any[]} */
        const created = [];
        const { orm, deferredsByField } = makeMockOrm();
        const model = makeSearchModel(sections, {
            _sectionLoadIds: new Map(),
            orm,
            globalContext: {},
            resModel: "res.partner",
            searchDomain: [],
            categories: [catA, catB],
            _getFilterDomain: () => [],
            _getCategoryDomain: () => [],
            _createCategoryTree: (/** @type {any} */ id, /** @type {any} */ result) =>
                created.push([id, result]),
            _reset() {},
            trigger() {},
        });

        const p1 = model._fetchCategories([catA, catB]);
        const p2 = model._fetchCategories([catB]);

        const resultA = { values: [{ id: 10 }], _tag: "A" };
        const resultB1 = { values: [{ id: 20 }], _tag: "B1" };
        const resultB2 = { values: [{ id: 30 }], _tag: "B2" };
        deferredsByField.get("a")[0].resolve(resultA);
        deferredsByField.get("b")[0].resolve(resultB1);
        deferredsByField.get("b")[1].resolve(resultB2);
        await Promise.all([p1, p2]);

        expect(created.length).toBe(2);
        const applied = new Map(created);
        expect(applied.get(1)).toBe(resultA);
        expect(applied.get(2)).toBe(resultB2);
    });

    test("a client-side failure is not laundered into a section error message", async () => {
        const category = makeCategory(1, { fieldName: "a" });
        /** @type {any[]} */
        const created = [];
        const { orm } = makeMockOrm();
        const model = makeSearchModel(new Map([[1, category]]), {
            _sectionLoadIds: new Map(),
            orm,
            globalContext: {},
            resModel: "res.partner",
            categories: [category],
            _getFilterDomain: () => [],
            _getCategoryDomain: () => {
                throw new TypeError("cannot read type of undefined");
            },
            _createCategoryTree: (/** @type {any} */ id, /** @type {any} */ result) =>
                created.push([id, result]),
            _reset() {},
            trigger() {},
        });

        await expect(model._fetchCategories([category])).rejects.toThrow(
            /cannot read type of undefined/,
        );
        expect(created).toEqual([]);
        expect(category.errorMsg).toBe(undefined);
    });
});

describe("_shouldWaitForData", () => {
    test("returns true when categories exist AND any filter has non-empty domain", () => {
        const sections = new Map();
        const model = makeSearchModel(sections, {
            categories: [{ fieldName: "categ_id", activeValueId: false }],
            filters: [{ domain: "['active','=',true]", enableCounters: false }],
            searchDomain: [],
        });

        expect(model._shouldWaitForData(false)).toBe(true);
    });

    test("returns false when searchDomain is empty (no category+filter combo)", () => {
        const sections = new Map();
        const model = makeSearchModel(sections, {
            categories: [],
            filters: [],
            searchDomain: [],
        });

        expect(model._shouldWaitForData(true)).toBe(false);
    });

    test("returns true when searchDomain non-empty and a non-expand section exists", () => {
        const section = makeFilter(1, [], { expand: false });
        const sections = new Map([[1, section]]);
        const model = makeSearchModel(sections, {
            categories: [],
            filters: [],
            searchDomain: [["active", "=", true]],
        });

        expect(model._shouldWaitForData(true)).toBe(true);
    });

    test("returns false when all sections have expand=true", () => {
        const section = makeFilter(1, [], { expand: true });
        const sections = new Map([[1, section]]);
        const model = makeSearchModel(sections, {
            categories: [],
            filters: [],
            searchDomain: [["active", "=", true]],
        });

        expect(model._shouldWaitForData(true)).toBe(false);
    });

    test("returns false when searchDomainChanged is false even with non-expand sections", () => {
        const section = makeFilter(1, [], { expand: false });
        const sections = new Map([[1, section]]);
        const model = makeSearchModel(sections, {
            categories: [],
            filters: [],
            searchDomain: [["active", "=", true]],
        });

        expect(model._shouldWaitForData(false)).toBe(false);
    });
});

describe("a failing section fetch leaves a usable section", () => {
    function makeThrowingOrm(error) {
        return {
            cache() {
                return this;
            },
            call() {
                return Promise.reject(error);
            },
        };
    }

    /**
     * @param {Object} section
     * @param {Object} overrides
     */
    function makeFetchModel(section, overrides) {
        return makeSearchModel(new Map([[section.id, section]]), {
            _sectionLoadIds: new Map(),
            orm: makeThrowingOrm(new Error("boom")),
            globalContext: {},
            resModel: "res.partner",
            searchDomain: [],
            _getFilterDomain: () => [],
            _getCategoryDomain: () => [],
            _getGroupDomain: () => null,
            _reset() {},
            trigger() {},
            ...overrides,
        });
    }

    test("a thrown category fetch still builds the tree the panel reads", async () => {
        const category = makeCategory(1, { fieldName: "a", activeValueId: 42 });
        category.values.set(false, { id: false, childrenIds: [], parentId: false });
        const model = makeFetchModel(category, { categories: [category] });

        await model._fetchCategories([category]);

        expect(category.errorMsg).toBe("boom");
        expect(category.rootIds).toEqual([false]);
        expect(category.activeValueId).toBe(false);
        expect(category.values.get(category.activeValueId)).toBeOfType("object");
    });

    test("a thrown filter fetch clears the section instead of half-updating it", async () => {
        const filter = makeFilter(1, [[7, true]], {
            fieldName: "a",
            groupBy: "group_id",
        });
        const model = makeFetchModel(filter, { filters: [filter] });

        await model._fetchFilters([filter]);

        expect(filter.errorMsg).toBe("boom");
        expect(filter.values.size).toBe(0);
        expect([...filter.groups.keys()]).toEqual([]);
    });
});

describe("invalidateSections", () => {
    test("marks the sections stale and notifies once", async () => {
        const model = makeSearchModel(new Map(), {
            searchPanelInfo: { loaded: true, shouldReload: false },
        });
        await model.invalidateSections();
        expect(model.searchPanelInfo.shouldReload).toBe(true);
        expect(model._notifications).toEqual(["notify"]);
    });

    test("answers a promise, so a caller can await the reload", async () => {
        let resolved = false;
        const model = makeSearchModel(new Map(), {
            searchPanelInfo: { shouldReload: false },
            _notify: async () => {
                await Promise.resolve();
                resolved = true;
            },
        });
        await model.invalidateSections();
        expect(resolved).toBe(true);
    });

    test("stays set when it was already set, rather than toggling", async () => {
        const model = makeSearchModel(new Map(), {
            searchPanelInfo: { shouldReload: true },
        });
        await model.invalidateSections();
        expect(model.searchPanelInfo.shouldReload).toBe(true);
    });
});

describe("_reloadSections choreography", () => {
    /** @param {Object} [overrides] */
    function makeReloadModel(overrides = {}) {
        /** @type {any[]} */
        const steps = [];
        const model = makeSearchModel(new Map(), {
            searchPanelInfo: { loaded: true, shouldReload: false },
            display: { searchPanel: true },
            searchDomain: [],
            _reloadMutex: new Mutex(),
            _getDomain: () => [],
            _shouldWaitForData: () => false,
            _fetchSections: async () => {
                steps.push("fetch");
            },
            _steps: steps,
            ...overrides,
        });
        return model;
    }

    test("notifications are blocked for the duration and RESTORED, not cleared", async () => {
        const seen = [];
        const model = makeReloadModel({
            blockNotification: true,
            _getDomain: () => [["a", "=", 1]],
            _fetchSections: async () => seen.push(this),
        });
        await model._reloadSections();
        expect(model.blockNotification).toBe(true);

        model.blockNotification = false;
        await model._reloadSections();
        expect(model.blockNotification).toBe(false);
    });

    test("an unchanged domain fetches nothing", async () => {
        const model = makeReloadModel({ searchDomain: [] });
        await model._reloadSections();
        expect(model._steps).toEqual([]);
    });

    test("a changed domain fetches, and the new domain is recorded", async () => {
        const model = makeReloadModel({
            searchDomain: [],
            _getDomain: () => [["a", "=", 1]],
        });
        await model._reloadSections();
        expect(model._steps).toEqual(["fetch"]);
        expect(model.searchDomain).toEqual([["a", "=", 1]]);
    });

    test("shouldReload forces a fetch even when the domain is identical", async () => {
        const model = makeReloadModel({
            searchPanelInfo: { loaded: true, shouldReload: true },
        });
        await model._reloadSections();
        expect(model._steps).toEqual(["fetch"]);
    });

    test("a hidden panel records that it must reload when shown again", async () => {
        const model = makeReloadModel({
            display: { searchPanel: false },
            _getDomain: () => [["a", "=", 1]],
        });
        await model._reloadSections();
        expect(model._steps).toEqual([]);
        expect(model.searchPanelInfo.shouldReload).toBe(true);
    });

    test("a displayed panel clears the flag once it has refetched", async () => {
        const model = makeReloadModel({
            searchPanelInfo: { loaded: true, shouldReload: true },
        });
        await model._reloadSections();
        expect(model.searchPanelInfo.shouldReload).toBe(false);
    });

    test("the fetch is left on sectionsPromise when it is not awaited", async () => {
        /** @type {(value?: unknown) => void} */
        let release;
        const model = makeReloadModel({
            _getDomain: () => [["a", "=", 1]],
            _shouldWaitForData: () => false,
            _fetchSections: () => new Promise((resolve) => (release = resolve)),
        });
        let settled = false;
        await model._reloadSections();
        model.sectionsPromise.then(() => (settled = true));
        expect(settled).toBe(false);
        release();
        await model.sectionsPromise;
        expect(settled).toBe(true);
    });

    test("the mutex serialises overlapping reloads", async () => {
        /** @type {any[]} */
        const order = [];
        const firstFetch = new Deferred();
        let started = 0;
        let domainSeq = 0;
        const model = makeReloadModel({
            _getDomain: () => [["a", "=", ++domainSeq]],
            _shouldWaitForData: () => true,
            _fetchSections: () => {
                started++;
                if (started === 1) {
                    order.push("start1");
                    return firstFetch.then(() => order.push("end1"));
                }
                order.push("start2");
                order.push("end2");
                return Promise.resolve();
            },
        });
        const first = model._reloadSections();
        const second = model._reloadSections();

        await animationFrame();
        expect(order).toEqual(["start1"]);

        firstFetch.resolve();
        await Promise.all([first, second]);
        expect(order).toEqual(["start1", "end1", "start2", "end2"]);
    });
});
