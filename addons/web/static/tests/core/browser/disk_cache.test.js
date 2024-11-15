import { _OriginalDiskCache as DiskCache } from "@web/core/browser/disk_cache";

import { after, describe, expect, test } from "@odoo/hoot";

describe.current.tags("headless");

const CACHE_NAME = "unit_test_disk_cache";

async function newDiskCache(tables) {
    const diskCache = new DiskCache(CACHE_NAME);
    for (const { name, version, getData, getKey } of tables) {
        await diskCache.defineTable(name, version, getData, getKey);
    }
    after(
        () =>
            new Promise((resolve) => {
                const request = indexedDB.deleteDatabase(CACHE_NAME);
                request.onerror = (error) => console.error(error);
                request.onsuccess = resolve;
            })
    );
    return diskCache;
}

test("one cache, read", async () => {
    const diskCache = await newDiskCache([
        {
            name: "mytable",
            version: 1,
            getData: (a) => {
                expect.step(`getData '${a}'`);
                return `value for '${a}'`;
            },
            getKey: (a) => {
                expect.step(`getKey '${a}'`);
                return `key for '${a}'`;
            },
        },
    ]);

    expect(await diskCache.read("mytable", "test")).toBe("value for 'test'");
    expect.verifySteps(["getKey 'test'", "getData 'test'"]);

    expect(await diskCache.read("mytable", "test")).toBe("value for 'test'");
    expect.verifySteps(["getKey 'test'"]);

    expect(await diskCache.read("mytable", "test2")).toBe("value for 'test2'");
    expect.verifySteps(["getKey 'test2'", "getData 'test2'"]);
});

test("two caches, read", async () => {
    // having 2 caches simulates 2 tabs, each one accessing the same indexeddb
    const table = {
        name: "mytable",
        version: 1,
        getData: (a) => {
            expect.step(`getData '${a}'`);
            return `value for '${a}'`;
        },
        getKey: (a) => {
            expect.step(`getKey '${a}'`);
            return `key for '${a}'`;
        },
    };
    const diskCache1 = await newDiskCache([table]);
    expect(await diskCache1.read("mytable", "test")).toBe("value for 'test'");
    expect.verifySteps(["getKey 'test'", "getData 'test'"]);

    const diskCache2 = await newDiskCache([table]);
    expect(await diskCache2.read("mytable", "test")).toBe("value for 'test'");
    expect.verifySteps(["getKey 'test'"]);
});

test("one cache, invalidate", async () => {
    const diskCache = await newDiskCache([
        {
            name: "mytable",
            version: 1,
            getData: (a) => {
                expect.step(`getData '${a}'`);
                return `value for '${a}'`;
            },
            getKey: (a) => {
                expect.step(`getKey '${a}'`);
                return `key for '${a}'`;
            },
        },
    ]);

    // populate the table
    await diskCache.read("mytable", "test");
    await diskCache.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);

    await diskCache.invalidate("mytable");
    await diskCache.read("mytable", "test");
    await diskCache.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);
});

test("two caches, invalidate", async () => {
    // having 2 caches simulates 2 tabs, each one accessing the same indexeddb
    const table = {
        name: "mytable",
        version: 1,
        getData: (a) => {
            expect.step(`getData '${a}'`);
            return `value for '${a}'`;
        },
        getKey: (a) => {
            expect.step(`getKey '${a}'`);
            return `key for '${a}'`;
        },
    };
    const diskCache1 = await newDiskCache([table]);
    const diskCache2 = await newDiskCache([table]);

    // populate the table
    await diskCache1.read("mytable", "test");
    await diskCache1.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);

    await diskCache1.invalidate("mytable");
    await diskCache1.read("mytable", "test");
    await diskCache2.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);
});

test("two caches, new table version", async () => {
    const table = {
        name: "mytable",
        version: 1,
        getData: (a) => {
            expect.step(`getData '${a}'`);
            return `value for '${a}'`;
        },
        getKey: (a) => {
            expect.step(`getKey '${a}'`);
            return `key for '${a}'`;
        },
    };
    const diskCache1 = await newDiskCache([table]);
    // populate the table
    await diskCache1.read("mytable", "test");
    await diskCache1.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);

    // simulate a new page, with a new version number for the given table
    table.version = 2;
    const diskCache2 = await newDiskCache([table]);
    await diskCache2.read("mytable", "test");
    await diskCache2.read("mytable", "test2");
    expect.verifySteps(["getKey 'test'", "getData 'test'", "getKey 'test2'", "getData 'test2'"]);
});

test("several tables", async () => {
    const diskCache = await newDiskCache([
        {
            name: "table1",
            version: 1,
            getData: (a) => `value for '${a}'`,
            getKey: (a) => `key for '${a}'`,
        },
        {
            name: "table2",
            version: 1,
            getData: (a) => `value for '${a}'`,
            getKey: (a) => `key for '${a}'`,
        },
    ]);

    expect(await diskCache.read("table1", "test")).toBe("value for 'test'");
    expect(await diskCache.read("table1", "test")).toBe("value for 'test'");
    expect(await diskCache.read("table2", "test2")).toBe("value for 'test2'");
    expect(await diskCache.read("table2", "test2")).toBe("value for 'test2'");
});

test("several caches, several tables", async () => {
    const table1 = {
        name: "table1",
        version: 1,
        getData: (a) => {
            expect.step(`table1, getData '${a}'`);
            return `value for '${a}'`;
        },
        getKey: (a) => {
            expect.step(`table1, getKey '${a}'`);
            return `key for '${a}'`;
        },
    };
    const table2 = {
        name: "table2",
        version: 1,
        getData: (a) => {
            expect.step(`table2, getData '${a}'`);
            return `value for '${a}'`;
        },
        getKey: (a) => {
            expect.step(`table2, getKey '${a}'`);
            return `key for '${a}'`;
        },
    };
    const diskCache1 = await newDiskCache([table1]);
    expect(await diskCache1.read("table1", "test")).toBe("value for 'test'");
    expect(await diskCache1.read("table1", "test")).toBe("value for 'test'");
    expect.verifySteps([
        "table1, getKey 'test'",
        "table1, getData 'test'",
        "table1, getKey 'test'",
    ]);

    const diskCache2 = await newDiskCache([table1, table2]);
    expect(await diskCache1.read("table1", "test")).toBe("value for 'test'");
    expect(await diskCache2.read("table1", "test")).toBe("value for 'test'");
    expect(await diskCache2.read("table2", "test")).toBe("value for 'test'");
    expect(await diskCache2.read("table2", "test")).toBe("value for 'test'");
    expect.verifySteps([
        "table1, getKey 'test'", // first table hasn't been invalidated
        "table1, getKey 'test'", // first table hasn't been invalidated
        "table2, getKey 'test'",
        "table2, getData 'test'",
        "table2, getKey 'test'",
    ]);

    // check that second table has been correctly setup
    const diskCache3 = await newDiskCache([table1, table2]);
    expect(await diskCache3.read("table2", "test")).toBe("value for 'test'");
    expect.verifySteps(["table2, getKey 'test'"]);
});
