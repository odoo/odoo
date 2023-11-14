/** @odoo-module */

import { mergeContiguousZones } from "@spreadsheet/helpers/zones";

QUnit.module("spreadsheet > zone helpers", {});

QUnit.test("mergeContiguousZones: can merge two contiguous zones", (assert) => {
    let zones = mergeContiguousZones([
        { top: 0, bottom: 5, left: 0, right: 0 },
        { top: 0, bottom: 5, left: 1, right: 1 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 5, left: 0, right: 1 }]);

    zones = mergeContiguousZones([
        { top: 0, bottom: 0, left: 0, right: 5 },
        { top: 1, bottom: 1, left: 0, right: 5 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 1, left: 0, right: 5 }]);

    zones = mergeContiguousZones([
        { top: 0, bottom: 5, left: 0, right: 0 },
        { top: 1, bottom: 1, left: 1, right: 1 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 5, left: 0, right: 1 }]);

    zones = mergeContiguousZones([
        { top: 0, bottom: 0, left: 2, right: 2 },
        { top: 1, bottom: 1, left: 0, right: 5 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 1, left: 0, right: 5 }]);

    // Not contiguous
    zones = mergeContiguousZones([
        { top: 0, bottom: 0, left: 2, right: 2 },
        { top: 2, bottom: 2, left: 2, right: 2 },
    ]);
    assert.deepEqual(zones, [
        { top: 0, bottom: 0, left: 2, right: 2 },
        { top: 2, bottom: 2, left: 2, right: 2 },
    ]);
});

QUnit.test("mergeContiguousZones: can merge two overlapping zones", (assert) => {
    let zones = mergeContiguousZones([
        { top: 0, bottom: 5, left: 0, right: 0 },
        { top: 0, bottom: 3, left: 0, right: 2 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 5, left: 0, right: 2 }]);

    zones = mergeContiguousZones([
        { top: 0, bottom: 5, left: 0, right: 2 },
        { top: 0, bottom: 4, left: 0, right: 1 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 5, left: 0, right: 2 }]);
});

QUnit.test("mergeContiguousZones: can merge overlapping and contiguous zones", (assert) => {
    const zones = mergeContiguousZones([
        { top: 0, bottom: 5, left: 0, right: 0 },
        { top: 0, bottom: 3, left: 0, right: 2 },
        { top: 6, bottom: 6, left: 0, right: 0 },
    ]);
    assert.deepEqual(zones, [{ top: 0, bottom: 6, left: 0, right: 2 }]);
});
