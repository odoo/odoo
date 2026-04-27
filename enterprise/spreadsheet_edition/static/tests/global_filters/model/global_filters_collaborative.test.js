import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    addColumns,
    addGlobalFilter,
    deleteColumns,
    editGlobalFilter,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import { getCellValue } from "@spreadsheet/../tests/helpers/getters";
import { toRangeData } from "@spreadsheet/../tests/helpers/zones";

import { helpers } from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import {
    setupCollaborativeEnv,
    spExpect,
    insertPivot,
} from "@spreadsheet_edition/../tests/helpers/collaborative_helpers";

describe.current.tags("headless");
defineSpreadsheetModels();

const { toZone } = helpers;

let alice, bob, charlie, network;

beforeEach(async () => {
    ({ alice, bob, charlie, network } = await setupCollaborativeEnv(getBasicServerData()));
});

test("Add a filter with a default value", async () => {
    await insertPivot(alice);
    const filter = {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
        modelName: undefined,
        rangeType: undefined,
    };
    await waitForDataLoaded(alice);
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "D4"), 10);
    await addGlobalFilter(alice, filter, {
        pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
    });
    await waitForDataLoaded(alice);
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getGlobalFilterValue(filter.id),
        [41]
    );
    // the default value should be applied immediately
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "D4"), "");
});

test("Edit a filter", async () => {
    await insertPivot(alice);
    const filter = {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
        modelID: undefined,
        modelName: undefined,
        rangeType: undefined,
    };
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "B4"), 11);
    await addGlobalFilter(alice, filter, {
        pivot: { "PIVOT#1": { chain: "product_id", type: "many2one" } },
    });
    await waitForDataLoaded(alice);
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "B4"), 11);
    await editGlobalFilter(alice, { ...filter, defaultValue: [37] });
    await waitForDataLoaded(alice);
    await waitForDataLoaded(bob);
    await waitForDataLoaded(charlie);
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue((user) => getCellValue(user, "B4"), "");
});

test("Edit a filter and remove it concurrently", async () => {
    const filter = {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
        modelID: undefined,
        modelName: undefined,
        rangeType: undefined,
    };
    await addGlobalFilter(alice, filter);
    await animationFrame();
    await network.concurrent(() => {
        editGlobalFilter(charlie, { ...filter, defaultValue: [37] });
        bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getGlobalFilters(),
        []
    );
});

test("Remove a filter and edit it concurrently", async () => {
    const filter = {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
        modelID: undefined,
        modelName: undefined,
        rangeType: undefined,
    };
    await addGlobalFilter(alice, filter);
    await animationFrame();
    await network.concurrent(() => {
        bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
        editGlobalFilter(charlie, { ...filter, defaultValue: [37] });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getGlobalFilters(),
        []
    );
});

test("Remove a filter and edit another concurrently", async () => {
    const filter1 = {
        id: "41",
        type: "relation",
        label: "41",
        defaultValue: [41],
        modelID: undefined,
        modelName: undefined,
        rangeType: undefined,
    };
    const filter2 = {
        id: "37",
        type: "relation",
        label: "37",
        defaultValue: [37],
        modelID: undefined,
        modelName: undefined,
        rangeType: undefined,
    };
    await addGlobalFilter(alice, filter1);
    await addGlobalFilter(alice, filter2);
    await animationFrame();
    await network.concurrent(() => {
        bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
        editGlobalFilter(charlie, { ...filter2, defaultValue: [74] });
    });
    spExpect([alice, bob, charlie]).toHaveSynchronizedValue(
        (user) => user.getters.getGlobalFilters().map((filter) => filter.id),
        ["37"]
    );
});

test("Setting a filter value is only applied locally", async () => {
    await insertPivot(alice);
    const filter = {
        id: "41",
        type: "relation",
        label: "a relational filter",
    };
    await addGlobalFilter(alice, filter);
    await setGlobalFilterValue(bob, {
        id: filter.id,
        value: [1],
    });
    await animationFrame();
    expect(alice.getters.getActiveFilterCount()).toBe(0);
    expect(bob.getters.getActiveFilterCount()).toBe(1);
    expect(charlie.getters.getActiveFilterCount()).toBe(0);
});

test("add column concurrently to adding a text filter with a range", async () => {
    const sheetId = alice.getters.getActiveSheetId();
    const filter = {
        id: "41",
        type: "text",
        label: "text filter",
        rangeOfAllowedValues: toRangeData(sheetId, "A1:A2"),
    };
    await network.concurrent(async () => {
        await addGlobalFilter(alice, filter);
        addColumns(bob, "before", "A", 1);
    });
    expect(alice.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(toZone("B1:B2"));
    expect(bob.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(toZone("B1:B2"));
    expect(charlie.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(
        toZone("B1:B2")
    );
});

test("delete entirely range concurrently to adding a text filter with a range", async () => {
    const sheetId = alice.getters.getActiveSheetId();
    const filter = {
        id: "41",
        type: "text",
        label: "text filter",
        rangeOfAllowedValues: toRangeData(sheetId, "A1:A2"),
    };
    await network.concurrent(async () => {
        await addGlobalFilter(alice, filter);
        deleteColumns(bob, ["A"]);
    });
    expect(alice.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
    expect(bob.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
    expect(charlie.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
});
test("add column concurrently to editing a text filter with a range", async () => {
    const sheetId = alice.getters.getActiveSheetId();
    const filter = {
        id: "41",
        type: "text",
        label: "text filter",
    };
    await addGlobalFilter(alice, filter);
    await network.concurrent(() => {
        editGlobalFilter(charlie, {
            ...filter,
            rangeOfAllowedValues: toRangeData(sheetId, "A1:A2"),
        });
        addColumns(bob, "before", "A", 1);
    });
    expect(alice.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(toZone("B1:B2"));
    expect(bob.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(toZone("B1:B2"));
    expect(charlie.getters.getGlobalFilter("41").rangeOfAllowedValues.zone).toEqual(
        toZone("B1:B2")
    );
});

test("delete entirely range concurrently to editing a text filter with a range", async () => {
    const sheetId = alice.getters.getActiveSheetId();
    const filter = {
        id: "41",
        type: "text",
        label: "text filter",
        rangeOfAllowedValues: toRangeData(sheetId, "A1:A2"),
    };
    await addGlobalFilter(alice, filter);
    await network.concurrent(() => {
        editGlobalFilter(charlie, {
            ...filter,
            rangeOfAllowedValues: toRangeData(sheetId, "A1:A2"),
        });
        deleteColumns(bob, ["A"]);
    });
    expect(alice.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
    expect(bob.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
    expect(charlie.getters.getGlobalFilter("41").rangeOfAllowedValues).toBe(undefined);
});
