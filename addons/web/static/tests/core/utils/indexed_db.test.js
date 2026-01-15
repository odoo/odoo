import { _OriginalIndexedDB as IndexedDB } from "@web/core/utils/indexed_db";

import { describe, expect, onError, test } from "@odoo/hoot";

describe.current.tags("headless");

const CACHE_NAME = "unit_test_disk_cache";

function deleteCacheDB() {
    return new Promise((resolve) => {
        const request = indexedDB.deleteDatabase(CACHE_NAME);
        request.onerror = (error) => console.error(error);
        request.onsuccess = resolve;
    });
}

async function ensureDbIsAbsent() {
    const databases = await window.indexedDB.databases();
    expect(databases.filter((db) => db.name === CACHE_NAME).length).toBe(0, {
        message: "DB is correctly cleaned",
    });
}

test("one cache, read", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    expect(await indexedDB.read("mytable", "test")).toBe(undefined);

    await indexedDB.write("mytable", "test", "value for 'test'");
    expect(await indexedDB.read("mytable", "test")).toBe("value for 'test'");

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("two caches, read", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    // having 2 caches simulates 2 tabs, each one accessing the same indexeddb
    const indexedDB1 = new IndexedDB(CACHE_NAME, 1);
    await indexedDB1.write("mytable", "test", "value for 'test'");
    expect(await indexedDB1.read("mytable", "test")).toBe("value for 'test'");

    const indexedDB2 = new IndexedDB(CACHE_NAME, 1);
    expect(await indexedDB2.read("mytable", "test")).toBe("value for 'test'");

    await indexedDB1.deleteDatabase();
    await indexedDB2.deleteDatabase(); // deleting twice the same DB don't throw error !
    await ensureDbIsAbsent();
});

test("two caches, read (2)", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    // having 2 caches simulates 2 tabs, each one accessing the same indexeddb
    const indexedDB1 = new IndexedDB(CACHE_NAME, 1);
    const indexedDB2 = new IndexedDB(CACHE_NAME, 1);

    await indexedDB1.write("mytable", "test", "value for 'test'");
    await indexedDB1.write("mytable1", "test", "value for 'test'");

    expect(await indexedDB2.read("mytable", "test")).toBe("value for 'test'");

    await indexedDB1.deleteDatabase();
    await indexedDB2.deleteDatabase(); // deleting twice the same DB don't throw error !
    await ensureDbIsAbsent();
});

test("one cache, invalidate", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    // populate the table
    await indexedDB.write("mytable", "test", "value for 'test'");
    await indexedDB.write("mytable", "test2", "value for 'test2'");
    expect(await indexedDB.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("mytable", "test2")).toBe("value for 'test2'");

    await indexedDB.invalidate("mytable");
    expect(await indexedDB.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB.read("mytable", "test2")).toBe(undefined);

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("one cache, invalidate multi-tables", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    // populate the table
    await indexedDB.write("mytable", "test", "value for 'test'");
    await indexedDB.write("mytable", "test2", "value for 'test2'");
    await indexedDB.write("mytable2", "test", "value for 'test'");
    await indexedDB.write("mytable2", "test2", "value for 'test2'");
    expect(await indexedDB.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("mytable", "test2")).toBe("value for 'test2'");
    expect(await indexedDB.read("mytable2", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("mytable2", "test2")).toBe("value for 'test2'");

    await indexedDB.invalidate(["mytable", "mytable2"]);
    expect(await indexedDB.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB.read("mytable", "test2")).toBe(undefined);
    expect(await indexedDB.read("mytable2", "test")).toBe(undefined);
    expect(await indexedDB.read("mytable2", "test2")).toBe(undefined);

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("one cache, invalidate all tables", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    // populate the table
    await indexedDB.write("mytable", "test", "value for 'test'");
    await indexedDB.write("mytable2", "test2", "value for 'test2'");
    expect(await indexedDB.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("mytable2", "test2")).toBe("value for 'test2'");

    await indexedDB.invalidate();
    expect(await indexedDB.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB.read("mytable2", "test2")).toBe(undefined);

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("invalidate all tables, empty cache", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    //The indexedDB __DBVersion__ is not invalidated
    const indexedDB = new IndexedDB(CACHE_NAME, 1);
    await indexedDB.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });
    expect(await indexedDB.read("__DBVersion__", "__version__")).toBe(1);
    await indexedDB.invalidate();
    await indexedDB.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });
    expect(await indexedDB.read("__DBVersion__", "__version__")).toBe(1);

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("invalidate non existing table", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);
    await indexedDB.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });
    await indexedDB.invalidate("nonExistingTable");
    await indexedDB.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("invalidate non existing and existing table", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    // populate the table
    await indexedDB.write("mytable", "test", "value for 'test'");
    await indexedDB.write("mytable", "test2", "value for 'test2'");
    expect(await indexedDB.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("mytable", "test2")).toBe("value for 'test2'");

    await indexedDB.invalidate(["nonExistingTable", "mytable"]);
    expect(await indexedDB.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB.read("mytable", "test2")).toBe(undefined);

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("two caches, invalidate", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    // having 2 caches simulates 2 tabs, each one accessing the same indexeddb
    const indexedDB1 = new IndexedDB(CACHE_NAME, 1);
    const indexedDB2 = new IndexedDB(CACHE_NAME, 1);

    // populate the table
    await indexedDB1.write("mytable", "test", "value for 'test'");
    await indexedDB1.write("mytable", "test2", "value for 'test2'");
    expect(await indexedDB1.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB1.read("mytable", "test2")).toBe("value for 'test2'");
    expect(await indexedDB2.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB2.read("mytable", "test2")).toBe("value for 'test2'");

    await indexedDB1.invalidate("mytable");
    expect(await indexedDB1.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB1.read("mytable", "test2")).toBe(undefined);
    expect(await indexedDB2.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB2.read("mytable", "test2")).toBe(undefined);

    await indexedDB1.deleteDatabase();
    await indexedDB2.deleteDatabase();
    await ensureDbIsAbsent();
});

test("two caches, new DB version", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB1 = new IndexedDB(CACHE_NAME, 1);
    // populate the table
    await indexedDB1.write("mytable", "test", "value for 'test'");
    await indexedDB1.write("mytable", "test2", "value for 'test2'");
    expect(await indexedDB1.read("mytable", "test")).toBe("value for 'test'");
    expect(await indexedDB1.read("mytable", "test2")).toBe("value for 'test2'");

    // simulate a new page, with a new version number for the given databases
    const indexedDB2 = new IndexedDB(CACHE_NAME, 2);
    // await new Promise((r) => setTimeout(r, 1));
    // DB should not contain tables !
    await indexedDB2.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });
    await indexedDB2.execute((db) => {
        expect([...db.objectStoreNames]).toEqual(["__DBVersion__"]);
    });
    expect(await indexedDB2.read("mytable", "test")).toBe(undefined);
    expect(await indexedDB2.read("mytable", "test2")).toBe(undefined);

    await indexedDB1.deleteDatabase();
    await indexedDB2.deleteDatabase();
    await ensureDbIsAbsent();
});

test("several tables", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB = new IndexedDB(CACHE_NAME, 1);

    await indexedDB.write("table1", "test", "value for 'test'");
    await indexedDB.write("table2", "test2", "value for 'test2'");
    expect(await indexedDB.read("table1", "test")).toBe("value for 'test'");
    expect(await indexedDB.read("table2", "test2")).toBe("value for 'test2'");

    await indexedDB.deleteDatabase();
    await ensureDbIsAbsent();
});

test("several caches, several tables", async () => {
    onError(() => deleteCacheDB());
    await ensureDbIsAbsent();

    const indexedDB1 = new IndexedDB(CACHE_NAME, 1);
    await indexedDB1.write("table1", "test", "value for 'test'");
    expect(await indexedDB1.read("table1", "test")).toBe("value for 'test'");

    const indexedDB2 = new IndexedDB(CACHE_NAME, 1);
    await indexedDB2.write("table2", "test", "value for 'test'");
    expect(await indexedDB2.read("table1", "test")).toBe("value for 'test'");
    expect(await indexedDB2.read("table2", "test")).toBe("value for 'test'");

    // check that second table has been correctly setup
    const diskCache3 = new IndexedDB(CACHE_NAME, 1);
    expect(await diskCache3.read("table2", "test")).toBe("value for 'test'");

    await indexedDB1.deleteDatabase();
    await indexedDB2.deleteDatabase();
    await ensureDbIsAbsent();
});
