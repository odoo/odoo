import { afterEach, expect, test } from "@odoo/hoot";
import IndexedDB from "@point_of_sale/app/models/utils/indexed_db";

const openedDbNames = new Set();

function uniqueDbName() {
    const name = `pos_test_indexeddb_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    openedDbNames.add(name);
    return name;
}

function openDB(dbName, dbStores) {
    return new Promise((resolve) => {
        const instance = new IndexedDB(dbName, false, dbStores, () => resolve(instance), null);
    });
}

function deleteDB(dbName) {
    return new Promise((resolve) => {
        const request = indexedDB.deleteDatabase(dbName);
        request.onsuccess = () => resolve();
        request.onerror = () => resolve();
        request.onblocked = () => resolve();
    });
}

afterEach(async () => {
    for (const dbName of openedDbNames) {
        await deleteDB(dbName);
    }
    openedDbNames.clear();
});

test("creates object stores that are declared but missing", async () => {
    const dbName = uniqueDbName();
    const db = await openDB(dbName, [
        ["id", "pos.category"],
        ["id", "pos.order"],
    ]);

    expect(Array.from(db.db.objectStoreNames)).toInclude("pos.category");
    expect(Array.from(db.db.objectStoreNames)).toInclude("pos.order");

    db.db.close();
});

test("drops object stores that are no longer expected (ex: module uninstalled)", async () => {
    const dbName = uniqueDbName();

    const first = await openDB(dbName, [
        ["id", "pos.category"],
        ["id", "obox.obox"],
    ]);
    expect(Array.from(first.db.objectStoreNames)).toInclude("obox.obox");
    first.db.close();

    const second = await openDB(dbName, [["id", "pos.category"]]);

    expect(Array.from(second.db.objectStoreNames)).toInclude("pos.category");
    expect(Array.from(second.db.objectStoreNames)).not.toInclude("obox.obox");

    second.db.close();
});

test("keeps unrelated stores untouched when dropping a stale one", async () => {
    const dbName = uniqueDbName();

    const first = await openDB(dbName, [
        ["id", "pos.category"],
        ["id", "obox.obox"],
    ]);
    await new Promise((resolve, reject) => {
        const tx = first.db.transaction(["pos.category"], "readwrite");
        tx.objectStore("pos.category").put({ id: 1, name: "Kept" });
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error);
    });
    first.db.close();

    const second = await openDB(dbName, [["id", "pos.category"]]);
    const records = await new Promise((resolve, reject) => {
        const tx = second.db.transaction(["pos.category"], "readonly");
        const request = tx.objectStore("pos.category").getAll();
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });

    expect(records.length).toBe(1);
    expect(records[0].name).toBe("Kept");

    second.db.close();
});
