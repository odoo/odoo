import { expect, test } from "@odoo/hoot";
import IndexedDB from "@point_of_sale/app/models/utils/indexed_db";

test("Test indexedDB upgrade", async () => {
    window.indexedDB.deleteDatabase("unit-test-db");
    const store = [["id", "model1"]];
    const initDb = async (stores) =>
        new Promise((resolve) => new IndexedDB("unit-test-db", false, stores, resolve));

    {
        const result = await initDb(store);
        expect(result.success).toBe(true);
        expect(Array.from(result.instance.db.objectStoreNames)).toEqual(["model1"]);
        result.instance.db.close();
    }

    {
        store.push(["id", "model2"]);
        const result = await initDb(store);
        expect(result.success).toBe(true);
        expect(Array.from(result.instance.db.objectStoreNames)).toEqual(["model1", "model2"]);
        result.instance.db.close();
    }

    {
        store.splice(1, 1); // remove model1
        const result = await initDb(store);
        expect(result.success).toBe(true);
        expect(Array.from(result.instance.db.objectStoreNames)).toEqual(["model1"]);
        result.instance.db.close();
    }

    {
        const result = await initDb(store);
        expect(result.success).toBe(true);
        expect(Array.from(result.instance.db.objectStoreNames)).toEqual(["model1"]);
        result.instance.db.close();
    }

    window.indexedDB.deleteDatabase("unit-test-db");
});
