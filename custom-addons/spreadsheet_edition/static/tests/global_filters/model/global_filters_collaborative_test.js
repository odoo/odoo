/** @odoo-module */

import {
    addColumns,
    addGlobalFilter,
    deleteColumns,
    editGlobalFilter,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/utils/commands";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { getCellValue } from "@spreadsheet/../tests/utils/getters";
import { toRangeData } from "@spreadsheet/../tests/utils/zones";
import { nextTick } from "@web/../tests/helpers/utils";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import { insertPivot } from "../../pivot/model/pivot_collaborative_test";
import { setupCollaborativeEnv } from "../../utils/collaborative_helpers";
import { helpers } from "@odoo/o-spreadsheet";

const { toZone } = helpers;

let alice, bob, charlie, network;

async function beforeEach() {
    const env = await setupCollaborativeEnv(getBasicServerData());
    alice = env.alice;
    bob = env.bob;
    charlie = env.charlie;
    network = env.network;
}

QUnit.module("spreadsheet_edition > collaborative global filters", { beforeEach }, () => {
    QUnit.test("Add a filter with a default value", async (assert) => {
        assert.expect(3);
        await insertPivot(alice);
        const filter = {
            id: "41",
            type: "relation",
            label: "41",
            defaultValue: [41],
            modelName: undefined,
            rangeType: undefined,
        };
        await waitForDataSourcesLoaded(alice);
        await waitForDataSourcesLoaded(bob);
        await waitForDataSourcesLoaded(charlie);
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellValue(user, "D4"),
            10
        );
        await addGlobalFilter(alice, filter, {
            pivot: { 1: { chain: "product_id", type: "many2one" } },
        });
        await waitForDataSourcesLoaded(alice);
        await waitForDataSourcesLoaded(bob);
        await waitForDataSourcesLoaded(charlie);
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => user.getters.getGlobalFilterValue(filter.id),
            [41]
        );
        // the default value should be applied immediately
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellValue(user, "D4"),
            ""
        );
    });

    QUnit.test("Edit a filter", async (assert) => {
        assert.expect(3);
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
        await waitForDataSourcesLoaded(bob);
        await waitForDataSourcesLoaded(charlie);
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellValue(user, "B4"),
            11
        );
        await addGlobalFilter(alice, filter, {
            pivot: { 1: { chain: "product_id", type: "many2one" } },
        });
        await waitForDataSourcesLoaded(alice);
        await waitForDataSourcesLoaded(bob);
        await waitForDataSourcesLoaded(charlie);
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellValue(user, "B4"),
            11
        );
        await editGlobalFilter(alice, { ...filter, defaultValue: [37] });
        await waitForDataSourcesLoaded(alice);
        await waitForDataSourcesLoaded(bob);
        await waitForDataSourcesLoaded(charlie);
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => getCellValue(user, "B4"),
            ""
        );
    });

    QUnit.test("Edit a filter and remove it concurrently", async (assert) => {
        assert.expect(1);
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
        await nextTick();
        await network.concurrent(() => {
            editGlobalFilter(charlie, { ...filter, defaultValue: [37] });
            bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
        });
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => user.getters.getGlobalFilters(),
            []
        );
    });

    QUnit.test("Remove a filter and edit it concurrently", async (assert) => {
        assert.expect(1);
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
        await nextTick();
        await network.concurrent(() => {
            bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
            editGlobalFilter(charlie, { ...filter, defaultValue: [37] });
        });
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => user.getters.getGlobalFilters(),
            []
        );
    });

    QUnit.test("Remove a filter and edit another concurrently", async (assert) => {
        assert.expect(1);
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
        await nextTick();
        await network.concurrent(() => {
            bob.dispatch("REMOVE_GLOBAL_FILTER", { id: "41" });
            editGlobalFilter(charlie, { ...filter2, defaultValue: [74] });
        });
        assert.spreadsheetIsSynchronized(
            [alice, bob, charlie],
            (user) => user.getters.getGlobalFilters().map((filter) => filter.id),
            ["37"]
        );
    });

    QUnit.test("Setting a filter value is only applied locally", async (assert) => {
        assert.expect(3);
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
        await nextTick();
        assert.equal(alice.getters.getActiveFilterCount(), 0);
        assert.equal(bob.getters.getActiveFilterCount(), 1);
        assert.equal(charlie.getters.getActiveFilterCount(), 0);
    });

    QUnit.test("add column concurrently to adding a text filter with a range", async (assert) => {
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
        assert.deepEqual(
            alice.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
        assert.deepEqual(
            bob.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
        assert.deepEqual(
            charlie.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
    });

    QUnit.test(
        "delete entirely range concurrently to adding a text filter with a range",
        async (assert) => {
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
            assert.strictEqual(alice.getters.getGlobalFilter("41").rangeOfAllowedValues, undefined);
            assert.strictEqual(bob.getters.getGlobalFilter("41").rangeOfAllowedValues, undefined);
            assert.strictEqual(
                charlie.getters.getGlobalFilter("41").rangeOfAllowedValues,
                undefined
            );
        }
    );
    QUnit.test("add column concurrently to editing a text filter with a range", async (assert) => {
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
        assert.deepEqual(
            alice.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
        assert.deepEqual(
            bob.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
        assert.deepEqual(
            charlie.getters.getGlobalFilter("41").rangeOfAllowedValues.zone,
            toZone("B1:B2")
        );
    });

    QUnit.test(
        "delete entirely range concurrently to editing a text filter with a range",
        async (assert) => {
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
            assert.strictEqual(alice.getters.getGlobalFilter("41").rangeOfAllowedValues, undefined);
            assert.strictEqual(bob.getters.getGlobalFilter("41").rangeOfAllowedValues, undefined);
            assert.strictEqual(
                charlie.getters.getGlobalFilter("41").rangeOfAllowedValues,
                undefined
            );
        }
    );
});
